import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "form_check.py"

from form_tests import FormServer, run_script, start_server  # noqa: E402
from guard_tests import SKIP, GuardLeakPathsMixin  # noqa: E402


@SKIP
class FormCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.base = start_server()
        cls.addClassCleanup(cls.server.server_close)
        cls.addClassCleanup(cls.server.shutdown)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.cache = {}

    def run_page(self, page, *flags):
        """Run the script over a fixture page; the same page and flags run once and share the result."""
        key = (page, flags)
        if key not in self.cache:
            self.cache[key] = run_script(SCRIPT, "%s/%s" % (self.base, page), *flags, tmp=self.tmp.name)
        return self.cache[key]

    def test_read_only_sends_nothing(self):
        run = self.run_page("form-lead.html")
        self.assertEqual(run.code, 0, run.err)
        self.assertEqual(run.data["mode"], "read-only")
        self.assertEqual([p for p in run.paths() if p.startswith("/lead")], [])
        self.assertEqual([m for m, _p, _a, _b in run.seen if m not in ("GET", "HEAD")], [])
        self.assertEqual(run.data["network"]["consented"], 0)
        self.assertEqual(run.data["forms"][0]["submit"]["pressed"], True)
        self.assertTrue((run.dir / "form1-1440.png").is_file() and (run.dir / "form1-390.png").is_file())

    def test_get_form_action_is_blocked_in_read_only(self):
        run = self.run_page("form-get.html")
        self.assertEqual(run.code, 0, run.err)
        self.assertEqual([p for p in run.paths() if p.startswith("/lead-get")], [])
        self.assertTrue(run.logged("/lead-get", "blocked", "form:action"), run.log)
        self.assertEqual(run.form["method"], "get")

    def test_a_submit_controls_formaction_is_blocked_in_read_only_and_simulate(self):
        for flags in ((), ("--simulate", "success")):
            run = self.run_page("form-formaction.html", *flags)
            self.assertEqual(run.code, 0, (flags, run.err))
            self.assertEqual([p for p in run.paths() if p.startswith(("/real-get", "/lead-get"))], [], flags)
            self.assertTrue(run.logged("/real-get", "blocked", "form:"), (flags, run.log))

    def test_a_target_blank_get_form_never_reaches_its_address(self):
        for flags in ((), ("--simulate", "error")):
            run = self.run_page("form-blank.html", *flags)
            self.assertEqual(run.code, 0, (flags, run.err))
            self.assertEqual([p for p in run.paths() if p.startswith("/blank-get")], [], flags)
            self.assertTrue(run.logged("/blank-get", "blocked", "form:"), (flags, run.log))
            self.assertNotIn("SENT", [r for _l, _f, r, _d in run.lines])

    def test_fetch_post_without_action_is_blocked(self):
        run = self.run_page("form-fetch.html")
        self.assertEqual(run.code, 0, run.err)
        self.assertEqual(run.posts(), [])
        self.assertTrue(run.logged("/api/lead", "blocked", "method:POST"), run.log)
        self.assertTrue(run.form["action"].endswith("/form-fetch.html"), run.form["action"])

    def check_simulated(self, answer, phrase):
        run = self.run_page("form-lead.html", "--simulate", answer)
        self.assertEqual(run.code, 0, run.err)
        self.assertEqual(run.data["mode"], "simulate-" + answer)
        self.assertEqual(run.posts(), [])
        self.assertEqual([p for p in run.paths() if p.startswith("/lead")], [])
        self.assertTrue(run.logged("/lead", "blocked", "form:simulate"), run.log)
        submit = run.form["submit"]
        self.assertEqual(submit["state"], "changed")
        self.assertIn(phrase, submit["status_text"])
        self.assertIn(phrase, run.form["thank_you"]["text"])
        self.assertTrue((run.dir / ("form1-simulate-%s.png" % answer)).is_file())
        filled = run.form["filled"]
        self.assertEqual(filled["name"], "Test Person")
        self.assertTrue(filled["email"].endswith("@example.com"), filled)
        self.assertIn("simulated by form_check", filled["message"])
        self.assertEqual(run.data["network"]["consented"], 0)
        return run

    def test_simulate_success_reaches_the_thank_you_state_and_sends_nothing(self):
        self.check_simulated("success", "Thanks")

    def test_simulate_error_shows_the_error_state_and_sends_nothing(self):
        self.check_simulated("error", "went wrong")

    def test_simulate_on_a_form_that_posts_elsewhere_is_skipped(self):
        run = self.run_page("form-fetch.html", "--simulate", "success")
        self.assertEqual(run.code, 0, run.err)
        self.assertTrue([d for lv, _f, r, d in run.lines if (lv, r) == ("SKIPPED", "SIMULATE") and "/api/lead" in d], run.lines)
        self.assertEqual(run.posts(), [])

    def test_simulate_needs_one_form(self):
        run = self.run_page("form-two.html", "--simulate", "success")
        self.assertEqual(run.code, 3, run.err)
        self.assertIn("form_check", run.err)
        run = self.run_page("form-two.html", "--simulate", "success", "--form", "#second")
        self.assertEqual(run.code, 0, run.err)
        self.assertEqual(run.data["forms"][0]["index"], 2)
        self.assertEqual(run.posts(), [])
        self.assertTrue((run.dir / "form2-simulate-success.png").is_file())

    def test_a_form_that_matches_nothing_or_a_page_with_no_form_exits_3_with_the_files_written(self):
        for page, flags in (("form-none.html", ()), ("form-lead.html", ("--form", "#nothing-here"))):
            run = self.run_page(page, *flags)
            self.assertEqual(run.code, 3, run.err)
            self.assertIn("form_check", run.err)
            self.assertEqual(run.data["forms"], [])
            self.assertIsInstance(run.log, list)

    def test_fields_report_label_type_required_autocomplete(self):
        run = self.run_page("form-lead.html")
        fields = {f["id"]: f for f in run.form["fields"]}
        self.assertEqual(
            {i: (f["label"], f["type"], f["required"], f["autocomplete"], f["inputmode"], f["visible"]) for i, f in fields.items()},
            {"f-name": ("Your name", "text", True, "name", None, True),
             "f-email": ("Work email", "email", True, "email", "email", True),
             "f-msg": ("What should we look at?", "textarea", False, None, None, True)})
        self.assertEqual(sorted(fields["f-name"]), sorted(["name", "id", "label", "type", "required", "autocomplete", "inputmode", "visible"]))
        submit = run.form["submit"]
        self.assertTrue(submit["validation"], submit)
        self.assertIn("status", json.dumps(submit["regions"]))
        self.assertEqual(run.rules(), set())

    def test_the_thank_you_link_comes_from_a_redirect_field(self):
        run = self.run_page("form-redirect-field.html")
        self.assertTrue((run.form["thank_you"]["url"] or "").endswith("/form-thanks.html"), run.form["thank_you"])
        self.assertIsNone(self.run_page("form-lead.html").form["thank_you"]["url"])

    def test_more_than_four_fields_warns(self):
        self.assertIn(("WARN", "FIELD_COUNT"), self.run_page("form-five.html").rules())
        four = self.run_page("form-four.html")
        self.assertNotIn(("WARN", "FIELD_COUNT"), four.rules(), four.out)

    def test_visible_captcha_warns(self):
        self.assertEqual(self.run_page("form-captcha.html").rules(), {("WARN", "CAPTCHA")})
        self.assertEqual(self.run_page("form-captcha-hidden.html").rules(), set())

    def test_phone_width_targets_under_44_warn(self):
        run = self.run_page("form-small.html")
        lines = [d for lv, _f, r, d in run.lines if (lv, r) == ("WARN", "TARGET")]
        self.assertEqual(len(lines), 2, run.out)
        self.assertTrue(any(d.startswith("#tiny-name") and d.endswith("x30") for d in lines), lines)
        self.assertTrue(any(d.startswith("#tiny-send") and d.endswith("x30") for d in lines), lines)
        self.assertEqual(run.rules(), {("WARN", "TARGET")})

    def test_summary_line_counts_what_was_printed_and_issues_match(self):
        run = self.run_page("form-five.html")
        fails = sum(1 for l in run.lines if l[0] == "FAIL")
        warns = sum(1 for l in run.lines if l[0] == "WARN")
        self.assertEqual(run.out.strip().splitlines()[-1], "form_check: %d FAIL, %d WARN" % (fails, warns))
        issues = {(i["level"], i["rule"]) for i in run.form["issues"]}
        self.assertEqual(issues, run.rules(("FAIL", "WARN", "SKIPPED")))

    def test_analytics_blocked_in_every_mode(self):
        for flags in ((), ("--simulate", "success"), ("--simulate", "error")):
            run = self.run_page("form-lead.html", *flags)
            self.assertEqual(run.code, 0, run.err)
            self.assertFalse([p for p in run.paths() if p.startswith(("/gtm.js", "/g/collect"))], (flags, run.paths()))
            tags = [e for e in run.log if "/gtm.js" in e["url"] or "/g/collect" in e["url"]]
            self.assertTrue(tags, flags)
            self.assertEqual({e["outcome"] for e in tags}, {"blocked"}, flags)

    def test_user_agent_is_ordinary_chrome_in_every_mode(self):
        for flags in ((), ("--simulate", "success"), ("--simulate", "error")):
            run = self.run_page("form-lead.html", *flags)
            agents = [a for _m, _p, a, _b in run.seen]
            self.assertTrue(agents, flags)
            for agent in agents:
                self.assertIn("Chrome/", agent)
                self.assertNotIn("Headless", agent)

    def test_bad_input_exits_2_before_any_page_is_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            before = len(FormServer.requests)
            sentinel = self.base + "/form-bad-input.html"
            for argv in ([], ["--out", tmp], [sentinel], [sentinel, "--out", tmp, "--simulate", "maybe"],
                         ["ftp://example.com/x", "--out", tmp]):
                done = subprocess.run([sys.executable, str(SCRIPT), *argv], capture_output=True, text=True, timeout=60)
                self.assertEqual(done.returncode, 2, (argv, done.stderr))
                self.assertIn("form_check", done.stderr)
            self.assertEqual(len(FormServer.requests), before)


@SKIP
class FormCheckLeakPaths(GuardLeakPathsMixin, unittest.TestCase):
    @classmethod
    def run_route(cls, url, out):
        done = subprocess.run([sys.executable, str(SCRIPT), url, "--out", str(out)], capture_output=True, text=True, timeout=240)
        if done.returncode not in (0, 1, 3):
            raise RuntimeError("form_check exited %d: %s" % (done.returncode, done.stderr))
        cls.errors_by_run[out.parent.name] = json.loads((out / "form.json").read_text(encoding="utf-8"))["errors"]
        return json.loads((out / "network-log.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
