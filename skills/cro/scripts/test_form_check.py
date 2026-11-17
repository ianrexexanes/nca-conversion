import json
import struct
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "form_check.py"

import form_check  # noqa: E402
from form_tests import FormServer, run_script, start_server  # noqa: E402
from guard_tests import SKIP, GuardLeakPathsMixin  # noqa: E402


class TripwireTests(unittest.TestCase):
    """form_check.tripwire over stub log entries: when FAIL SENT appears and when it does not."""

    ACTION = "https://forms.example.com/lead"

    def sent(self, *entries, marks=None):
        rows = [{"url": u, "method": m, "resource_type": r, "outcome": o} for u, m, r, o in entries]
        recorder = type("Recorder", (), {"entries": rows, "finish": lambda self: rows})()
        session = type("Session", (), {"recorders": [recorder]})()
        first = {"issues": []}
        form_check.tripwire({0: first}, session, {form_check.address(self.ACTION)}, marks or {})
        return [i for i in first["issues"] if (i["level"], i["rule"]) == ("FAIL", "SENT")]

    def test_a_non_get_that_was_not_blocked_is_a_sent_fail(self):
        for outcome in ("completed", "continued", "failed", None):
            self.assertEqual(len(self.sent(("https://forms.example.com/x", "POST", "fetch", outcome))), 1, outcome)

    def test_a_get_to_the_action_address_that_was_not_blocked_is_a_sent_fail(self):
        self.assertEqual(len(self.sent((self.ACTION + "?a=1", "GET", "document", "completed"))), 1)

    def test_blocked_requests_websockets_and_ordinary_gets_are_not(self):
        self.assertEqual(self.sent(("https://forms.example.com/x", "POST", "fetch", "blocked"), (self.ACTION, "GET", "document", "blocked"),
                                   ("wss://forms.example.com/s", "GET", "websocket", None), ("https://forms.example.com/page", "GET", "document", "completed"),
                                   ("https://forms.example.com/page", "OPTIONS", "fetch", "completed")), [])


class WaitForStateStopTests(unittest.TestCase):
    """form_check.wait_for_state over a stand-in page, no browser."""

    class Page:
        def wait_for_timeout(self, ms):
            time.sleep(ms / 1000)

    def test_a_stop_ends_the_wait_while_the_page_is_held(self):
        started = time.monotonic()
        result = form_check.wait_for_state(self.Page(), 0, None, started, 3000, stop=lambda elapsed: True, hold=lambda: True)
        self.assertEqual(result[0], "none")
        self.assertLess(time.monotonic() - started, 1.0)


class BoundedReadFlagTests(unittest.TestCase):
    """form_check.safe_eval with the bound set, over a stand-in page, no browser."""

    class Handle:
        def json_value(self):
            return {"value": "answer"}

    class Page:
        def __init__(self, error):
            self.calls = 0
            self.error = error

        def wait_for_function(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                raise self.error("Timeout 3000ms exceeded")
            return BoundedReadFlagTests.Handle()

    def test_a_read_that_is_answered_clears_the_flag_a_missed_read_set(self):
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        self.addCleanup(lambda: setattr(form_check, "READ_BOUND_MS", None))
        self.addCleanup(lambda: setattr(form_check, "READ_MISSED", False))
        form_check.READ_BOUND_MS, form_check.READ_MISSED = 3000, False
        page = self.Page(PlaywrightTimeoutError)
        self.assertEqual(form_check.safe_eval(page, "() => 1", None, "default"), "default")
        self.assertIs(form_check.READ_MISSED, True)
        self.assertEqual(form_check.safe_eval(page, "() => 1", None, "default"), "answer")
        self.assertIs(form_check.READ_MISSED, False)


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

    def test_a_popup_request_to_the_action_address_is_aborted_too(self):
        # the page saved window.open before the press, so the press's own neutralising does not reach it; the popup is a second page
        run = self.run_page("form-popup.html")
        self.assertEqual(run.code, 0, run.err)
        self.assertEqual([(m, p) for m, p, _a, _b in run.seen if p.startswith("/lead")], [])
        self.assertTrue(run.logged("/lead", "blocked", "form:action"), run.log)

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

    def test_a_hidden_status_region_has_no_text_until_it_is_shown(self):
        for answer, phrase in (("success", "Thanks"), ("error", "went wrong")):
            run = self.run_page("form-hidden-status.html", "--simulate", answer)
            self.assertEqual(run.code, 0, (run.out, run.err))
            submit = run.form["submit"]
            self.assertEqual(submit["state"], "changed", answer)
            self.assertIn(phrase, submit["status_text"], answer)
            self.assertEqual(len(submit["regions"]), 2, submit["regions"])

    def test_a_rendered_region_whose_children_are_hidden_has_no_text(self):
        run = self.run_page("form-hidden-children.html", "--simulate", "success")
        self.assertEqual(run.code, 0, (run.out, run.err))
        submit = run.form["submit"]
        self.assertEqual(submit["state"], "changed")
        for text in [submit["status_text"]] + [r["text"] for r in submit["regions"]]:
            self.assertNotIn("went wrong", text)
            self.assertNotIn("we reply soon", text)

    def test_the_status_source_says_where_the_outcome_text_came_from(self):
        hero = "Our pump maintenance team keeps your plant running"
        run = self.run_page("form-plain-message.html", "--simulate", "success")
        self.assertEqual(run.code, 0, (run.out, run.err))
        submit = run.form["submit"]
        self.assertEqual(submit["state"], "changed")
        self.assertEqual(submit.get("status_source"), "form", submit)
        self.assertIn("Thanks, we reply within one working day.", submit["status_text"])
        self.assertFalse(submit["status_text"].startswith(hero), submit["status_text"])
        self.assertLessEqual(len(submit["status_text"]), 600)
        self.assertEqual(run.form["thank_you"]["text"], submit["status_text"])
        self.assertEqual(self.run_page("form-lead.html", "--simulate", "success").form["submit"].get("status_source"), "region")
        moved = self.run_page("form-moves-news.html", "--simulate", "success").form
        self.assertEqual(moved["submit"].get("status_source"), "page", moved["submit"])
        self.assertEqual(moved["thank_you"]["text"], moved["submit"]["status_text"])

    def test_a_form_hidden_on_success_reads_the_thank_you_from_the_page(self):
        run = self.run_page("form-hidden-on-success.html", "--simulate", "success")
        self.assertEqual(run.code, 0, (run.out, run.err))
        submit = run.form["submit"]
        self.assertEqual(submit["state"], "changed", submit)
        self.assertEqual(submit.get("status_source"), "page", submit)
        self.assertIn("Thanks, we will reply within one day.", submit["status_text"] or "")
        self.assertEqual(run.form["thank_you"]["text"], submit["status_text"])

    def test_a_form_faded_out_by_opacity_alone_reads_the_thank_you_from_the_page(self):
        run = self.run_page("form-faded-on-success.html", "--simulate", "success")
        self.assertEqual(run.code, 0, (run.out, run.err))
        submit = run.form["submit"]
        self.assertEqual(submit["state"], "changed", submit)
        self.assertEqual(submit.get("status_source"), "page", submit)
        self.assertIn("Thanks, we will reply within one day.", submit["status_text"] or "")

    def test_a_form_revealed_by_the_press_is_not_a_change_and_the_real_answer_is_waited_for(self):
        run = self.run_page("form-revealed-on-press.html", "--simulate", "success")
        self.assertEqual(run.code, 0, (run.out, run.err))
        submit = run.form["submit"]
        self.assertEqual(submit["state"], "changed", submit)
        self.assertEqual(submit.get("status_source"), "region", submit)
        self.assertEqual(submit["status_text"], "Thanks, we will reply within one day.", submit)
        self.assertGreaterEqual(submit["time_ms"], 700, submit)

    def test_a_press_that_changes_nothing_reports_no_outcome_text(self):
        run = self.run_page("form-quiet.html")
        self.assertEqual(run.code, 0, (run.out, run.err))
        submit = run.form["submit"]
        self.assertEqual(submit["state"], "none")
        self.assertIsNone(submit["status_text"])
        self.assertEqual(submit.get("status_source"), "none", submit)
        self.assertIsNone(run.form["thank_you"]["text"])

    def test_nothing_is_read_from_a_form_of_the_new_document_after_a_navigation(self):
        run = self.run_page("form-moves-news.html", "--simulate", "success")
        self.assertEqual(run.code, 0, (run.out, run.err))
        submit = run.form["submit"]
        self.assertEqual(submit["state"], "navigated")
        self.assertEqual(submit["validation"], [])

    def test_a_screen_reader_only_live_region_keeps_its_text(self):
        run = self.run_page("form-sr-live.html", "--simulate", "success")
        self.assertEqual(run.code, 0, (run.out, run.err))
        self.assertEqual(run.form["submit"]["state"], "changed")
        self.assertIn("Thanks", run.form["submit"]["status_text"])

    def test_a_form_the_page_removed_is_not_replaced_by_the_next_form(self):
        run = self.run_page("form-replaced.html", "--simulate", "success", "--form", "#lead")
        self.assertEqual(run.code, 0, (run.out, run.err))
        submit = run.form["submit"]
        self.assertEqual(submit["state"], "changed")
        self.assertIn("Thank you, your pump check request", submit["status_text"])
        self.assertEqual([row["field"] for row in submit["validation"]], [])
        # the second form is 400 px wide in the fixture: a picture of it is 400 px wide, the whole page is as wide as the 1440 px window
        header = (run.dir / "form1-simulate-success.png").read_bytes()[16:24]
        width, _height = struct.unpack(">II", header)
        self.assertEqual(width, 1440)

    def test_simulate_success_reaches_the_thank_you_state_and_sends_nothing(self):
        self.check_simulated("success", "Thanks")

    def test_simulate_error_shows_the_error_state_and_sends_nothing(self):
        self.check_simulated("error", "went wrong")

    def test_url_like_text_field_gets_a_url(self):
        def field(**over):
            base = {"index": 0, "name": None, "id": None, "label": None, "type": "text", "required": True, "autocomplete": None,
                    "inputmode": None, "visible": True, "disabled": False, "readonly": False, "maxlength": None, "value": None,
                    "first_option": None}
            return dict(base, **over)
        cases = {"inputmode": field(name="site", inputmode="url"), "autocomplete": field(name="site", autocomplete="section-x url"),
                 "name": field(name="website"), "id": field(id="homepage-link"), "label": field(label="Your URL")}
        for what, f in cases.items():
            plan = form_check.plan_fill([f], "free text line", None)
            self.assertEqual([v for _f, _a, v in plan], ["https://example.com"], what)
        mail = form_check.plan_fill([field(name="email", label="Website email")], "free text line", "me@example.com")
        self.assertEqual([v for _f, _a, v in mail], ["me@example.com"])
        plain = form_check.plan_fill([field(name="message", label="Currently using")], "free text line", None)
        self.assertEqual([v for _f, _a, v in plain], ["free text line"])

    def test_simulation_presses_past_a_url_pattern(self):
        run = self.run_page("form-url-pattern.html", "--simulate", "success")
        self.assertEqual(run.code, 0, run.err)
        submit = run.form["submit"]
        self.assertTrue(submit["pressed"], submit)
        self.assertEqual(submit["validation"], [])
        self.assertEqual(submit["state"], "changed")
        self.assertIn("Thanks", submit["status_text"])
        self.assertEqual(run.form["filled"]["website"], "https://example.com")
        self.assertEqual(run.posts(), [])

    def test_fill_that_breaks_a_pattern_is_named_before_the_press(self):
        run = self.run_page("form-code-pattern.html", "--simulate", "success")
        self.assertEqual(run.code, 0, run.err)
        submit = run.form["submit"]
        self.assertFalse(submit["pressed"], submit)
        self.assertEqual([v["field"] for v in submit["validation"]], ["code"])
        self.assertTrue(submit["validation"][0]["message"], submit)
        self.assertIn(("WARN", "FILL"), run.rules(), run.lines)
        detail = [d for lv, _f, r, d in run.lines if (lv, r) == ("WARN", "FILL")][0]
        self.assertIn("the test data does not satisfy code (", detail)
        self.assertIn("the form was not pressed", detail)
        self.assertEqual(run.posts(), [])
        self.assertEqual(run.paths().count("/lead"), 0)

    def test_simulate_on_a_form_that_posts_elsewhere_is_skipped(self):
        run = self.run_page("form-fetch.html", "--simulate", "success")
        self.assertEqual(run.code, 0, run.err)
        self.assertTrue([d for lv, _f, r, d in run.lines if (lv, r) == ("SKIPPED", "SIMULATE") and "/api/lead" in d], run.lines)
        self.assertEqual(run.posts(), [])

    def test_simulate_on_a_form_whose_press_sends_nothing_is_skipped(self):
        run = self.run_page("form-nosend.html", "--simulate", "success")
        self.assertEqual(run.code, 0, run.err)
        self.assertTrue([d for lv, _f, r, d in run.lines if (lv, r) == ("SKIPPED", "SIMULATE") and "the press sent nothing" in d], run.lines)
        self.assertEqual(run.paths().count("/lead"), 0)
        self.assertEqual(run.posts(), [])

    def test_the_simulated_state_is_the_one_after_the_reply(self):
        run = self.run_page("form-slow.html", "--simulate", "success")
        self.assertEqual(run.code, 0, (run.out, run.err))
        text = run.form["submit"]["status_text"]
        self.assertIn("Thanks", text)
        self.assertNotIn("Sending", text)
        self.assertEqual(run.posts(), [])

    def test_a_form_without_a_script_is_not_simulated(self):
        for answer in ("success", "error"):
            run = self.run_page("form-noscript.html", "--simulate", answer)
            self.assertEqual(run.code, 0, (run.out, run.err))
            self.assertTrue([d for lv, _f, r, d in run.lines if (lv, r) == ("SKIPPED", "SIMULATE") and "without a script" in d], run.lines)
            self.assertNotIn("Simulated answer", json.dumps(run.form["thank_you"]))
            self.assertIsNone(run.form["thank_you"]["text"])
            self.assertIsNone(run.form["thank_you"]["url"])
            self.assertFalse((run.dir / ("form1-simulate-%s.png" % answer)).exists())
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

    def test_an_address_that_cannot_be_parsed_is_bad_input_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            done = subprocess.run([sys.executable, str(SCRIPT), "http://[::1", "--out", tmp], capture_output=True, text=True, timeout=60)
            self.assertEqual(done.returncode, 2, done.stderr)
            self.assertTrue(done.stderr.startswith("form_check: "), done.stderr)
            self.assertNotIn("Traceback", done.stderr)


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
