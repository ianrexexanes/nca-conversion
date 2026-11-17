import json
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
LAUNCH = FIXTURES / "launch"
SCRIPT = HERE / "launch_render.py"
VARIANTS = FIXTURES / "deck-variants.md"

from guard_tests import SKIP, GuardLeakPathsMixin  # noqa: E402
import launch_render  # noqa: E402

LINE = re.compile(r"^(FAIL|WARN|SKIPPED) (\S+)@(\d+) ([A-Z][A-Z0-9_]*): (.*)$")


class _Pages(BaseHTTPRequestHandler):
    requests = []

    def do_GET(self):
        type(self).requests.append((self.command, self.path, self.headers.get("User-Agent", "")))
        name = self.path.split("?")[0].lstrip("/")
        target = LAUNCH / name
        if name == "mobile-only.html" and "Mobile" not in self.headers.get("User-Agent", ""):
            target = LAUNCH / "missing"  # a page that only the phone view can load
        if name and target.is_file() and target.parent == LAUNCH:
            body, status = target.read_bytes(), 200
        else:
            body, status = b"not found", 404
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_HEAD = do_OPTIONS = do_GET

    def log_message(self, *args):
        pass


def findings(stdout):
    """(level, page, width, rule, detail) for every finding line."""
    rows = []
    for text in stdout.splitlines():
        m = LINE.match(text)
        if m:
            rows.append((m.group(1), m.group(2), int(m.group(3)), m.group(4), m.group(5)))
    return rows


@SKIP
class LaunchRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _Pages)
        cls.server.daemon_threads = True
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = "http://127.0.0.1:%d" % cls.server.server_address[1]
        cls.addClassCleanup(cls.server.server_close)
        cls.addClassCleanup(cls.server.shutdown)

    def render(self, page, width, *flags):
        """Run the script over one fixture page at one width; return (exit code, stdout, findings)."""
        with tempfile.TemporaryDirectory() as tmp:
            done = subprocess.run([sys.executable, str(SCRIPT), "%s/%s" % (self.base, page), "--out", tmp,
                                   "--widths", str(width), *flags], capture_output=True, text=True, timeout=180)
        self.assertIn(done.returncode, (0, 1), done.stderr)
        return done.returncode, done.stdout, findings(done.stdout)

    def has(self, rows, level, rule, width, detail=""):
        return any(r[0] == level and r[3] == rule and r[2] == width and detail in r[4] for r in rows)

    def levels(self, rows, rule):
        return {r[0] for r in rows if r[3] == rule}

    def test_a_headline_ratio_the_widest_view_could_not_check_is_skipped_on_the_narrower(self):
        with tempfile.TemporaryDirectory() as tmp:
            done = subprocess.run([sys.executable, str(SCRIPT), "%s/mobile-only.html" % self.base, "--out", tmp,
                                   "--widths", "375,1440"], capture_output=True, text=True, timeout=180)
        self.assertIn(done.returncode, (0, 1), done.stderr)
        rows = findings(done.stdout)
        self.assertTrue(self.has(rows, "SKIPPED", "HEADLINE_RATIO", 375, "did not load"), done.stdout)
        self.assertTrue(self.has(rows, "FAIL", "STATUS", 1440), done.stdout)

    def test_forty_small_footer_links_are_one_warning_row_for_the_view(self):
        _c, out, rows = self.render("forty-footer-links.html", 390)
        small = [r for r in rows if r[0] == "WARN" and r[3] == "TARGET" and r[2] == 390]
        self.assertEqual(len(small), 1, out)
        self.assertIn("40", small[0][4], out)

    def test_horizontal_scroll_fails(self):
        code, out, rows = self.render("wide.html", 375)
        self.assertTrue(self.has(rows, "FAIL", "SCROLL", 375), out)
        self.assertEqual(code, 1)

    def test_small_body_text_fails(self):
        _c, out, rows = self.render("small.html", 1440)
        self.assertTrue(self.has(rows, "FAIL", "BODY_TEXT", 1440), out)

    def test_two_h1_fail(self):
        _c, out, rows = self.render("two-h1.html", 1440)
        self.assertTrue(self.has(rows, "FAIL", "H1", 1440), out)

    def test_missing_alt_fails(self):
        _c, out, rows = self.render("no-alt.html", 1440)
        self.assertTrue(self.has(rows, "FAIL", "ALT", 1440), out)

    def test_variant_label_below_first_screen_fails(self):
        _c, out, rows = self.render("late-button.html", 1440, "--deck", str(VARIANTS), "--variant", "b")
        self.assertTrue(self.has(rows, "FAIL", "LABEL_FOLD", 1440, "p.cta.hook.b"), out)

    def test_a_label_with_a_no_break_space_is_found_on_the_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            deck = Path(tmp) / "deck.md"
            deck.write_text(VARIANTS.read_text(encoding="utf-8").replace("p.cta.button: Book my pump check", "p.cta.button: Book my pump check\u202f!", 1), encoding="utf-8")
            _c, out, rows = self.render("label-spaces.html", 1440, "--deck", str(deck), "--variant", "c")
        self.assertFalse(self.has(rows, "FAIL", "LABEL_FOLD", 1440), out)
        self.assertFalse(self.has(rows, "FAIL", "ONE_TARGET", 1440), out)

    def test_a_label_in_a_hidden_container_is_not_the_label_in_the_first_screen(self):
        _c, out, rows = self.render("hidden-label.html", 1440, "--deck", str(VARIANTS), "--variant", "b")
        self.assertTrue(self.has(rows, "FAIL", "LABEL_FOLD", 1440, "p.cta.hook.b"), out)

    def test_a_link_in_a_hidden_menu_is_not_judged_for_target(self):
        _c, out, rows = self.render("hidden-menu.html", 390)
        self.assertFalse([r for r in rows if r[3] == "TARGET"], out)

    def test_a_page_that_is_not_found_fails_status(self):
        code, out, rows = self.render("no-such-page.html", 1440)
        self.assertTrue(self.has(rows, "FAIL", "STATUS", 1440, "HTTP 404"), out)
        self.assertEqual(code, 1)

    def test_every_action_button_shares_one_target(self):
        _c, out, rows = self.render("two-targets.html", 1440, "--deck", str(VARIANTS), "--variant", "c")
        self.assertTrue(self.has(rows, "FAIL", "ONE_TARGET", 1440), out)
        self.assertFalse(self.has(rows, "FAIL", "LABEL_FOLD", 1440), out)
        _c, out, rows = self.render("clean.html", 1440, "--deck", str(VARIANTS), "--variant", "c")
        self.assertFalse(self.has(rows, "FAIL", "ONE_TARGET", 1440), out)

    def test_a_label_with_an_arrow_is_still_the_label(self):
        _c, out, rows = self.render("arrow-label.html", 1440, "--deck", str(VARIANTS), "--variant", "c")
        self.assertFalse(self.has(rows, "FAIL", "LABEL_FOLD", 1440, "no button or link shows it"), out)
        self.assertTrue(self.has(rows, "FAIL", "ONE_TARGET", 1440), out)

    def test_a_label_with_a_word_added_is_not_the_label(self):
        _c, out, rows = self.render("label-plus-word.html", 1440, "--deck", str(VARIANTS), "--variant", "c")
        self.assertTrue(self.has(rows, "FAIL", "LABEL_FOLD", 1440, "no button or link shows it"), out)

    def test_a_button_inside_a_link_is_one_call_to_action(self):
        _c, out, rows = self.render("button-in-link.html", 1440, "--deck", str(VARIANTS), "--variant", "c")
        self.assertFalse(self.has(rows, "FAIL", "ONE_TARGET", 1440), out)

    def test_a_link_inside_a_role_button_goes_where_the_link_goes(self):
        _c, out, rows = self.render("link-in-role-button.html", 1440, "--deck", str(VARIANTS), "--variant", "c")
        self.assertFalse(self.has(rows, "FAIL", "ONE_TARGET", 1440), out)

    def test_target_under_24_fails_and_under_44_warns(self):
        _c, out, rows = self.render("targets.html", 390)
        self.assertTrue(self.has(rows, "FAIL", "TARGET", 390, "button#tiny-a 20x20"), out)
        self.assertTrue(self.has(rows, "WARN", "TARGET", 390, "button#mid 30x30"), out)
        self.assertFalse(self.has(rows, "WARN", "TARGET", 390, "tiny-a"), out)

    def test_inline_link_is_not_a_target_finding(self):
        _c, out, rows = self.render("inline-link.html", 390)
        self.assertFalse([r for r in rows if r[3] == "TARGET" and "terms" in r[4]], out)

    def test_isolated_small_icon_button_passes_by_spacing(self):
        _c, out, rows = self.render("lone-icon.html", 390)
        self.assertFalse(self.has(rows, "FAIL", "TARGET", 390), out)
        self.assertTrue(self.has(rows, "WARN", "TARGET", 390, "button#icon 20x20"), out)

    def test_action_colour_on_a_non_action_fails(self):
        _c, out, rows = self.render("colour.html", 1440, "--action-color", "#0047b3")
        self.assertTrue(self.has(rows, "FAIL", "ACTION_COLOUR", 1440, "h2"), out)
        self.assertFalse(self.has(rows, "FAIL", "ACTION_COLOUR", 1440, "Book my pump check"), out)

    def test_oklch_panels_are_measured_not_read_as_transparent(self):
        _c, out, rows = self.render("oklch-dark.html", 1440)
        self.assertFalse(self.has(rows, "FAIL", "CONTRAST", 1440), out)
        self.assertFalse(self.has(rows, "SKIPPED", "CONTRAST", 1440), out)
        _c, out, rows = self.render("oklch-pale.html", 1440)
        fails = [r for r in rows if r[0] == "FAIL" and r[3] == "CONTRAST"]
        self.assertTrue(fails, out)
        self.assertNotIn("on #ffffff", fails[0][4], out)

    def test_color_function_matches_the_action_colour(self):
        _c, out, rows = self.render("color-fn.html", 1440, "--action-color", "#0047B3")
        self.assertTrue(self.has(rows, "FAIL", "ACTION_COLOUR", 1440, "h2"), out)

    def test_page_error_fails(self):
        _c, out, rows = self.render("throws.html", 1440)
        self.assertTrue(self.has(rows, "FAIL", "PAGE_ERROR", 1440, "page says boom"), out)

    def test_a_failed_network_call_after_a_blocked_request_is_a_warning(self):
        _c, out, rows = self.render("post-on-load.html", 1440)
        self.assertTrue(self.has(rows, "WARN", "PAGE_ERROR", 1440, "the guard blocked 1 request(s) on this view, so this may be its own doing: confirm in an ordinary browser"), out)
        self.assertFalse(self.has(rows, "FAIL", "PAGE_ERROR", 1440), out)

    def test_a_failed_network_call_where_nothing_was_blocked_still_fails(self):
        _c, out, rows = self.render("get-fails.html", 1440)
        self.assertTrue(self.has(rows, "FAIL", "PAGE_ERROR", 1440, "Failed to fetch"), out)
        self.assertFalse(self.has(rows, "WARN", "PAGE_ERROR", 1440), out)

    def test_a_page_error_with_blocked_requests_but_no_network_text_still_fails(self):
        _c, out, rows = self.render("throws.html", 1440)
        self.assertTrue(self.has(rows, "FAIL", "PAGE_ERROR", 1440, "page says boom"), out)

    def test_body_black_warns(self):
        _c, out, rows = self.render("black.html", 1440)
        self.assertTrue(self.has(rows, "WARN", "BODY_BLACK", 1440), out)

    def test_headline_ratio_warns(self):
        _c, out, rows = self.render("ratio.html", 1440)
        self.assertTrue(self.has(rows, "WARN", "HEADLINE_RATIO", 1440), out)
        _c, out, rows = self.render("clean.html", 1440)
        self.assertFalse(self.levels(rows, "HEADLINE_RATIO"), out)

    def test_low_contrast_text_on_a_solid_background_fails(self):
        _c, out, rows = self.render("contrast.html", 1440)
        self.assertTrue(self.has(rows, "FAIL", "CONTRAST", 1440, "#999999"), out)

    def test_text_on_an_image_is_listed_not_measured(self):
        _c, out, rows = self.render("on-image.html", 1440)
        self.assertTrue(self.has(rows, "SKIPPED", "CONTRAST", 1440), out)
        self.assertFalse(self.has(rows, "FAIL", "CONTRAST", 1440), out)

    def test_missing_nav_warns_unless_landing(self):
        _c, out, rows = self.render("no-nav.html", 1440)
        self.assertTrue(self.has(rows, "WARN", "NAV", 1440), out)
        _c, out, rows = self.render("no-nav.html", 1440, "--landing")
        self.assertFalse(self.levels(rows, "NAV"), out)

    def test_autoplay_video_warns(self):
        _c, out, rows = self.render("autoplay.html", 1440)
        self.assertTrue(self.has(rows, "WARN", "AUTOPLAY", 1440), out)

    def test_slider_markup_warns(self):
        _c, out, rows = self.render("slider.html", 1440)
        self.assertTrue(self.has(rows, "WARN", "SLIDER", 1440), out)

    def test_sends_an_ordinary_chrome_agent(self):
        _Pages.requests.clear()
        self.render("clean.html", 1440)
        agents = [ua for _m, _p, ua in _Pages.requests]
        self.assertTrue(agents)
        self.assertTrue(all("Chrome/" in ua and "HeadlessChrome" not in ua for ua in agents), agents)

    def test_clean_page_passes_at_four_widths(self):
        with tempfile.TemporaryDirectory() as tmp:
            done = subprocess.run([sys.executable, str(SCRIPT), self.base + "/clean.html", "--out", tmp],
                                  capture_output=True, text=True, timeout=240)
            data = json.loads((Path(tmp) / "launch.json").read_text(encoding="utf-8"))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(done.stdout.strip().splitlines()[-1], "launch_render: 0 FAIL, 0 WARN", done.stdout)
        self.assertEqual([v["width"] for v in data["pages"][0]["views"]], [375, 390, 820, 1440])
        self.assertEqual(data["widths"], [375, 390, 820, 1440])


class LaunchRenderThresholdTests(unittest.TestCase):
    """The measured limits, on synthetic facts with no browser: each one at its edge."""

    def targets(self, size):
        one = {"name": "button#a", "x": 0, "y": 0, "w": size, "h": size, "parent": -1, "inline": False}
        two = dict(one, name="button#b", x=size - 4)  # a neighbour overlapping it, so the spacing exception does not apply
        return launch_render.target_findings([one, two])

    def test_target_boundaries_24_and_44(self):
        self.assertEqual({r[0] for r in self.targets(23.99)}, {"FAIL"})
        self.assertEqual({r[0] for r in self.targets(24)}, {"WARN"})
        self.assertEqual({r[0] for r in self.targets(43.99)}, {"WARN"})
        self.assertEqual(self.targets(44), [])

    def contrast_rows(self, colour, large):
        facts = {"scroll": {"scroll_width": 100, "client_width": 100}, "body_text": [], "h1": [{"name": "h1", "size": 40}], "images_without_alt": [],
                 "viewport": {"w": 390, "h": 800}, "candidates": [], "targets": [], "contrast_skipped": [], "has_nav": True, "autoplay": [],
                 "sliders": [], "body_element": {"color": "rgb(34, 34, 34)", "size": 18},
                 "contrast": [{"name": "p", "fg": colour, "bg": "#ffffff", "large": large}]}
        args = type("Args", (), {"label": None, "action_color": None, "landing": False})()
        return [r for r in launch_render.analyse(facts, args, 1440, 390, "") if r[1] == "CONTRAST"]

    def test_large_text_needs_three_to_one(self):
        self.assertEqual(len(self.contrast_rows("#777777", False)), 1)  # 4.48:1 small text is under 4.5
        self.assertEqual(self.contrast_rows("#767676", False), [])  # 4.54:1
        self.assertEqual(self.contrast_rows("#777777", True), [])  # the same grey is enough at large size
        self.assertEqual(self.contrast_rows("#929292", True), [])  # 3.11:1
        self.assertEqual(len(self.contrast_rows("#959595", True)), 1)  # 2.995:1 large text is under 3


@SKIP
class LaunchRenderInputTests(unittest.TestCase):
    def bad(self, *args):
        done = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertTrue(done.stderr.startswith("launch_render: "), done.stderr)

    def test_bad_input_exits_2_before_a_browser_opens(self):
        with tempfile.TemporaryDirectory() as tmp:
            url = "http://127.0.0.1:9/x.html"
            self.bad("--out", tmp)
            self.bad(url)
            self.bad(url, "--out", tmp, "--widths", "375,abc")
            self.bad(url, "--out", tmp, "--widths", "0")
            self.bad(url, "--out", tmp, "--variant", "a")
            self.bad(url, "--out", tmp, "--deck", str(Path(tmp) / "missing.md"))
            self.bad(url, "--out", tmp, "--deck", str(VARIANTS))
            self.bad(url, "--out", tmp, "--deck", str(VARIANTS), "--variant", "z")
            self.bad(url, "--out", tmp, "--action-color", "blue")

    def test_an_action_colour_with_a_trailing_line_break_is_bad_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            done = subprocess.run([sys.executable, str(SCRIPT), "http://127.0.0.1:9/x.html", "--out", tmp,
                                   "--action-color", "#abc\n"], capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertIn("--action-color must be #rgb or #rrggbb", done.stderr)
        self.assertNotIn("Traceback", done.stderr)


    def test_a_page_address_that_is_not_an_address_is_bad_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            done = subprocess.run([sys.executable, str(SCRIPT), "not a url", "--out", tmp],
                                  capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertIn("launch_render: the page address must start with http:// or https://", done.stderr)
        self.assertNotIn("Traceback", done.stderr)


@SKIP
class LaunchRenderLeakPaths(GuardLeakPathsMixin, unittest.TestCase):
    @classmethod
    def run_route(cls, url, out):
        done = subprocess.run([sys.executable, str(SCRIPT), url, "--out", str(out), "--widths", "390,1440"],
                              capture_output=True, text=True, timeout=240)
        if done.returncode not in (0, 1):
            raise RuntimeError("launch_render exited %d: %s" % (done.returncode, done.stderr))
        cls.errors_by_run[out.parent.name] = json.loads((out / "launch.json").read_text(encoding="utf-8"))["errors"]
        return json.loads((out / "network-log.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
