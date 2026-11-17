import contextlib
import io
import json
import os
import pty
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "form_consent.py"
sys.path.insert(0, str(HERE))

import clarity_export  # noqa: E402
import cro_runtime  # noqa: E402
import form_consent  # noqa: E402
from form_tests import FormServer, Run, run_script, start_server  # noqa: E402
from guard_tests import SKIP, GuardLeakPathsMixin  # noqa: E402

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

    def test_a_missing_flag_or_address_exits_2_and_names_the_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            for argv in ([], ["http://127.0.0.1:9/x.html", "--out", tmp], ["http://127.0.0.1:9/x.html", "--out", tmp, *GOOD[:4]]):
                done = subprocess.run([sys.executable, str(SCRIPT), *argv], capture_output=True, text=True, timeout=60)
                self.assertEqual(done.returncode, 2, argv)
                self.assertIn("form_consent", done.stderr)


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
        cls.server, cls.base = start_server()
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
