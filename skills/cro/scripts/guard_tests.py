"""Shared test pieces for every rendered route: the local pages and request recorders, and the leak-path cases.

A script that renders a page subclasses GuardLeakPathsMixin together with unittest.TestCase and gives it
run_route(url, out), the network log of one run of that script. Every case below then runs against it.
"""
import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def _browser_ok():
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.launch(channel="chrome", headless=True).close()
        return True
    except Exception:
        return False


BROWSER_OK = _browser_ok()
SKIP = unittest.skipUnless(BROWSER_OK, "Playwright or Chrome missing: run setup.py")


LEAKY_PAGE = """<!doctype html><title>leaky</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script>
function send(tag) {
  navigator.sendBeacon('/sent/beacon-' + tag, 'x=1');
  fetch('/sent/keepalive-' + tag, {method: 'POST', body: 'x=1', keepalive: true}).catch(() => {});
  fetch('/sent/plain-' + tag, {method: 'POST', body: 'x=1'}).catch(() => {});
  new Image().src = '/g/collect?v=2&via=' + tag;
}
for (const type of ['beforeunload', 'pagehide', 'unload', 'visibilitychange']) {
  window.addEventListener(type, () => send(type));
}
window.onpagehide = () => send('attribute');
if (location.search === '?moves') setTimeout(() => location.replace('/after'), 300);
try { new SharedWorker('/shared.js'); } catch (e) {}
try { new WebSocket(location.origin.replace('http', 'ws') + '/socket'); } catch (e) {}
fetch('/sent/onload', {method: 'POST', body: 'x=1'}).catch(() => {});
fetch('/slow').catch(() => {});
console.error('page says boom');
</script>
<h1>Leaky page</h1>
<img src="/hop" width="1" height="1" alt="">
<script src="/gtag/js?id=G-TEST0000000"></script>
"""
WIDE_PAGE = """<!doctype html><meta name="viewport" content="width=device-width, initial-scale=1">
<body style="margin:0"><div style="width:800px;height:50px">wide</div></body>"""
CLIPPED_PAGE = """<!doctype html><meta name="viewport" content="width=device-width, initial-scale=1">
<html style="overflow-x:hidden"><body style="margin:0;overflow-x:hidden"><div style="width:800px;height:50px">wide</div></body></html>"""
GROWING_PAGE = """<!doctype html><meta name="viewport" content="width=device-width, initial-scale=1">
<script>addEventListener('scroll', () => {
  const block = document.createElement('div');
  block.style.height = '900px';
  document.body.append(block);
});</script><h1>Keeps growing</h1><div style="height:900px"></div>"""
FACTS_PAGE = """<!doctype html><meta name="viewport" content="width=device-width, initial-scale=1">
<h1>Headline words</h1><p>Paragraph words</p>
<a href="#a" style="background:#0a5">Filled link</a>
<a href="#b">Plain link</a>
<a href="#c" style="background:#000;position:absolute;left:-9999px">Off screen link</a>
<a href="#d" style="background:#000;position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)">Clipped link</a>
<button style="opacity:0">Faded button</button>
<div style="height:2000px"></div>
<p>Below the fold words</p><button>Low button</button>"""


class _LeakRecorder(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    requests = []
    pages = {"/": LEAKY_PAGE, "/after": "<h1>after</h1>", "/wide": WIDE_PAGE, "/clipped": CLIPPED_PAGE,
             "/growing": GROWING_PAGE, "/facts": FACTS_PAGE}

    def _reply(self, status, body, content_type, location=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if location:
            self.send_header("Location", location)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _handle(self):
        type(self).requests.append((self.command, self.path, self.headers.get("Upgrade", ""),
                                    self.headers.get("User-Agent", "")))
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        path = self.path.split("?")[0]
        if path in self.pages:
            self._reply(200, self.pages[path].encode(), "text/html; charset=utf-8")
        elif path == "/hop":
            self._reply(302, b"", "text/plain", location="/g/collect?v=2&via=hop")
        elif path == "/missing":
            self._reply(404, b"<h1>Not found</h1>", "text/html; charset=utf-8")
        elif path == "/shared.js":
            self._reply(200, b"fetch('/sent/shared', {method: 'POST', body: 'x=1'});", "text/javascript")
        elif path == "/slow":
            time.sleep(20)
            self._reply(200, b"late", "text/plain")
        else:
            self._reply(200, b"ok", "text/plain")

    do_GET = do_POST = do_HEAD = do_OPTIONS = _handle

    def handle(self):
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *args):
        pass



class _LocalPages(unittest.TestCase):
    script = None  # the subclass names the script whose run it records

    @classmethod
    def start(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _LeakRecorder)
        cls.server.daemon_threads = True
        cls.base = "http://127.0.0.1:%d" % cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.addClassCleanup(cls.server.server_close)
        cls.addClassCleanup(cls.server.shutdown)

    @classmethod
    def render(cls, path, name):
        out = Path(cls.tmp.name) / name / "nested"  # R15: render_check makes it, parents included
        done = subprocess.run([sys.executable, str(cls.script), cls.base + path, "--out", str(out)],
                              capture_output=True, text=True, timeout=120)
        return done, out

    @classmethod
    def facts(cls, path, name):
        done, out = cls.render(path, name)
        return done, json.loads((out / "render.json").read_text())



TARGETS_PAGE = """<!doctype html><title>targets</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<h1>Targets page</h1>
<img src="/hop?via=main" width="1" height="1" alt="">
<iframe src="http://localhost:%(port)d/frame" width="300" height="80"></iframe>
<script>
const opened = window.open('/popup');
new Image().src = '/note?opened=' + (opened ? 'window' : 'null');
new Worker('/worker.js');
const link = document.createElement('a');
link.href = '/link-page';
link.target = '_blank';
link.rel = 'opener';
document.body.append(link);
link.click();
</script>
<form action="/form-page" method="get" target="_blank"><input name="q" value="1"></form>
<script>document.forms[0].submit();</script>
"""


class _TargetRecorder(_LeakRecorder):
    requests = []
    targets = {"/popup": '<img src="/hop?via=popup" width="1" height="1" alt="">',
               "/frame": '<p>Frame words</p><img src="/hop?via=frame" width="1" height="1" alt="">'}
    new_pages = {"/link-page": "link", "/form-page": "form"}

    def _handle(self):
        type(self).requests.append((self.command, self.path))
        path, _, query = self.path.partition("?")
        if path == "/":
            page = TARGETS_PAGE % {"port": self.server.server_address[1]}
            self._reply(200, page.encode(), "text/html; charset=utf-8")
        elif path in self.targets:
            self._reply(200, self.targets[path].encode(), "text/html; charset=utf-8")
        elif path == "/worker.js":
            self._reply(200, b"fetch('/hop?via=worker');", "text/javascript")
        elif path == "/hop":
            self._reply(302, b"", "text/plain", location="/g/collect?v=2&" + query)
        elif path in self.new_pages:
            self._reply(302, b"", "text/plain", location="/g/collect?v=2&via=" + self.new_pages[path])
        else:
            self._reply(200, b"ok", "text/plain")

    do_GET = do_POST = do_HEAD = do_OPTIONS = _handle


class GuardLeakPathsMixin:
    """The leak-path cases, run against whatever script the subclass's run_route runs.

    Subclass with unittest.TestCase (and @SKIP) and define
    run_route(cls, url: str, out: Path) -> list[dict], a classmethod returning the network log of one run.
    It also stores the page errors that run reported in cls.errors_by_run[out.parent.name], a list of strings.
    """

    errors_by_run = None

    @classmethod
    def run_route(cls, url, out):
        raise NotImplementedError("the subclass runs its own script here")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.errors_by_run = {}
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _LeakRecorder)
        cls.server.daemon_threads = True
        base = "http://127.0.0.1:%d" % cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.addClassCleanup(cls.server.server_close)
        cls.addClassCleanup(cls.server.shutdown)
        _LeakRecorder.requests.clear()
        cls.logs = []
        for path, name in (("/", "still"), ("/?moves", "moves")):
            cls.logs += cls.run_route(base + path, Path(cls.tmp.name) / name / "nested")
        time.sleep(1.5)  # a send that outlives the run would land here
        cls.seen = list(_LeakRecorder.requests)

        cls.target_server = ThreadingHTTPServer(("127.0.0.1", 0), _TargetRecorder)
        cls.target_server.daemon_threads = True
        threading.Thread(target=cls.target_server.serve_forever, daemon=True).start()
        cls.addClassCleanup(cls.target_server.server_close)
        cls.addClassCleanup(cls.target_server.shutdown)
        _TargetRecorder.requests.clear()
        cls.run_route("http://127.0.0.1:%d/" % cls.target_server.server_address[1], Path(cls.tmp.name) / "targets" / "nested")
        time.sleep(1.5)  # a request that outlives the run lands here
        cls.target_paths = [p for _m, p in _TargetRecorder.requests]

    def paths(self):
        return [p for _m, p, _u, _a in self.seen]

    def test_nothing_sent_during_teardown_reaches_the_server(self):
        self.assertEqual([p for m, p, _u, _a in self.seen if m not in ("GET", "HEAD", "OPTIONS")], [])
        self.assertFalse(any(p.startswith("/sent/") for p in self.paths()), self.paths())

    def test_redirect_hop_to_a_tag_path_stops(self):
        self.assertIn("/hop", self.paths())
        self.assertFalse(any(p.startswith("/g/collect") for p in self.paths()), self.paths())
        hops = [e for e in self.logs if "/g/collect?v=2&via=hop" in e["url"]]
        self.assertTrue(hops)
        self.assertEqual({e["outcome"] for e in hops}, {"blocked"})

    def test_shared_worker_never_starts(self):
        self.assertNotIn("/shared.js", self.paths())

    def test_websocket_never_reaches_the_server_and_is_logged(self):
        self.assertEqual([p for _m, p, up, _a in self.seen if up.lower() == "websocket"], [])
        sockets = [e for e in self.logs if e["url"].endswith("/socket")]
        self.assertTrue(sockets)
        for entry in sockets:
            self.assertEqual((entry["outcome"], entry["rule"]), ("blocked", "websocket"))

    def test_no_request_carries_the_headless_agent(self):
        self.assertFalse([ua for _m, _p, _u, ua in self.seen if "Headless" in ua])

    def test_request_still_open_at_write_time_is_logged_as_failed(self):
        slow = [e for e in self.logs if e["url"].endswith("/slow")]
        self.assertTrue(slow)
        self.assertEqual({e["outcome"] for e in slow}, {"failed"})

    def test_no_redirect_hop_reaches_a_tag_path_from_a_frame_popup_new_page_or_worker(self):
        self.assertIn("/hop?via=main", self.target_paths)
        self.assertFalse([p for p in self.target_paths if p.startswith("/g/collect")], self.target_paths)

    def test_a_cross_site_frame_still_renders(self):
        self.assertIn("/frame", self.target_paths)
        self.assertIn("/hop?via=frame", self.target_paths)

    def test_popups_are_blocked_as_in_a_visitors_chrome(self):
        self.assertIn("/note?opened=null", self.target_paths)
        for path in ("/popup", "/link-page", "/form-page"):
            self.assertNotIn(path, [p.split("?")[0] for p in self.target_paths], path)

    def test_no_worker_runs_and_none_is_reported_as_an_error(self):
        self.assertNotIn("/worker.js", self.target_paths)
        errors = self.errors_by_run["targets"]
        self.assertFalse([e for e in errors if "Worker" in e], errors)

    def test_page_errors_are_kept_and_the_runs_own_aborts_are_not(self):
        errors = self.errors_by_run["still"]
        self.assertTrue(any("page says boom" in e for e in errors), errors)
        self.assertFalse([e for e in errors if "net::ERR_" in e], errors)

    def test_both_launches_carry_the_host_rules_one_process_and_the_popup_blocker(self):
        from types import SimpleNamespace

        from playwright.sync_api import Error as PlaywrightError

        import cro_runtime

        calls = []

        def launch(**options):
            calls.append(options)
            if options.get("channel") == "chrome":
                raise PlaywrightError("no Chrome here")
            return "bundled browser"

        browser = cro_runtime.guarded_launch(SimpleNamespace(chromium=SimpleNamespace(launch=launch)))
        self.assertEqual(browser, "bundled browser")
        self.assertEqual([options.get("channel") for options in calls], ["chrome", None])
        for options in calls:
            self.assertIn(cro_runtime.host_rules(), options["args"])
            self.assertIn("--disable-site-isolation-trials", options["args"])
            self.assertIn("--disable-popup-blocking", options["ignore_default_args"])
