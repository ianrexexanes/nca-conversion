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
    "google-analytics.com",
    "analytics.google.com",
    "googletagmanager.com",
    "doubleclick.net",
    "googleadservices.com",
    "googlesyndication.com",
    "clarity.ms",
    "connect.facebook.net",
    "px.ads.linkedin.com",
    "snap.licdn.com",
    "analytics.tiktok.com",
    "bat.bing.com",
    "hotjar.com",
    "hotjar.io",
    "plausible.io",
    "cdn.segment.com",
    "api.segment.io",
    "mixpanel.com",
    "heapanalytics.com",
    "static.cloudflareinsights.com",
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
    r"facebook\.com/tr",
    r"/tr\?id=",
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
    "*facebook.com/tr*",
    "*/tr?id=*",
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
    target = parts.path + "?" + parts.query
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
