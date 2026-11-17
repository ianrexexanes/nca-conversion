import contextlib
import io
import json
import os
import pty
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "form_consent.py"
sys.path.insert(0, str(HERE))

import clarity_export  # noqa: E402
import cro_runtime  # noqa: E402
import form_check  # noqa: E402
import form_consent  # noqa: E402
from http.server import ThreadingHTTPServer  # noqa: E402
from form_tests import FormServer, Run, run_script  # noqa: E402
from guard_tests import SKIP, GuardLeakPathsMixin  # noqa: E402

HOLD_SECONDS = 6.0  # how long the fixture server holds a POST or a page it is asked to hold
TODAY = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()
OWNER = "Test Owner"
EMAIL = "test.owner@example.com"
LINE = "Test submission, consented by %s, %s" % (OWNER, TODAY)
GOOD = ["--owner", OWNER, "--date", TODAY, "--email", EMAIL]


def run_with(args, url="http://127.0.0.1:9/form-bad-input.html"):
    """Run form_consent.main in this process with the guard's launch patched to raise, so a call to it fails the test.
    args is a list of flag, value pairs read as given; a value of None leaves the flag out. Returns the exit code."""
    argv = [url, "--out", tempfile.mkdtemp()]
    given = {args[i]: args[i + 1] for i in range(0, len(args), 2)}
    base = {"--owner": OWNER, "--date": TODAY, "--email": EMAIL}
    base.update(given)
    for flag, value in base.items():
        if value is not None:
            argv += [flag, value]
    import form_consent
    with mock.patch.object(cro_runtime, "guarded_launch", side_effect=AssertionError("a browser opened")), \
            contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
        return form_consent.main(argv)


class BadInputTests(unittest.TestCase):
    def test_consent_refuses_bad_input_before_a_browser_opens(self):
        for args in (["--owner", ""], ["--owner", "   "], ["--date", YESTERDAY], ["--date", "2026-13-40"], ["--email", None],
                     ["--email", "not-an-address"]):
            code = run_with(args)  # guarded_launch is patched to raise if it is called
            self.assertEqual(code, 2, args)

    def test_more_bad_input_is_refused_the_same_way(self):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        for args in (["--date", tomorrow], ["--date", "today"], ["--email", "owner@example"], ["--email", "owner@@example.com"],
                     ["--email", "@example.com"], ["--email", "owner@.com"], ["--email", "own er@example.com"],
                     ["--owner", "Line\nBreak"]):
            self.assertEqual(run_with(args), 2, args)

    def test_an_address_that_cannot_be_parsed_is_refused_before_a_browser_opens(self):
        try:
            code = run_with([], url="http://[::1")  # guarded_launch is patched to raise if it is called
        except ValueError as error:
            self.fail("an unparseable address escaped as %r instead of exit 2" % error)
        self.assertEqual(code, 2)

    def test_a_missing_flag_or_address_exits_2_and_names_the_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            for argv in ([], ["http://127.0.0.1:9/x.html", "--out", tmp], ["http://127.0.0.1:9/x.html", "--out", tmp, *GOOD[:4]]):
                done = subprocess.run([sys.executable, str(SCRIPT), *argv], capture_output=True, text=True, timeout=60)
                self.assertEqual(done.returncode, 2, argv)
                self.assertIn("form_consent", done.stderr)


class AnswerServer(FormServer):
    """The recording server with the extra answers these tests need: a POST that answers after 6 seconds, and answers of 200 and 500."""
    ANSWERS = {"/lead-1500": (200, 1.5), "/lead-6s": (200, 6.0), "/lead-elsewhere-500": (500, 0), "/lead-elsewhere-200": (200, 0), "/api/lead": (200, 0)}

    PAGE = b"<!doctype html><title>Thanks</title><main><h1>Thank you</h1><p>We reply within one working day.</p></main>"

    def _go(self):
        path = self.path.split("?", 1)[0]
        if path in ("/lead-hold", "/lead-hold-long", "/lead-hold-303", "/lead-hangup", "/page-held"):
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length).decode("utf-8", "replace") if length else ""
            with FormServer.lock:
                FormServer.requests.append((self.command, self.path, self.headers.get("User-Agent", ""), body))
            try:
                if path == "/lead-hangup":
                    self.close_connection = True
                    self.connection.shutdown(socket.SHUT_RDWR)  # no answer at all: the connection just ends
                elif path == "/lead-hold-303":
                    self._send(303, b"", None, {"Location": "/page-held"})
                else:
                    time.sleep(30.0 if path == "/lead-hold-long" else HOLD_SECONDS)
                    self._send(200, self.PAGE, "text/html; charset=utf-8")
            except OSError:
                pass
        elif self.command == "POST" and path in self.ANSWERS:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length).decode("utf-8", "replace") if length else ""
            with FormServer.lock:
                FormServer.requests.append((self.command, self.path, self.headers.get("User-Agent", ""), body))
            status, delay = self.ANSWERS[path]
            time.sleep(delay)
            try:
                if path == "/lead-6s":
                    self._send(status, b"<!doctype html><title>Thanks</title><main><h1>Thank you</h1><p>We reply within one working day.</p></main>",
                               "text/html; charset=utf-8")
                else:
                    self._send(status, b'{"ok": true}', "application/json", {"Access-Control-Allow-Origin": "*"})
            except OSError:
                pass
        elif self.command == "GET" and path == "/thanks-slow":
            time.sleep(0.6)
            try:
                self._send(200, self.PAGE, "text/html; charset=utf-8")
            except OSError:
                pass
        else:
            super()._go()

    do_GET = do_HEAD = do_POST = do_OPTIONS = _go


def start_answer_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), AnswerServer)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, "http://127.0.0.1:%d" % server.server_address[1]


class ReadMethodNameTests(unittest.TestCase):
    def test_the_read_methods_have_one_name_and_no_other_copy(self):
        self.assertFalse(hasattr(form_consent, "NON_GET"))
        literal = '("GET", "HEAD", ' + '"OPTIONS")'
        for script in ("form_check.py", "form_consent.py"):
            self.assertNotIn(literal, (HERE / script).read_text(encoding="utf-8"), script)


class SinglePressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.base = start_answer_server()
        cls.addClassCleanup(cls.server.server_close)
        cls.addClassCleanup(cls.server.shutdown)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)

    def test_a_form_answered_after_six_seconds_is_pressed_once_and_reported_pressed(self):
        run = run_script(SCRIPT, "%s/form-answer-6s.html" % self.base, *GOOD, tmp=self.tmp.name)
        self.assertEqual(run.code, 0, (run.out, run.err))
        self.assertEqual([p for _m, p in run.posts()], ["/lead-6s"])
        self.assertIs(run.form["submit"]["pressed"], True)
        self.assertEqual(run.form["submit"]["state"], "navigated")
        self.assertEqual(len([e for e in run.log if e["method"] not in cro_runtime.ALLOWED_METHODS]), 1, run.log)

    def test_a_form_hidden_after_the_send_reads_the_thank_you_from_the_page(self):
        run = run_script(SCRIPT, "%s/form-hidden-on-success.html" % self.base, *GOOD, tmp=self.tmp.name)
        self.assertEqual(run.code, 0, (run.out, run.err))
        self.assertIn("Thanks, we will reply within one day.", run.form["thank_you"]["text"] or "")

    def test_a_click_that_raised_after_it_landed_is_not_made_twice(self):
        run = run_script(SCRIPT, "%s/form-busy-click.html" % self.base, *GOOD, tmp=self.tmp.name)
        self.assertEqual(run.code, 0, (run.out, run.err))
        self.assertEqual([p for _m, p in run.posts()], ["/lead"])
        self.assertIs(run.form["submit"]["pressed"], True)
        # a second click would show as a second request in the log, aborted by the guard though it never reaches the server
        self.assertEqual(len([e for e in run.log if e["method"] not in cro_runtime.ALLOWED_METHODS]), 1, run.log)

    def test_a_submit_control_covered_by_another_element_is_still_pressed_once(self):
        run = run_script(SCRIPT, "%s/form-covered-submit.html" % self.base, *GOOD, tmp=self.tmp.name)
        self.assertEqual([p for _m, p in run.posts()], ["/lead-303"], (run.out, run.err))
        self.assertIs(run.form["submit"]["pressed"], True)


class ElsewhereAnswerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.base = start_answer_server()
        cls.addClassCleanup(cls.server.server_close)
        cls.addClassCleanup(cls.server.shutdown)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)

    def test_an_answer_of_500_from_where_the_page_script_sent_the_form_is_a_fail(self):
        run = run_script(SCRIPT, "%s/form-elsewhere-500.html" % self.base, *GOOD, tmp=self.tmp.name)
        self.assertEqual(run.code, 1, (run.out, run.err))
        self.assertEqual([p for _m, p in run.posts()], ["/lead-elsewhere-500"])
        self.assertTrue([d for lv, _f, r, d in run.lines if (lv, r) == ("FAIL", "SEND") and "/lead-elsewhere-500" in d and "500" in d], run.lines)
        self.assertTrue([d for lv, _f, r, d in run.lines if (lv, r) == ("WARN", "SEND") and "lead arrived" in d], run.lines)

    def test_an_answer_of_200_from_where_the_page_script_sent_the_form_is_not_a_fail(self):
        run = run_script(SCRIPT, "%s/form-elsewhere-200.html" % self.base, *GOOD, tmp=self.tmp.name)
        self.assertEqual(run.code, 0, (run.out, run.err))
        self.assertEqual([p for _m, p in run.posts()], ["/lead-elsewhere-200"])
        self.assertEqual([r for lv, _f, r, _d in run.lines if lv == "FAIL"], [], run.lines)


class HeldAnswerTests(unittest.TestCase):
    """S07: a host that has not answered must not hold the script past the wait. The wait is cut to 1.5 seconds and the host holds
    for 6, and each run has its own bound of the wait plus 10 seconds."""
    WAIT = 1500

    @classmethod
    def setUpClass(cls):
        cls.server, cls.base = start_answer_server()
        cls.addClassCleanup(cls.server.server_close)
        cls.addClassCleanup(cls.server.shutdown)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)

    def bounded_run(self, page, wait=None, bound=None):
        wait = wait or self.WAIT
        folder = tempfile.mkdtemp(dir=self.tmp.name)
        with FormServer.lock:
            mark = len(FormServer.requests)
        out, err, result = io.StringIO(), io.StringIO(), []

        def go():
            with mock.patch.object(form_consent, "WAIT_MS", wait), mock.patch.object(form_consent, "POST_WAIT_MS", 1000), \
                    mock.patch.object(form_consent, "LOOPBACK", form_consent.LOOPBACK), mock.patch.object(sys, "stdin", FakeTerminal(False)), \
                    contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                result.append(form_consent.main(["%s/%s" % (self.base, page), "--out", folder, *GOOD]))

        thread = threading.Thread(target=go, daemon=True)
        started = time.monotonic()
        thread.start()
        thread.join(bound or wait / 1000 + 10)
        self.assertFalse(thread.is_alive(), "the run did not end within its bound")
        with FormServer.lock:
            seen = list(FormServer.requests[mark:])
        return Run(result[0], out.getvalue(), err.getvalue(), seen, folder), time.monotonic() - started

    def test_a_post_the_host_holds_past_the_wait_ends_the_run_with_the_warning(self):
        run, _took = self.bounded_run("form-hold-post.html")
        self.assertEqual(run.code, 0, (run.out, run.err))
        self.assertEqual([p for _m, p in run.posts()], ["/lead-hold"])
        self.assertTrue([d for lv, _f, r, d in run.lines if (lv, r) == ("WARN", "SEND") and "had not answered" in d], run.lines)
        self.assertIs(run.form["submit"]["pressed"], True)
        self.assertEqual(run.data["network"]["consented"], 1)

    def test_a_page_blocked_by_a_synchronous_request_to_a_slow_host_still_ends_the_run(self):
        run, _took = self.bounded_run("form-sync-xhr.html", bound=self.WAIT / 1000 + 20)
        self.assertEqual(run.code, 0, (run.out, run.err))
        self.assertEqual([p for _m, p in run.posts()], ["/lead-hold-long"])
        self.assertTrue([d for lv, _f, r, d in run.lines if (lv, r) == ("WARN", "SEND") and "had not answered" in d], run.lines)
        self.assertIs(run.form["submit"]["pressed"], True)

    def test_a_page_after_the_send_that_the_host_holds_past_the_wait_ends_the_run_with_the_warning(self):
        run, _took = self.bounded_run("form-hold-page.html")
        self.assertEqual(run.code, 0, (run.out, run.err))
        self.assertEqual([p for _m, p in run.posts()], ["/lead-hold-303"])
        self.assertTrue([d for lv, _f, r, d in run.lines if (lv, r) == ("WARN", "SEND") and "had not loaded" in d and "303" in d], run.lines)
        self.assertIs(run.form["submit"]["pressed"], True)


class HangUpTests(HeldAnswerTests):
    """S06: a host that ends the connection on the POST with no answer. The wait is 20 seconds and the run must end in under 10."""

    def test_a_host_that_hangs_up_on_the_post_is_a_fail_and_the_error_page_is_not_the_thank_you(self):
        run, _took = self.bounded_run("form-hangup.html", wait=20000, bound=10)
        self.assertEqual(run.code, 1, (run.out, run.err))
        self.assertTrue([d for lv, _f, r, d in run.lines if (lv, r) == ("FAIL", "SEND") and "ended the connection" in d and "ERR_" in d],
                        run.lines)
        self.assertNotIn("had not answered", run.out)
        self.assertIsNone(run.form["thank_you"]["url"])
        self.assertIsNone(run.form["thank_you"]["text"])

    test_a_post_the_host_holds_past_the_wait_ends_the_run_with_the_warning = None  # inherited tests run once, in their own class
    test_a_page_after_the_send_that_the_host_holds_past_the_wait_ends_the_run_with_the_warning = None
    test_a_page_blocked_by_a_synchronous_request_to_a_slow_host_still_ends_the_run = None


class FollowUpTests(HeldAnswerTests):
    """What the run reads and reports once the answer is in: the page that follows the send, and how a failed request is named."""

    def test_a_frame_that_loads_after_the_send_does_not_hold_the_page(self):
        run, _took = self.bounded_run("form-frame-after-send.html")
        self.assertEqual(run.code, 0, (run.out, run.err))
        self.assertEqual([p for _m, p in run.posts()], ["/lead"])
        self.assertEqual(run.form["thank_you"]["text"], "Thank you, we got it", run.form["thank_you"])
        self.assertFalse([d for lv, _f, r, d in run.lines if lv == "WARN"], run.lines)
        self.assertNotIn("had not loaded", run.out + run.err)
        self.assertTrue((Path(run.dir) / "form1-consented.png").is_file(), sorted(p.name for p in Path(run.dir).iterdir()))

    def test_a_thank_you_page_that_is_slow_to_answer_is_waited_for_and_read(self):
        run, _took = self.bounded_run("form-moves-to-slow-thanks.html", wait=8000, bound=30)
        self.assertEqual(run.code, 0, (run.out, run.err))
        self.assertEqual([p for _m, p in run.posts()], ["/lead-1500"])
        self.assertEqual(run.form["submit"]["state"], "navigated", run.form["submit"])
        self.assertTrue((run.form["thank_you"]["url"] or "").endswith("/thanks-slow"), run.form["thank_you"])
        self.assertIn("We reply within one working day", run.form["thank_you"]["text"] or "")
        self.assertFalse([d for lv, _f, r, d in run.lines if lv == "WARN"], run.lines)
        self.assertNotIn("had not loaded", run.out + run.err)

    def test_a_request_the_page_cancels_itself_is_a_warning_and_not_a_hang_up(self):
        run, _took = self.bounded_run("form-aborts-own-request.html", wait=20000, bound=10)
        self.assertEqual(run.code, 0, (run.out, run.err))
        self.assertEqual([p for _m, p in run.posts()], ["/lead-hold"])
        self.assertTrue([d for lv, _f, r, d in run.lines if (lv, r) == ("WARN", "SEND") and "was cancelled before an answer came" in d
                         and "ERR_ABORTED" in d and "most likely by the page itself" in d and "check before any rerun" in d], run.lines)
        self.assertEqual([d for lv, _f, _r, d in run.lines if lv == "FAIL"], [], run.lines)
        self.assertNotIn("ended the connection", run.out)
        self.assertNotIn("had not answered", run.out)

    def test_a_request_the_browser_refuses_is_named_as_failed_and_not_as_a_hang_up(self):
        run, _took = self.bounded_run("form-unsafe-port.html", wait=20000, bound=10)
        self.assertEqual(run.code, 1, (run.out, run.err))
        self.assertTrue([d for lv, _f, r, d in run.lines if (lv, r) == ("FAIL", "SEND") and "the browser reports the consented request as failed" in d
                         and "ERR_" in d and "check before any rerun" in d], run.lines)
        self.assertNotIn("ended the connection", run.out)
        self.assertNotIn("had not answered", run.out)

    def test_a_form_that_changes_at_the_click_is_timed_from_the_press_and_not_from_a_fixed_pause(self):
        run, _took = self.bounded_run("form-changes-at-click.html", wait=8000, bound=30)
        self.assertEqual(run.code, 0, (run.out, run.err))
        self.assertEqual([p for _m, p in run.posts()], ["/api/lead"])
        self.assertEqual(run.form["submit"]["state"], "changed", run.form["submit"])
        self.assertLess(run.form["submit"]["time_ms"], 350, run.form["submit"])

    test_a_post_the_host_holds_past_the_wait_ends_the_run_with_the_warning = None  # inherited tests run once, in their own class
    test_a_page_after_the_send_that_the_host_holds_past_the_wait_ends_the_run_with_the_warning = None
    test_a_page_blocked_by_a_synchronous_request_to_a_slow_host_still_ends_the_run = None


class FakeTerminal:
    """Standard input for an in-process run: isatty() and readline() are the test's to set."""

    def __init__(self, tty, answer=""):
        self.tty, self.answer = tty, answer

    def isatty(self):
        return self.tty

    def readline(self):
        return self.answer


class TerminalQuestionTests(unittest.TestCase):
    def test_loopback_is_the_three_hosts_the_plugin_already_names(self):
        self.assertEqual(form_consent.LOOPBACK, clarity_export.LOOPBACK)
        self.assertEqual(sorted(form_consent.LOOPBACK), ["127.0.0.1", "::1", "localhost"])

    def test_the_terminal_question_is_not_put_without_a_terminal(self):
        err = io.StringIO()
        with mock.patch.object(sys, "stdin", FakeTerminal(False, "example.com\n")), contextlib.redirect_stderr(err):
            answer = form_consent.ask_host("example.com", "https://example.com/contact")
        self.assertIsNone(answer)
        self.assertEqual(err.getvalue(), "")

    def test_the_terminal_question_reads_the_typed_host_from_a_real_terminal(self):
        master, slave = pty.openpty()
        self.addCleanup(lambda: os.close(master))
        stdin = os.fdopen(slave, "r")
        self.addCleanup(stdin.close)
        os.write(master, b"EXAMPLE.com \n")
        err = io.StringIO()
        with mock.patch.object(sys, "stdin", stdin), contextlib.redirect_stderr(err):
            answer = form_consent.ask_host("example.com", "https://example.com/contact")
        self.assertEqual(answer, "example.com")
        self.assertIn("form_consent: this sends one real test submission to example.com, through the form on https://example.com/contact.\n", err.getvalue())
        self.assertTrue(err.getvalue().endswith("Type example.com to send it, or press Enter to stop: "), err.getvalue())

    def test_a_missing_standard_input_counts_as_no_terminal(self):
        class Broken:
            def isatty(self):
                raise ValueError("I/O operation on closed file")

        for stdin in (None, Broken()):
            err = io.StringIO()
            with mock.patch.object(sys, "stdin", stdin), contextlib.redirect_stderr(err):
                self.assertIsNone(form_consent.ask_host("example.com", "https://example.com/contact"))
            self.assertEqual(err.getvalue(), "")

    def test_a_terminal_that_fails_on_the_read_counts_as_nothing_typed(self):
        for failure in (OSError("hung up"), KeyboardInterrupt()):
            class Failing(FakeTerminal):
                def readline(self):
                    raise failure

            with mock.patch.object(sys, "stdin", Failing(True)), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(form_consent.ask_host("example.com", "https://example.com/contact"), "", failure)


@SKIP
class FormConsentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.base = start_answer_server()  # answers /api/lead too, so the ajax test's lead is answered 200
        cls.addClassCleanup(cls.server.server_close)
        cls.addClassCleanup(cls.server.shutdown)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.cache = {}
        cls.counts = {}

    def consent(self, page, *flags):
        key = (page, flags)
        if key not in self.cache:
            run = run_script(SCRIPT, "%s/%s" % (self.base, page), *GOOD, *flags, tmp=self.tmp.name)
            self.cache[key] = run
            type(self).counts[" ".join((page,) + flags)] = {"POST": len(run.posts()), "OPTIONS": sum(1 for m, _p, _a, _b in run.seen if m == "OPTIONS"),
                                       "GET": sum(1 for m, _p, _a, _b in run.seen if m == "GET"),
                                       "consented": run.data.get("network", {}).get("consented"), "exit": run.code}
        return self.cache[key]

    @classmethod
    def tearDownClass(cls):
        print("\nrecording server counts per consent run: %s" % json.dumps(cls.counts, sort_keys=True), file=sys.stderr)
        super().tearDownClass()

    def test_consent_sends_exactly_one_post_to_the_action_host(self):
        run = self.consent("form-lead.html")
        self.assertEqual(run.code, 0, run.err)
        self.assertEqual([p for _m, p in run.posts()], ["/lead"])
        self.assertFalse([p for p in run.paths() if p.startswith(("/gtm.js", "/g/collect"))], run.paths())
        self.assertEqual(run.data["mode"], "consented")
        self.assertEqual(run.data["network"]["consented"], 1)
        self.assertEqual(sum(1 for e in run.log if e["outcome"] == "consented"), 1)
        self.assertEqual(run.out.strip().splitlines()[-1], "form_consent: 0 FAIL, 0 WARN")
        self.assertNotIn("Type ", run.err)  # a loopback host is not asked
        self.assertIsInstance(run.form["submit"]["time_ms"], int)
        self.assertEqual(run.form["submit"]["state"], "changed")
        self.assertIn("Thanks", run.form["submit"]["status_text"])
        self.assertTrue((run.dir / "form1-consented.png").is_file())
        for _m, _p, agent, _b in run.seen:
            self.assertIn("Chrome/", agent)
            self.assertNotIn("Headless", agent)

    def in_process(self, terminal, page="form-lead.html", loopback=()):
        """form_consent.main in this process, with the server's own host counted as a real one and standard input a FakeTerminal."""
        folder = tempfile.mkdtemp(dir=self.tmp.name)
        with FormServer.lock:
            mark = len(FormServer.requests)
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(form_consent, "LOOPBACK", loopback), mock.patch.object(sys, "stdin", terminal), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = form_consent.main(["%s/%s" % (self.base, page), "--out", folder, *GOOD])
        with FormServer.lock:
            seen = list(FormServer.requests[mark:])
        return Run(code, out.getvalue(), err.getvalue(), seen, folder)

    def assertNothingSent(self, run):
        self.assertEqual(run.code, 3, run.out + run.err)
        self.assertEqual(run.posts(), [])
        self.assertFalse([e for e in run.log if e["outcome"] == "consented"], run.log)
        self.assertIn("SKIPPED", run.out)

    def test_a_real_host_with_no_terminal_sends_nothing(self):
        run = self.in_process(FakeTerminal(False, "127.0.0.1\n"))
        self.assertNothingSent(run)
        self.assertIn("needs a person at a terminal", run.out)
        self.assertNotIn("Type ", run.err)

    def test_a_real_host_with_another_host_typed_sends_nothing(self):
        run = self.in_process(FakeTerminal(True, "example.org\n"))
        self.assertNothingSent(run)
        self.assertIn("was not", run.out)

    def test_a_real_host_with_nothing_typed_sends_nothing(self):
        for answer in ("\n", ""):
            run = self.in_process(FakeTerminal(True, answer))
            self.assertNothingSent(run)

    def test_a_real_host_with_its_host_typed_sends_once(self):
        run = self.in_process(FakeTerminal(True, " 127.0.0.1 \n"))
        self.assertEqual(run.code, 0, run.out + run.err)
        self.assertEqual([p for _m, p in run.posts()], ["/lead"])
        self.assertIn("Type 127.0.0.1 to send it", run.err)

    def test_consent_does_not_press_when_the_fill_breaks_a_pattern(self):
        run = self.consent("form-code-pattern.html")
        self.assertEqual(run.code, 3, run.err)
        self.assertEqual(run.posts(), [])
        self.assertIn("not sent: the fill does not satisfy code (", run.out)
        self.assertEqual(run.data["network"]["consented"], 0)
        self.assertFalse(run.form["submit"]["pressed"], run.form)

    def test_a_second_post_is_aborted(self):
        run = self.consent("form-twice.html")
        self.assertEqual([p for _m, p in run.posts()], ["/lead-twice"])
        self.assertTrue(run.logged("/lead-twice", "blocked", "consent:used"), run.log)
        self.assertEqual(run.data["network"]["consented"], 1)

    def test_consent_text_is_recorded(self):
        run = self.consent("form-lead.html")
        body = [b for m, _p, _a, b in run.seen if m == "POST"][0]
        self.assertIn(LINE, body)
        self.assertIn(EMAIL, body)
        self.assertEqual(run.data["consent"], "%s, %s" % (OWNER, TODAY))
        filled = run.form["filled"]
        self.assertEqual(filled["email"], EMAIL)
        self.assertEqual(filled["name"], LINE)
        self.assertEqual(filled["message"], LINE)

    def test_blocked_action_host_is_never_consented(self):
        # In this process, with the analytics host counted as loopback only so the terminal question is not put: this test is about the guard's block.
        run = self.in_process(FakeTerminal(False), "form-analytics.html", ("www.google-analytics.com",))
        self.assertEqual(run.code, 3, run.err)
        self.assertTrue([d for lv, _f, r, d in run.lines if (lv, r) == ("SKIPPED", "SEND") and "google-analytics.com" in d],
                        run.lines)
        self.assertEqual(run.data["network"]["consented"], 0)
        self.assertTrue(run.logged("google-analytics.com", "blocked", "host:"), run.log)
        self.assertEqual(run.posts(), [])

    def test_a_blocked_host_typed_at_the_terminal_is_still_blocked(self):
        run = self.in_process(FakeTerminal(True, "www.google-analytics.com\n"), "form-analytics.html", form_consent.LOOPBACK)
        self.assertEqual(run.code, 3, run.err)
        self.assertIn("Type www.google-analytics.com to send it", run.err)
        self.assertTrue([d for lv, _f, r, d in run.lines if (lv, r) == ("SKIPPED", "SEND") and "google-analytics.com" in d], run.lines)
        self.assertEqual(run.data["network"]["consented"], 0)
        self.assertFalse([e for e in run.log if e["outcome"] == "consented"], run.log)
        self.assertTrue(run.logged("google-analytics.com", "blocked", "host:"), run.log)
        self.assertEqual(run.posts(), [])

    def test_upper_case_action_host_is_consented(self):
        run = self.consent("form-cors.html")
        self.assertEqual(run.code, 0, run.err)
        self.assertEqual(run.data["network"]["consented"], 1)
        self.assertEqual([p for _m, p in run.posts()], ["/lead-cors"])
        self.assertIn(LINE, [b for m, _p, _a, b in run.seen if m == "POST"][0])

    def test_preflight_does_not_use_up_the_consent(self):
        # Playwright answers the preflight itself while a route is on, so the server sees no OPTIONS and exactly one POST
        run = self.consent("form-cors.html")
        self.assertEqual([m for m, p, _a, _b in run.seen if p.startswith("/lead-cors")], ["POST"])
        self.assertEqual(run.data["network"]["consented"], 1)

    def test_redirect_after_the_consented_post_is_followed_by_get(self):
        run = self.consent("form-native.html")
        self.assertEqual(run.code, 0, run.err)
        self.assertEqual([(m, p) for m, p, _a, _b in run.seen if p.startswith(("/lead-303", "/form-thanks"))],
                         [("POST", "/lead-303"), ("GET", "/form-thanks.html")])
        self.assertEqual(run.data["network"]["consented"], 1)
        self.assertEqual(run.form["submit"]["state"], "navigated")
        self.assertTrue(run.form["thank_you"]["url"].endswith("/form-thanks.html"), run.form["thank_you"])
        self.assertIn("next step", run.form["thank_you"]["text"])

    def test_a_beacon_on_load_does_not_take_the_single_send(self):
        run = self.consent("form-beacon.html")
        self.assertEqual(run.code, 0, (run.err, run.lines))
        self.assertEqual([p for _m, p in run.posts()], ["/lead"])
        self.assertEqual(run.paths().count("/api/event"), 0)
        self.assertTrue(run.logged("/api/event", "blocked", "method:"), run.log)
        self.assertEqual(run.data["network"]["consented"], 1)

    def test_a_get_form_is_refused_before_the_press(self):
        run = self.consent("form-get.html")
        self.assertEqual(run.code, 3, run.err)
        self.assertEqual([p for p in run.paths() if p.startswith("/lead-get")], [])
        self.assertTrue([d for lv, _f, r, d in run.lines if (lv, r) == ("SKIPPED", "SEND") and "GET" in d], run.lines)
        self.assertEqual(run.data["network"]["consented"], 0)

    def test_a_form_with_an_invalid_method_value_is_refused_as_get(self):
        # The browser reads method="psot", method="post " and formmethod="put" as GET, so each is refused like a GET form.
        for page in ("form-method-typo.html", "form-method-space.html", "form-formmethod-put.html"):
            run = self.consent(page)
            self.assertEqual(run.code, 3, (page, run.err))
            self.assertEqual([p for p in run.paths() if p.startswith("/lead")], [], page)
            self.assertTrue([d for lv, _f, r, d in run.lines if (lv, r) == ("SKIPPED", "SEND") and "GET" in d], (page, run.lines))
            self.assertEqual(run.data["network"]["consented"], 0, page)

    def test_a_field_named_method_does_not_hide_the_forms_method(self):
        # A control called method takes the place of form.method, so the gate must read the real value.
        run = self.consent("form-method-shadowed.html")
        self.assertEqual(run.code, 3, run.err)
        self.assertEqual([p for p in run.paths() if p.startswith("/lead")], [])
        self.assertTrue([d for lv, _f, r, d in run.lines if (lv, r) == ("SKIPPED", "SEND") and "GET" in d], run.lines)
        self.assertEqual(run.data["network"]["consented"], 0)
        run = self.consent("form-method-shadowed-post.html")
        self.assertEqual(run.code, 0, (run.err, run.lines))
        self.assertEqual([p for _m, p in run.posts()], ["/lead"])

    def test_a_tracking_post_fired_by_the_click_does_not_take_the_single_send(self):
        run = self.consent("form-clickhook.html")
        self.assertEqual(run.code, 0, (run.err, run.lines))
        self.assertEqual([p for _m, p in run.posts()], ["/lead"])
        self.assertTrue(run.logged("/api/event", "blocked", "consent:"), run.log)
        self.assertEqual(run.data["network"]["consented"], 1)
        self.assertEqual(sum(1 for e in run.log if e["outcome"] == "consented" and e["url"].endswith("/lead")), 1)

    def test_a_form_with_no_email_field_skips_the_send_and_names_the_address(self):
        run = self.consent("form-no-email.html")
        self.assertEqual(run.code, 3, (run.err, run.lines))
        self.assertTrue([d for lv, _f, r, d in run.lines if (lv, r) == ("SKIPPED", "SEND") and "carried the address" in d], run.lines)
        self.assertEqual(run.data["network"]["consented"], 0)
        self.assertEqual(run.posts(), [])

    def closed_run(self, patched):
        with mock.patch.object(form_consent, patched[0], patched[1]):
            return self.in_process(FakeTerminal(False), loopback=form_consent.LOOPBACK)

    def test_a_page_that_closes_after_the_send_is_never_reported_as_nothing_sent(self):
        # the page is closed once the consented request has been answered, before the picture: the next wait on the page raises
        real = form_consent.snap_form

        def close_then_picture(page, i, path):
            page.close()
            return real(page, i, path)

        run = self.closed_run(("snap_form", close_then_picture))
        self.assertEqual(run.code, 0, (run.out, run.err))
        self.assertEqual([p for _m, p in run.posts()], ["/lead"])
        self.assertTrue(run.form["submit"]["pressed"], run.form["submit"])
        self.assertTrue([d for lv, _f, r, d in run.lines if (lv, r) == ("WARN", "SEND") and "could not be read" in d and "lead arrived" in d],
                        run.lines)
        self.assertNotIn("nothing was sent", run.out + run.err)
        self.assertEqual(run.data["network"]["consented"], 1)
        self.assertEqual(run.data["forms"][0]["index"], 1)

    def test_a_page_that_closes_before_any_request_leaves_is_nothing_sent(self):
        # the page is closed in place of the press: no request leaves, the next wait on the page raises
        real = form_consent.press

        def close_then_press(page, i, info, limit_ms, stop=None, **keep):
            page.close()
            return real(page, i, info, limit_ms, stop, **keep)

        run = self.closed_run(("press", close_then_press))
        self.assertEqual(run.code, 3, (run.out, run.err))
        self.assertEqual(run.posts(), [])
        self.assertTrue([d for lv, _f, r, d in run.lines if (lv, r) == ("SKIPPED", "SEND") and "nothing was sent" in d], run.lines)
        self.assertEqual(run.data["forms"][0]["index"], 1)
        self.assertFalse(run.form["submit"]["pressed"], run.form["submit"])
        rows = [d for lv, _f, r, d in run.lines if (lv, r) == ("SKIPPED", "SEND")]
        self.assertEqual(len(rows), 1, run.lines)
        self.assertIn("the page could not be read after the press (Page.wait_for_timeout", rows[0])
        self.assertNotIn("may need a field", rows[0])

    def test_a_page_lost_inside_the_press_still_says_it_was_pressed(self):
        # the page is closed when the press has seen the change and not yet returned: the click is made, the form's host has not
        # answered (form-slower answers late) and the next read of the page raises inside press
        real = form_check.wait_for_state

        def lose_the_page(page, *args, **keep):
            found = real(page, *args, **keep)
            page.close()
            page.wait_for_timeout(1)
            return found

        with mock.patch.object(form_check, "wait_for_state", lose_the_page):
            run = self.in_process(FakeTerminal(False), page="form-slower.html", loopback=form_consent.LOOPBACK)
        self.assertEqual(run.code, 0, (run.out, run.err))
        self.assertEqual([p for _m, p in run.posts()], ["/lead-slower"])
        self.assertNotIn("nothing was sent", run.out + run.err)
        self.assertEqual(run.form["submit"]["pressed"], True)
        self.assertEqual(run.form["submit"]["state"], "none")
        rows = [d for lv, _f, r, d in run.lines if (lv, r) == ("WARN", "SEND")]
        self.assertEqual(len(rows), 1, run.lines)
        self.assertIn("the form's host had not answered yet", rows[0])
        self.assertNotIn("seconds after the press", rows[0])

    def test_a_defect_after_the_consent_was_opened_tells_the_reader_to_check_first(self):
        def broken(page, i, path):
            raise RuntimeError("defect")

        err = io.StringIO()
        folder = tempfile.mkdtemp(dir=self.tmp.name)
        with mock.patch.object(form_consent, "snap_form", broken), mock.patch.object(sys, "stdin", FakeTerminal(False)), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            with self.assertRaises(RuntimeError):
                form_consent.main(["%s/form-lead.html" % self.base, "--out", folder, *GOOD])
        self.assertIn("a submission may have been sent", err.getvalue())

    def test_an_interrupt_after_the_consent_was_opened_prints_the_line_and_goes_on(self):
        def interrupted(page, i, path):
            raise KeyboardInterrupt

        err = io.StringIO()
        folder = tempfile.mkdtemp(dir=self.tmp.name)
        with mock.patch.object(form_consent, "snap_form", interrupted), mock.patch.object(sys, "stdin", FakeTerminal(False)), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            with self.assertRaises(KeyboardInterrupt):
                form_consent.main(["%s/form-lead.html" % self.base, "--out", folder, *GOOD])
        self.assertIn("a submission may have been sent", err.getvalue())

    def test_a_307_after_the_consented_post_is_a_fail(self):
        run = self.consent("form-307.html")
        self.assertEqual(run.code, 1, (run.err, run.lines))
        self.assertTrue([d for lv, _f, r, d in run.lines if (lv, r) == ("FAIL", "SEND") and "redirect" in d], run.lines)
        self.assertEqual([p for _m, p in run.posts()], ["/lead-307", "/sink"])

    def test_an_ajax_form_whose_script_posts_elsewhere_warns_and_reports_the_send(self):
        run = self.consent("form-ajax.html")
        self.assertEqual(run.code, 0, (run.err, run.lines))
        self.assertEqual([p for _m, p in run.posts()], ["/api/lead"])
        self.assertTrue([d for lv, _f, r, d in run.lines if (lv, r) == ("WARN", "SEND") and "/api/lead" in d and "lead arrived" in d], run.lines)
        self.assertEqual(run.data["network"]["consented"], 1)
        self.assertNotIn("not sent", run.out)
        self.assertEqual([r for lv, _f, r, _d in run.lines if lv == "FAIL"], [])

    def test_a_post_redirect_get_to_the_same_path_is_not_a_second_send(self):
        run = self.consent("form-prg.html")
        self.assertEqual(run.code, 0, (run.err, run.lines))
        self.assertEqual([(m, p) for m, p, _a, _b in run.seen if p.startswith("/lead-prg")], [("POST", "/lead-prg"), ("GET", "/lead-prg")])
        self.assertEqual([lv for lv, _f, _r, _d in run.lines if lv == "FAIL"], [])
        self.assertEqual(run.data["network"]["consented"], 1)

    def test_a_form_with_no_method_is_refused_with_its_own_reason(self):
        run = self.consent("form-nomethod.html")
        self.assertEqual(run.code, 3, run.err)
        self.assertTrue([d for lv, _f, r, d in run.lines if (lv, r) == ("SKIPPED", "SEND") and "has no method" in d], run.lines)
        self.assertEqual([p for p in run.paths() if p.startswith("/lead-nm")], [])

    def test_a_page_with_no_form_or_two_forms_sends_nothing_and_exits_3(self):
        for page, flags in (("form-none.html", ()), ("form-two.html", ())):
            run = self.consent(page, *flags)
            self.assertEqual(run.code, 3, (page, run.err))
            self.assertIn("form_consent", run.err)
            self.assertEqual(run.posts(), [])
            self.assertEqual(run.data["network"]["consented"], 0)
        run = self.consent("form-two.html", "--form", "#second")
        self.assertEqual(run.code, 0, run.err)
        self.assertEqual(len(run.posts()), 1)
        self.assertEqual(run.data["forms"][0]["index"], 2)

    def test_the_read_pass_sends_nothing_before_the_press(self):
        run = self.consent("form-lead.html")
        first_post = next(i for i, (m, _p, _a, _b) in enumerate(run.seen) if m == "POST")
        self.assertEqual([m for m, _p, _a, _b in run.seen[:first_post]], ["GET"] * first_post)

    def test_a_slow_answer_is_waited_for(self):
        run = self.consent("form-slow.html")
        self.assertEqual(run.code, 0, (run.err, run.lines))
        self.assertEqual([p for _m, p in run.posts()], ["/lead-slow"])
        self.assertEqual([e["status"] for e in run.log if e["outcome"] == "consented"], [200])
        self.assertIn("Thanks", run.form["submit"]["status_text"])
        self.assertNotIn("Sending", run.form["submit"]["status_text"])
        self.assertGreaterEqual(run.form["submit"]["time_ms"], 1500)

    def test_a_page_that_moves_on_after_the_answer_is_read_as_navigated(self):
        run = self.consent("form-moves.html")
        self.assertEqual(run.code, 0, (run.out, run.err))
        self.assertEqual([p for _m, p in run.posts()], ["/lead-slow"])
        self.assertEqual(run.form["submit"]["state"], "navigated")
        self.assertTrue((run.form["thank_you"]["url"] or "").endswith("/form-thanks.html"), run.form["thank_you"])
        self.assertIn("Thank you", run.form["thank_you"]["text"])
        self.assertNotIn("Sending", run.form["thank_you"]["text"])
        self.assertGreaterEqual(run.form["submit"]["time_ms"], 1500)

    def test_a_form_that_shows_no_change_keeps_the_state_none(self):
        with mock.patch.object(form_consent, "WAIT_MS", 1500):
            run = self.in_process(FakeTerminal(False), page="form-quiet.html", loopback=form_consent.LOOPBACK)
        self.assertEqual(run.code, 0, run.out + run.err)
        self.assertEqual([p for _m, p in run.posts()], ["/lead"])
        self.assertEqual(run.form["submit"]["state"], "none")

    def test_a_late_post_is_waited_for(self):
        run = self.consent("form-late.html")
        self.assertEqual(run.code, 0, (run.out, run.err))
        self.assertEqual([p for _m, p in run.posts()], ["/lead"])

    def test_a_post_after_the_wait_is_not_sent(self):
        real = form_consent.snap_form

        def post_after_the_close(page, i, path):
            # snap_form runs after the consent is closed: a request of the page to the form's own address now is not the send
            page.evaluate("(email) => fetch('/lead', {method: 'POST', body: 'email=' + email}).catch(() => 0)", EMAIL)
            return real(page, i, path)

        with mock.patch.object(form_consent, "POST_WAIT_MS", 300), mock.patch.object(form_consent, "snap_form", post_after_the_close):
            run = self.in_process(FakeTerminal(False), page="form-silent.html", loopback=form_consent.LOOPBACK)
        self.assertEqual(run.code, 3, run.out + run.err)
        self.assertEqual(run.posts(), [])
        self.assertIn("nothing was sent", run.out)
        self.assertEqual(len(run.logged("/lead", "blocked", "method:")), 1, run.log)
        self.assertFalse([e for e in run.log if e["outcome"] == "consented"], run.log)

    def test_a_beacon_to_another_host_does_not_end_the_wait_for_the_form(self):
        run = self.consent("form-beacon-first.html")
        self.assertEqual(run.code, 0, (run.out, run.err))
        self.assertEqual([p for _m, p in run.posts()], ["/lead"])
        self.assertEqual(len(run.logged("localhost", "blocked")), 1, run.log)

    def test_an_unanswered_send_is_a_warning(self):
        with mock.patch.object(form_consent, "WAIT_MS", 1500):
            run = self.in_process(FakeTerminal(False), page="form-slower.html", loopback=form_consent.LOOPBACK)
        self.assertEqual(run.code, 0, run.out + run.err)
        self.assertEqual([p for _m, p in run.posts()], ["/lead-slower"])
        self.assertEqual(len([d for lv, _f, r, d in run.lines if (lv, r) == ("WARN", "SEND") and "had not answered" in d]), 1, run.lines)


@SKIP
class FormConsentLeakPaths(GuardLeakPathsMixin, unittest.TestCase):
    @classmethod
    def run_route(cls, url, out):
        done = subprocess.run([sys.executable, str(SCRIPT), url, "--out", str(out), *GOOD], capture_output=True, text=True, timeout=240)
        if done.returncode not in (0, 1, 3):
            raise RuntimeError("form_consent exited %d: %s" % (done.returncode, done.stderr))
        cls.errors_by_run[out.parent.name] = json.loads((out / "form.json").read_text(encoding="utf-8"))["errors"]
        return json.loads((out / "network-log.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
