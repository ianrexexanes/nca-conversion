import ast
import os
import re
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import urlsplit

import cro_runtime

HERE = Path(__file__).resolve().parent


def chrome_pattern_blocks(pattern: str, url: str) -> bool:
    # Measured on 2026-11-06 through a DevTools session with Network.setBlockedURLs, in Playwright 1.62.0's
    # Chromium 151.0.7922.34 and in Chrome 157.0.8103.38, with identical results: "*" matches any text, every
    # other character (a "?" included) is literal, and the pattern is not anchored. Chrome finds the parts
    # between the "*" characters in the URL, in order, anywhere in it.
    position = 0
    for part in pattern.split("*"):
        found = url.find(part, position)
        if found < 0:
            return False
        position = found + len(part)
    return True


# Browser layer: Chrome reads each glob from lighthouse_block_patterns(); request layer: is_blocked().
# Meta's advanced-page image form with custom data is documented at
# https://developers.facebook.com/docs/meta-pixel/advanced/ (read 2026-11-07).
DOCUMENTED_FORMS = (
    "https://www.facebook.com/tr/?id=123&ev=PageView",
    "https://www.facebook.com/tr?id=123&ev=Lead",
    "https://facebook.com/tr/?id=1&ev=PageView",
    "https://www.facebook.com/tr?id=12345&ev=PageView&noscript=1",
    "https://example.com/tr/?id=123",
    "https://www.google.com/ccm/collect?en=page_view",
    "https://tags.example.com/ccm/collect?en=page_view",
    "https://tags.example.com/ccm/collect",
    "https://www.facebook.com/tr?id=12345&ev=ViewContent&cd[content_name]=Trail%20Shoe&cd[value]=0.50&cd[currency]=USD",
)
NEAR_MISSES = (
    "https://www.facebook.com/trending",
    "https://www.facebook.com/translate/x",
    "https://myfacebook.com/trade",
    "https://posthog.com/docs",
    "https://www.hubspot.com/",
    "https://www.pinterest.com/",
    "https://twitter.com/x",
    "https://example.com/products/shoes?id=7",
    "https://example.com/assets/app.js",
)
# The README's limits: Chrome reads a glob unanchored (see chrome_pattern_blocks), so a glob
# cannot anchor a host or end at a path; these are blocked in the browser layer and open to is_blocked().
README_LIMITS = (
    "https://example.com/ccm/collections",
    "https://myfacebook.com/tr/",
    "https://notgoogletagmanager.com/",
    "https://googletagmanager.com.example.org/",
)


def browser_layer_blocks(url):
    return any(chrome_pattern_blocks(pattern, url) for pattern in cro_runtime.lighthouse_block_patterns())


class BrowserLayerTest(unittest.TestCase):
    def test_browser_layer_blocks_the_documented_forms(self):
        for url in DOCUMENTED_FORMS:
            with self.subTest(url=url):
                self.assertTrue(browser_layer_blocks(url), "browser layer should block " + url)
                self.assertIsNotNone(cro_runtime.is_blocked(url), "request layer should block " + url)

    def test_browser_layer_keeps_the_near_misses_open(self):
        for url in NEAR_MISSES:
            with self.subTest(url=url):
                self.assertFalse(browser_layer_blocks(url), "browser layer should leave open " + url)
                self.assertIsNone(cro_runtime.is_blocked(url), "request layer should leave open " + url)

    def test_browser_layer_limits_are_the_readme_limits(self):
        for url in README_LIMITS:
            with self.subTest(url=url):
                self.assertTrue(browser_layer_blocks(url), "browser layer blocks " + url)
                self.assertIsNone(cro_runtime.is_blocked(url), "request layer leaves open " + url)


class IsBlockedTest(unittest.TestCase):
    def test_is_blocked_matches_third_party_hosts(self):
        self.assertEqual(cro_runtime.is_blocked("https://www.googletagmanager.com/gtag/js?id=G-X"), "host:googletagmanager.com")

    def test_uet_hosts_are_blocked(self):
        self.assertEqual(cro_runtime.is_blocked("https://bat.bing.net/action/0?ti=123&evt=pageLoad"), "host:bat.bing.net")
        self.assertEqual(cro_runtime.is_blocked("https://bat.bing.com/bat.js"), "host:bat.bing.com")
        self.assertIn("*bat.bing.net*", cro_runtime.lighthouse_block_patterns())

    def test_is_blocked_ignores_lookalike_hosts(self):
        # A suffix matches only on a dot boundary.
        self.assertIsNone(cro_runtime.is_blocked("https://notgoogletagmanager.com/"))
        self.assertIsNone(cro_runtime.is_blocked("https://googletagmanager.com.example.org/"))

    def test_is_blocked_matches_first_party_paths(self):
        for url in ("https://example.com/gtag/js?id=G-X", "https://sgtm.example.com/g/collect?v=2", "https://example.com/matomo.php"):
            rule = cro_runtime.is_blocked(url)
            self.assertIsNotNone(rule, url)
            self.assertTrue(rule.startswith("path:"), rule)

    def test_is_blocked_passes_ordinary_assets(self):
        self.assertIsNone(cro_runtime.is_blocked("https://example.com/assets/app.js"))

    def test_meta_pixel_paths_are_blocked_by_host_and_path(self):
        for url in ("https://www.facebook.com/tr/?id=123&ev=PageView", "https://www.facebook.com/tr?id=123&ev=PageView",
                    "https://example.com/tr/?id=123"):
            self.assertIsNotNone(cro_runtime.is_blocked(url), url)

    def test_facebook_tr_rule_matches_on_the_host(self):
        self.assertEqual(cro_runtime.is_blocked("https://www.facebook.com/tr/?ev=PageView"), "path:(^|\\.)facebook\\.com/tr/")

    def test_meta_pixel_still_blocked_after_anchoring(self):
        for url in ("https://www.facebook.com/tr/?id=123&ev=PageView", "https://www.facebook.com/tr?id=123&ev=Lead",
                    "https://facebook.com/tr/?id=1&ev=PageView",
                    # The image-tag form Meta documents: https://developers.facebook.com/documentation/meta-pixel/get-started
                    "https://www.facebook.com/tr?id=12345&ev=PageView&noscript=1"):
            self.assertIsNotNone(cro_runtime.is_blocked(url), url)

    def test_ordinary_addresses_near_tracker_paths_stay_open(self):
        for url in ("https://www.facebook.com/trending", "https://www.facebook.com/translate/x",
                    "https://myfacebook.com/trade", "https://example.com/ccm/collections"):
            self.assertIsNone(cro_runtime.is_blocked(url), url)

    def test_ccm_collect_blocked_on_a_first_party_host_too(self):
        # No Google page documents the /ccm/collect request or a gateway path for it, so the cases are the endpoint
        # on Google's host and on a first-party host, with and without a query.
        for url in ("https://www.google.com/ccm/collect?en=page_view", "https://tags.example.com/ccm/collect?en=page_view",
                    "https://tags.example.com/ccm/collect"):
            self.assertIsNotNone(cro_runtime.is_blocked(url), url)

    def test_chrome_pattern_reading_matches_the_probe(self):
        # The 17 results measured for the helper's comment: pattern, path, blocked.
        probe = (
            ("*/ccm/collect", "/ccm/collect", True), ("*/ccm/collect", "/ccm/collections", True),
            ("*/ccm/collect", "/ccm/collect/", True), ("*/ccm/collect", "/ccm/collect;x", True),
            ("*/ccm/collect", "/ccm/collect?en=1", True), ("*/ccm/collect?*", "/ccm/collect?en=1", True),
            ("*/ccm/collect?*", "/ccm/collect?", True), ("*/ccm/collect?*", "/ccm/collections", False),
            ("*/ccm/collect?*", "/ccm/collectX", False), ("*/xtr?*", "/xtr?id=1", True),
            ("*/xtr?*", "/xtrending", False), ("*/xtr?*", "/xtrX", False), ("*/xtr/*", "/xtr/?id=1", True),
            ("*/xtr/*", "/xtrending", False), ("*/a*b", "/a1b", True), ("*/a*b", "/a1b2", True), ("*/a*b", "/ab", True),
        )
        self.assertEqual(len(probe), 17)
        for pattern, path, blocked in probe:
            self.assertIs(chrome_pattern_blocks(pattern, "http://127.0.0.1:1" + path), blocked, (pattern, path))

    def test_every_glob_blocks_its_own_regex_case(self):
        cases = {
            r"/gtm\.js": "https://example.com/gtm.js?id=GTM-X",
            r"/gtag/js": "https://example.com/gtag/js?id=G-X",
            r"/g/collect": "https://sgtm.example.com/g/collect?v=2",
            r"/j/collect": "https://example.com/j/collect?t=dc",
            r"/collect\?v=": "https://example.com/collect?v=1",
            r"matomo\.php": "https://example.com/matomo.php",
            r"matomo\.js": "https://example.com/matomo.js",
            r"piwik\.php": "https://example.com/piwik.php",
            r"piwik\.js": "https://example.com/piwik.js",
            r"(^|\.)facebook\.com/tr/": "https://www.facebook.com/tr/?id=1&ev=PageView",
            r"(^|\.)facebook\.com/tr\?": "https://www.facebook.com/tr?id=1&ev=PageView",
            r"/tr\?id=": "https://example.com/tr?id=5",
            r"/tr/\?id=": "https://example.com/tr/?id=5",
            r"/ccm/collect\?.": "https://www.google.com/ccm/collect?en=page_view",
            r"/ccm/collect\?$": "https://tags.example.com/ccm/collect",
        }
        patterns = cro_runtime.BLOCKED_PATH_PATTERNS
        self.assertEqual(set(cases), set(patterns))
        self.assertEqual(len(cro_runtime._PATH_GLOBS), len(patterns))
        for regex, glob in zip(patterns, cro_runtime._PATH_GLOBS):
            url = cases[regex]
            parts = urlsplit(url)
            self.assertTrue(re.search(regex, (parts.hostname or "") + parts.path + "?" + parts.query), url)
            self.assertTrue(chrome_pattern_blocks(glob, url), "%s does not match %s" % (glob, url))

    def test_google_consent_collect_is_blocked(self):
        self.assertIsNotNone(cro_runtime.is_blocked("https://www.google.com/ccm/collect?en=page_view"))

    def test_added_tag_hosts_are_blocked_one_family_each(self):
        for url in ("https://stats.wp.com/e-202544.js", "https://pixel.wp.com/g.gif?v=ext",
                    "https://js.hs-scripts.com/123.js", "https://js.hs-analytics.net/analytics/1/123.js",
                    "https://track.hubspot.com/__ptq.gif", "https://static.ads-twitter.com/uwt.js",
                    "https://analytics.twitter.com/i/adsct", "https://ct.pinterest.com/v3/?tid=1",
                    "https://example.matomo.cloud/matomo.js", "https://i.posthog.com/e/", "https://app.posthog.com/static/array.js"):
            rule = cro_runtime.is_blocked(url)
            self.assertIsNotNone(rule, url)
            self.assertTrue(rule.startswith("host:"), "%s %s" % (url, rule))

    def test_whole_product_domains_stay_open(self):
        for url in ("https://posthog.com/docs", "https://www.hubspot.com/", "https://www.pinterest.com/", "https://twitter.com/x"):
            self.assertIsNone(cro_runtime.is_blocked(url), url)

    def test_ordinary_query_id_stays_unblocked(self):
        self.assertIsNone(cro_runtime.is_blocked("https://example.com/products/shoes?id=7"))

    def test_lighthouse_patterns_cover_every_rule(self):
        patterns = cro_runtime.lighthouse_block_patterns()
        self.assertEqual(len(patterns), len(cro_runtime.BLOCKED_HOSTS) + len(cro_runtime.BLOCKED_PATH_PATTERNS))
        self.assertIn("*googletagmanager.com*", patterns)
        self.assertIn("*/gtag/js*", patterns)


class UserAgentTest(unittest.TestCase):
    def test_chrome_ua_desktop_and_mobile(self):
        desktop = cro_runtime.chrome_ua(156)
        mobile = cro_runtime.chrome_ua(156, mobile=True)
        self.assertEqual(desktop, "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36")
        self.assertEqual(mobile, "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Mobile Safari/537.36")
        self.assertNotIn("HeadlessChrome", desktop + mobile)


class PagespeedKeyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.key_file = Path(self.tmp.name) / "pagespeed.key"
        patcher = mock.patch.object(cro_runtime, "KEY_FILE", self.key_file)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _env(self, **values):
        env = {k: v for k, v in os.environ.items() if k != cro_runtime.KEY_ENV}
        env.update(values)
        return mock.patch.dict(os.environ, env, clear=True)

    def test_pagespeed_key_prefers_env(self):
        self.key_file.write_text("FILE-KEY")
        os.chmod(self.key_file, 0o600)
        with self._env(**{cro_runtime.KEY_ENV: "ENV-KEY"}):
            self.assertEqual(cro_runtime.pagespeed_key(), ("ENV-KEY", "env"))

    def test_pagespeed_key_reads_file(self):
        self.key_file.write_text("FILE-KEY\n")
        os.chmod(self.key_file, 0o600)
        with self._env():
            self.assertEqual(cro_runtime.pagespeed_key(), ("FILE-KEY", "file"))

    def test_pagespeed_key_flags_loose_permissions(self):
        self.key_file.write_text("FILE-KEY")
        os.chmod(self.key_file, 0o644)
        with self._env():
            self.assertEqual(cro_runtime.pagespeed_key(), ("FILE-KEY", "file-loose-permissions"))

    def test_pagespeed_key_missing(self):
        with self._env():
            self.assertEqual(cro_runtime.pagespeed_key(), (None, "missing"))


class ClarityTokenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.default = Path(self.tmp.name) / "clarity.token"
        self.second = Path(self.tmp.name) / "second.token"
        patcher = mock.patch.object(cro_runtime, "CLARITY_FILE", self.default)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _env(self, **values):
        env = {k: v for k, v in os.environ.items() if k != cro_runtime.CLARITY_ENV}
        env.update(values)
        return mock.patch.dict(os.environ, env, clear=True)

    def test_names(self):
        self.assertEqual(cro_runtime.CLARITY_ENV, "NCA_CLARITY_TOKEN")

    def test_env_wins_over_the_default_file(self):
        self.default.write_text("FILE-TOKEN")
        os.chmod(self.default, 0o600)
        with self._env(**{cro_runtime.CLARITY_ENV: " ENV-TOKEN \n"}):
            self.assertEqual(cro_runtime.clarity_token(), ("ENV-TOKEN", "env"))

    def test_default_file_and_loose_permissions(self):
        self.default.write_text("FILE-TOKEN\n")
        with self._env():
            os.chmod(self.default, 0o600)
            self.assertEqual(cro_runtime.clarity_token(), ("FILE-TOKEN", "file"))
            os.chmod(self.default, 0o644)
            self.assertEqual(cro_runtime.clarity_token(), ("FILE-TOKEN", "file-loose-permissions"))

    def test_missing_and_empty_are_missing(self):
        with self._env():
            self.assertEqual(cro_runtime.clarity_token(), (None, "missing"))
            self.default.write_text("  \n")
            self.assertEqual(cro_runtime.clarity_token(), (None, "missing"))

    def test_token_file_is_read_first_whatever_its_mode(self):
        self.second.write_text("SECOND\n")
        os.chmod(self.second, 0o644)
        self.default.write_text("FILE-TOKEN")
        with self._env(**{cro_runtime.CLARITY_ENV: "ENV-TOKEN"}):
            self.assertEqual(cro_runtime.clarity_token(self.second), ("SECOND", "token-file"))

    def test_a_bad_token_file_does_not_fall_back(self):
        self.default.write_text("FILE-TOKEN")
        with self._env(**{cro_runtime.CLARITY_ENV: "ENV-TOKEN"}):
            self.assertEqual(cro_runtime.clarity_token(self.second), (None, "missing"))
            self.second.write_text("\n")
            self.assertEqual(cro_runtime.clarity_token(self.second), (None, "missing"))


class BlankValuesAndHostlessUrlsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.key_file = Path(self.tmp.name) / "pagespeed.key"
        patcher = mock.patch.object(cro_runtime, "KEY_FILE", self.key_file)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _env(self, **values):
        env = {k: v for k, v in os.environ.items() if k != cro_runtime.KEY_ENV}
        env.update(values)
        return mock.patch.dict(os.environ, env, clear=True)

    def test_env_value_is_stripped(self):
        with self._env(**{cro_runtime.KEY_ENV: "  ENV-KEY \n"}):
            self.assertEqual(cro_runtime.pagespeed_key(), ("ENV-KEY", "env"))

    def test_blank_env_falls_through_to_file(self):
        self.key_file.write_text("FILE-KEY")
        os.chmod(self.key_file, 0o600)
        with self._env(**{cro_runtime.KEY_ENV: "   "}):
            self.assertEqual(cro_runtime.pagespeed_key(), ("FILE-KEY", "file"))

    def test_blank_env_and_no_file_is_missing(self):
        with self._env(**{cro_runtime.KEY_ENV: ""}):
            self.assertEqual(cro_runtime.pagespeed_key(), (None, "missing"))

    def test_blank_file_is_missing_whatever_its_mode(self):
        for mode in (0o600, 0o644):
            self.key_file.write_text(" \n")
            os.chmod(self.key_file, mode)
            with self._env():
                self.assertEqual(cro_runtime.pagespeed_key(), (None, "missing"), oct(mode))

    def test_is_blocked_does_not_raise_without_a_host(self):
        self.assertIsNone(cro_runtime.is_blocked("data:text/plain,hello"))
        self.assertIsNone(cro_runtime.is_blocked("about:blank"))
        self.assertIsNotNone(cro_runtime.is_blocked("data:text/javascript,/gtag/js"))


BYPASS_CALLS = ("launch", "launch_persistent_context", "connect", "connect_over_cdp", "new_context", "new_page",
                "new_cdp_session", "route_web_socket", "add_init_script")
GUARDED = ("guarded_launch", "guarded_context", "guarded_page")


def guard_bypasses(source: str, name: str) -> list[str]:
    """One string per way the script's calls skip the guard. Reads the syntax tree, so spacing and comments do not count."""
    problems = []
    called = set()
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        attr, receiver = node.func.attr, ast.unparse(node.func.value)
        if receiver == "cro_runtime" and attr in GUARDED:
            called.add(attr)
        elif attr in BYPASS_CALLS:
            problems.append("%s: %s.%s() builds its own browser, context or page layer" % (name, receiver, attr))
        elif attr == "route" and not (name == "form_check.py" and receiver in ("page", "page.context")):
            problems.append("%s: %s.route() adds a route outside the guard" % (name, receiver))
    for missing in GUARDED:
        if missing not in called:
            problems.append("%s: no call to cro_runtime.%s" % (name, missing))
    return problems


class FakeRoute:
    """A Playwright route that records whether it was continued or aborted."""

    def __init__(self, method, url, resource_type="fetch"):
        self.request = type("Request", (), {"url": url, "method": method, "resource_type": resource_type})()
        self.action = None

    def continue_(self):
        self.action = "continue"

    def abort(self):
        self.action = "abort"


class GuardStackTest(unittest.TestCase):
    def test_cro_runtime_imports_without_playwright(self):
        code = "import sys; sys.modules['playwright'] = None; sys.path.insert(0, %r); import cro_runtime" % str(HERE)
        self.assertEqual(subprocess.run([sys.executable, "-I", "-c", code]).returncode, 0)

    def test_recorder_allows_one_consented_post_to_its_host_only(self):
        rec = cro_runtime.Recorder(allow_post_host="forms.example.test")
        first, second, other = (FakeRoute("POST", "https://forms.example.test/f"), FakeRoute("POST", "https://forms.example.test/f"),
                                FakeRoute("POST", "https://other.example.test/f"))
        for r in (first, second, other):
            rec.on_route(r)
        self.assertEqual((first.action, second.action, other.action), ("continue", "abort", "abort"))
        self.assertEqual([e["outcome"] for e in rec.entries if e["method"] == "POST"], ["consented", "blocked", "blocked"])

    def test_no_rendered_script_builds_its_own_browser_or_context(self):
        for name in ("render_check.py", "launch_render.py", "form_check.py", "form_consent.py"):
            path = HERE / name
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            allowed = text.replace("page.context.route(", "") if name == "form_check.py" else text  # its action-address route, see guard_bypasses
            for banned in ("chromium.launch", "new_context(", "route_web_socket(", "new_cdp_session(", "context.route("):
                self.assertNotIn(banned, allowed, name)
            self.assertIn("cro_runtime.guarded_launch", text, name)
            self.assertIn("cro_runtime.guarded_context", text, name)
            self.assertEqual(guard_bypasses(text, name), [], name)

    def test_bypass_check_catches_every_way_around_the_guard(self):
        clean_calls = ("browser = cro_runtime.guarded_launch(p)\n"
                       "context = cro_runtime.guarded_context(browser, rec, major=1, width=1, height=1)\n"
                       "page = cro_runtime.guarded_page(context, rec)\n")
        planted = {
            "browser.new_page()": "browser.new_page()",
            "p.firefox.launch()": "p.firefox.launch()",
            "launch_persistent_context": "p.chromium.launch_persistent_context(d)",
            "connect_over_cdp": "p.chromium.connect_over_cdp(u)",
            "spaced new_context": "browser.new_context ()",
            "add_init_script": "ctx.add_init_script(s)",
            "context.route": 'context.route("**/*", h)',
            "page.route outside form_check": 'page.route("**/*", h)',
        }
        for label, line in planted.items():
            self.assertTrue(guard_bypasses(clean_calls + line + "\n", "render_check.py"), label)
        comment_only = "# cro_runtime.guarded_page(context, rec)\ncro_runtime.guarded_launch(p)\ncro_runtime.guarded_context(b, r)\n"
        self.assertTrue(guard_bypasses(comment_only, "render_check.py"), "guarded_page only in a comment")
        docstring_only = '"""cro_runtime.guarded_page(context, rec)"""\n' + comment_only
        self.assertTrue(guard_bypasses(docstring_only, "render_check.py"), "guarded_page only in a docstring")
        clean = clean_calls + "page.route(action, h)\nbrowser.close()\n"
        self.assertEqual(guard_bypasses(clean, "form_check.py"), [])
        self.assertEqual(guard_bypasses(clean_calls + "browser.close()\n", "render_check.py"), [])
        self.assertTrue(guard_bypasses(clean, "render_check.py"))

    def test_host_rules_wraps_the_rule_list(self):
        self.assertEqual(cro_runtime.host_rules(), "--host-resolver-rules=" + cro_runtime.host_rule_list())
