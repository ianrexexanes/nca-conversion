import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import cro_runtime


class IsBlockedTest(unittest.TestCase):
    def test_is_blocked_matches_third_party_hosts(self):
        self.assertEqual(cro_runtime.is_blocked("https://www.googletagmanager.com/gtag/js?id=G-X"), "host:googletagmanager.com")

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
        self.assertEqual(cro_runtime.is_blocked("https://www.facebook.com/tr/?ev=PageView"), "path:facebook\\.com/tr")

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
