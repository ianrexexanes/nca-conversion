"""Shared constants and helpers for the /cro scripts. Standard library only."""
import os
import re
import stat
from pathlib import Path
from urllib.parse import urlsplit

PLAYWRIGHT_VERSION = "1.62.0"
KEY_ENV = "NCA_PAGESPEED_KEY"
KEY_FILE = Path.home() / ".config" / "nca-conversion" / "pagespeed.key"

BLOCKED_HOSTS: tuple[str, ...] = (
    "google-analytics.com",  # https://developers.google.com/tag-platform/gtagjs
    "analytics.google.com",  # https://developers.google.com/tag-platform/gtagjs
    "googletagmanager.com",  # https://developers.google.com/tag-platform/gtagjs
    "doubleclick.net",  # https://developers.google.com/tag-platform/gtagjs
    "googleadservices.com",  # https://developers.google.com/tag-platform/gtagjs
    "googlesyndication.com",  # https://developers.google.com/tag-platform/gtagjs
    "clarity.ms",  # https://learn.microsoft.com/en-us/clarity/setup-and-installation/clarity-setup
    "connect.facebook.net",  # https://developers.facebook.com/documentation/meta-pixel/get-started
    "px.ads.linkedin.com",  # https://www.linkedin.com/help/lms/answer/a425696
    "snap.licdn.com",  # https://www.linkedin.com/help/lms/answer/a425696
    "analytics.tiktok.com",  # UNVERIFIED 2026-11-06: no vendor page found
    "bat.bing.com",  # https://github.com/MicrosoftDocs/Advertising/blob/main/advertising/msa-help/hlp_BA_CONC_UETv2CSP.md
    "hotjar.com",  # https://learning.hotjar.com/installing-the-hotjar-tracking-code
    "hotjar.io",  # UNVERIFIED 2026-11-06: no vendor page found
    "plausible.io",  # https://plausible.io/docs/events-api
    "cdn.segment.com",  # https://www.twilio.com/docs/segment/connections/sources/catalog/libraries/website/javascript/custom-proxy
    "api.segment.io",  # https://www.twilio.com/docs/segment/connections/sources/catalog/libraries/website/javascript/custom-proxy
    "mixpanel.com",  # https://docs.mixpanel.com/docs/tracking-methods/sdks/javascript
    "heapanalytics.com",  # https://developers.heap.io/docs/web
    "static.cloudflareinsights.com",  # https://developers.cloudflare.com/web-analytics/data-metrics/data-origin-and-collection/
    "stats.wp.com",  # https://github.com/Automattic/jetpack/blob/trunk/projects/packages/stats/README.md
    "pixel.wp.com",  # https://github.com/Automattic/jetpack/blob/trunk/projects/packages/stats/README.md
    "js.hs-scripts.com",  # https://knowledge.hubspot.com/reports/how-do-i-know-if-my-hubspot-tracking-code-is-working
    "js.hs-analytics.net",  # https://knowledge.hubspot.com/reports/how-do-i-know-if-my-hubspot-tracking-code-is-working
    "track.hubspot.com",  # https://knowledge.hubspot.com/account/how-does-hubspot-track-visitors
    "static.ads-twitter.com",  # https://business.x.com/en/help/campaign-measurement-and-analytics/conversion-tracking-for-websites
    "analytics.twitter.com",  # https://business.x.com/en/help/troubleshooting/faqs-about-pixels
    "ct.pinterest.com",  # https://help.pinterest.com/en-gb/business/article/install-the-base-code
    "matomo.cloud",  # https://matomo.org/faq/how-to-install/set-up-a-tracker-proxy-on-your-domain/
    "i.posthog.com",  # https://posthog.com/docs/api
    "app.posthog.com",  # UNVERIFIED 2026-11-06: no vendor page found
)

# Each regex is paired, by position, with its Lighthouse glob below.
BLOCKED_PATH_PATTERNS: tuple[str, ...] = (
    r"/gtm\.js",
    r"/gtag/js",
    r"/g/collect",
    r"/j/collect",
    r"/collect\?v=",
    r"matomo\.php",
    r"matomo\.js",
    r"piwik\.php",
    r"piwik\.js",
    r"(^|\.)facebook\.com/tr/",
    r"(^|\.)facebook\.com/tr\?",
    r"/tr\?id=",
    r"/tr/\?id=",
    r"/ccm/collect\?.",  # UNVERIFIED 2026-11-06: no vendor page found
    r"/ccm/collect\?$",  # UNVERIFIED 2026-11-06: no vendor page found
)
_PATH_GLOBS: tuple[str, ...] = (
    "*/gtm.js*",
    "*/gtag/js*",
    "*/g/collect*",
    "*/j/collect*",
    "*/collect?v=*",
    "*matomo.php*",
    "*matomo.js*",
    "*piwik.php*",
    "*piwik.js*",
    "*facebook.com/tr/*",
    "*facebook.com/tr?*",
    "*/tr?id=*",
    "*/tr/?id=*",
    "*/ccm/collect?*",
    "*/ccm/collect",
)


def default_data_dir() -> Path:
    return Path.home() / ".cache" / "nca-conversion"


def venv_python(data_dir: Path) -> Path:
    return Path(data_dir) / "venv" / "bin" / "python"


def chrome_ua(major: int, mobile: bool = False) -> str:
    if mobile:
        return (f"Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{major}.0.0.0 Mobile Safari/537.36")
    return (f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{major}.0.0.0 Safari/537.36")


def is_blocked(url: str) -> str | None:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if host:
        for suffix in BLOCKED_HOSTS:
            if host == suffix or host.endswith("." + suffix):
                return f"host:{suffix}"
    target = host + parts.path + "?" + parts.query
    for pattern in BLOCKED_PATH_PATTERNS:
        if re.search(pattern, target):
            return f"path:{pattern}"
    return None


def lighthouse_block_patterns() -> list[str]:
    return ["*" + suffix + "*" for suffix in BLOCKED_HOSTS] + list(_PATH_GLOBS)


def pagespeed_key() -> tuple[str | None, str]:
    value = os.environ.get(KEY_ENV, "").strip()
    if value:
        return value, "env"
    try:
        content = KEY_FILE.read_text(encoding="utf-8").strip()
        mode = stat.S_IMODE(KEY_FILE.stat().st_mode)
    except OSError:
        return None, "missing"
    if not content:
        return None, "missing"
    return content, "file-loose-permissions" if mode & 0o077 else "file"
