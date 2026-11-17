"""Shared constants, helpers and the browser guard for the /cro scripts. Standard library only at import:
Playwright is imported inside guarded_launch, so the system-Python scripts can import this module."""
import os
import re
import stat
from pathlib import Path
from urllib.parse import unquote_plus, urlsplit

PLAYWRIGHT_VERSION = "1.62.0"
KEY_ENV = "NCA_PAGESPEED_KEY"
KEY_FILE = Path.home() / ".config" / "nca-conversion" / "pagespeed.key"
CLARITY_ENV = "NCA_CLARITY_TOKEN"
CLARITY_FILE = Path.home() / ".config" / "nca-conversion" / "clarity.token"
ALLOWED_METHODS = ("GET", "HEAD", "OPTIONS")
OWN_ABORTS = ("net::ERR_FAILED", "net::ERR_BLOCKED_BY_CLIENT")

# Registers first, in the capture phase, so teardown handlers never run; no worker runs.
INIT_SCRIPT = """
(() => {
  for (const type of ['beforeunload', 'pagehide', 'unload', 'visibilitychange', 'freeze', 'pageswap']) {
    window.addEventListener(type, (event) => event.stopImmediatePropagation(), true);
  }
  delete window.SharedWorker;
  window.Worker = class {
    postMessage() {}
    terminate() {}
    addEventListener() {}
    removeEventListener() {}
    dispatchEvent() { return false; }
  };
})();
"""

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
    "bat.bing.net",  # https://github.com/MicrosoftDocs/Advertising/blob/main/advertising/msa-help/hlp_BA_CONC_UETv2CSP.md
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


def host_rule_list() -> str:
    """The Chromium host-resolver rules alone, as speed_check.py quotes them inside its own flag."""
    mapped = []
    for suffix in BLOCKED_HOSTS:
        mapped.append("MAP %s ~NOTFOUND" % suffix)
        mapped.append("MAP *.%s ~NOTFOUND" % suffix)
    return ", ".join(mapped)


def host_rules() -> str:
    return "--host-resolver-rules=" + host_rule_list()


class Recorder:
    """Every request of the run, keyed by request object so nothing is logged twice.

    With allow_post_host, the first non-GET request to that host continues and is logged "consented";
    any later one to it is aborted with rule "consent:used". Every other non-GET request is aborted.
    With allow_post_marker, only a request whose body carries that text (percent-decoded) can take the send; any other non-GET
    request to that host is aborted with rule "consent:no-marker" and does not use the consent up.
    """

    def __init__(self, allow_post_host: str | None = None):
        self.entries = []
        self.by_request = {}
        self.errors = []
        self.allow_post_host = allow_post_host.lower() if allow_post_host else None
        self.allow_post_marker = None
        self.consent_used = False

    def carries_marker(self, request):
        if not self.allow_post_marker:
            return True
        try:
            raw = request.post_data_buffer or b""
        except Exception:
            raw = b""
        text = raw.decode("utf-8", "replace").lower()
        marker = self.allow_post_marker.lower()
        return marker in text or marker in unquote_plus(text)

    def entry(self, request):
        found = self.by_request.get(request)
        if found is None:
            found = {"url": request.url, "method": request.method, "resource_type": request.resource_type,
                     "outcome": None, "rule": None, "status": None}
            self.by_request[request] = found
            self.entries.append(found)
        return found

    def on_request(self, request):
        self.entry(request)

    def on_response(self, response):
        self.entry(response.request)["status"] = response.status

    def on_finished(self, request):
        found = self.entry(request)
        if found["outcome"] is None:
            found["outcome"] = "completed"

    def on_failed(self, request):
        found = self.entry(request)
        if found["outcome"] == "consented":
            found["failure"] = request.failure  # the request left and the browser got no answer; the outcome stays "consented"
        if found["outcome"] is not None:
            return
        rule = is_blocked(request.url)
        found["outcome"], found["rule"] = ("blocked", rule) if rule else ("failed", None)

    def on_route(self, route):
        request = route.request
        rule = is_blocked(request.url)
        if rule is None and request.method not in ALLOWED_METHODS:
            if self.allow_post_host and (urlsplit(request.url).hostname or "").lower() == self.allow_post_host:
                if self.consent_used:
                    rule = "consent:used"
                elif not self.carries_marker(request):
                    rule = "consent:no-marker"
                else:
                    self.consent_used = True
                    self.entry(request)["outcome"] = "consented"
                    route.continue_()
                    return
            else:
                rule = "method:" + request.method
        if rule is None:
            route.continue_()
            return
        found = self.entry(request)
        found["outcome"], found["rule"] = "blocked", rule
        route.abort()

    def on_socket(self, socket):
        self.entries.append({"url": socket.url, "method": "GET", "resource_type": "websocket",
                             "outcome": "blocked", "rule": "websocket", "status": None})

    def on_console(self, message):
        if message.type == "error" and not any(own in message.text for own in OWN_ABORTS):
            self.add_error(message.text)

    def add_error(self, text):
        if text not in self.errors:
            self.errors.append(text)

    def finish(self):
        for found in self.entries:
            if found["outcome"] is None:
                found["outcome"] = "failed"
        return self.entries


def guarded_launch(playwright):
    """Headless Chrome, else the bundled Chromium, with the DNS host rules on. Close it last, with browser.close()."""
    options = {
        "headless": True,
        "args": [host_rules(), "--disable-site-isolation-trials"],
        "ignore_default_args": ["--disable-popup-blocking"],
    }
    from playwright.sync_api import Error as PlaywrightError
    try:
        return playwright.chromium.launch(channel="chrome", **options)
    except PlaywrightError:
        return playwright.chromium.launch(**options)


def guarded_context(browser, recorder, *, major, width, height, mobile=False, reduced_motion=None):
    """One context with the teardown init script, the URL and WebSocket routes and the request events.
    Contexts are never closed: browser.close() ends them."""
    context = browser.new_context(
        viewport={"width": width, "height": height},
        user_agent=chrome_ua(major, mobile=mobile),
        is_mobile=mobile,
        has_touch=mobile,
        device_scale_factor=3 if mobile else 1,
        reduced_motion=reduced_motion,
        service_workers="block",
    )
    context.add_init_script(INIT_SCRIPT)
    context.route("**/*", recorder.on_route)
    context.route_web_socket(re.compile(".*"), recorder.on_socket)
    context.on("request", recorder.on_request)
    context.on("response", recorder.on_response)
    context.on("requestfinished", recorder.on_finished)
    context.on("requestfailed", recorder.on_failed)
    return context


def guarded_page(context, recorder):
    """A page with the console and page-error hooks and the CDP URL block, the layer Lighthouse's patterns share."""
    page = context.new_page()
    page.on("console", recorder.on_console)
    page.on("pageerror", lambda error: recorder.add_error(str(error)))
    session = context.new_cdp_session(page)
    session.send("Network.enable")
    session.send("Network.setBlockedURLs", {"urls": lighthouse_block_patterns()})
    return page


def pagespeed_key() -> tuple[str | None, str]:
    value = os.environ.get(KEY_ENV, "").strip()
    if value:
        return value, "env"
    try:
        content = KEY_FILE.read_text(encoding="utf-8").strip()
        mode = stat.S_IMODE(KEY_FILE.stat().st_mode)
    except (OSError, ValueError):  # ValueError: UnicodeDecodeError, a key file that is not text
        return None, "missing"
    if not content:
        return None, "missing"
    return content, "file-loose-permissions" if mode & 0o077 else "file"


def clarity_token(token_file: Path | None = None) -> tuple[str | None, str]:
    """The Clarity export token and where it came from. A named token file is the only place looked at."""
    if token_file is not None:
        try:
            content = Path(token_file).expanduser().read_text(encoding="utf-8").strip()
        except (OSError, ValueError):
            return None, "missing"
        return (content, "token-file") if content else (None, "missing")
    value = os.environ.get(CLARITY_ENV, "").strip()
    if value:
        return value, "env"
    try:
        content = CLARITY_FILE.read_text(encoding="utf-8").strip()
        mode = stat.S_IMODE(CLARITY_FILE.stat().st_mode)
    except (OSError, ValueError):
        return None, "missing"
    if not content:
        return None, "missing"
    return content, "file-loose-permissions" if mode & 0o077 else "file"
