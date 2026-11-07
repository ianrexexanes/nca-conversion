import contextlib
import io
import json
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

import cro_runtime  # noqa: E402
from form_tests import FormServer, run_script, start_server  # noqa: E402
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
        self.assertIsInstance(run.form["submit"]["time_ms"], int)
        self.assertEqual(run.form["submit"]["state"], "changed")
        self.assertIn("Thanks", run.form["submit"]["status_text"])
        self.assertTrue((run.dir / "form1-consented.png").is_file())
        for _m, _p, agent, _b in run.seen:
            self.assertIn("Chrome/", agent)
            self.assertNotIn("Headless", agent)

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
        run = self.consent("form-analytics.html")
        self.assertEqual(run.code, 3, run.err)
        self.assertTrue([d for lv, _f, r, d in run.lines if (lv, r) == ("SKIPPED", "SEND") and "google-analytics.com" in d],
                        run.lines)
        self.assertEqual(run.data["network"]["consented"], 0)
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
