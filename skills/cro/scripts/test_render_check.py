import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
SCRIPT = HERE / "render_check.py"


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


class _Recorder(BaseHTTPRequestHandler):
    requests = []

    def _handle(self):
        type(self).requests.append((self.command, self.path, self.headers.get("User-Agent", "")))
        name = "tagged.html" if self.path.split("?")[0] in ("/", "/tagged.html") else None
        if name and self.command == "GET":
            body = (FIXTURES / name).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
        else:
            body = b"ok"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    do_GET = do_POST = do_HEAD = do_OPTIONS = _handle

    def log_message(self, *args):
        pass


@SKIP
class RenderCheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _Recorder)
        cls.base = "http://127.0.0.1:%d/" % cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        _Recorder.requests.clear()
        cls.proc = subprocess.run([sys.executable, str(SCRIPT), cls.base, "--out", str(cls.out)],
                                  capture_output=True, text=True, timeout=180)
        cls.render = json.loads((cls.out / "render.json").read_text())
        cls.log = json.loads((cls.out / "network-log.json").read_text())
        cls.seen = list(_Recorder.requests)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def blocked_urls(self):
        return [e["url"] for e in self.log if e["outcome"] == "blocked"]

    def test_third_party_tags_are_blocked(self):
        for host in ("googletagmanager.com/gtag/js", "googletagmanager.com/gtm.js", "clarity.ms",
                     "connect.facebook.net", "snap.licdn.com"):
            self.assertTrue(any(host in u for u in self.blocked_urls()), host)

    def test_first_party_tag_paths_are_blocked(self):
        paths = [p for _m, p, _ua in self.seen]
        self.assertFalse(any(p.startswith("/gtag/js") for p in paths), paths)
        self.assertFalse(any(p.startswith("/g/collect") for p in paths), paths)
        urls = self.blocked_urls()
        self.assertTrue(any("/gtag/js" in u for u in urls if u.startswith(self.base)))
        self.assertTrue(any("/g/collect" in u for u in urls if u.startswith(self.base)))

    def test_no_non_get_request_reaches_the_server(self):
        self.assertEqual([m for m, _p, _ua in self.seen if m not in ("GET", "HEAD", "OPTIONS")], [])
        by_path = {e["url"].replace(self.base, "/"): e for e in self.log}
        for path in ("/api/hit", "/beacon"):
            self.assertEqual(by_path[path]["outcome"], "blocked", path)
            self.assertEqual(by_path[path]["rule"], "method:POST", path)

    def test_user_agent_is_ordinary_chrome(self):
        page_agents = [ua for m, p, ua in self.seen if m == "GET" and p == "/"]
        self.assertGreaterEqual(len(page_agents), 2)  # one per viewport pass
        for ua in page_agents:
            self.assertIn("Chrome/", ua)
            self.assertNotIn("HeadlessChrome", ua)
        self.assertTrue(any("Mobile" in ua for ua in page_agents))
        self.assertTrue(any("Mobile" not in ua for ua in page_agents))

    def test_render_json_shape_and_screenshots(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr)
        for key in ("url", "final_url", "checked_at", "user_agent", "status", "viewports", "blocked", "errors", "could_not_check"):
            self.assertIn(key, self.render)
        self.assertEqual(sorted(self.render["viewports"]), ["desktop", "phone"])
        for name in ("desktop-first-screen.png", "desktop-full.png", "phone-first-screen.png", "phone-full.png"):
            png = self.out / name
            self.assertTrue(png.exists(), name)
            self.assertEqual(png.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(self.render["viewports"]["desktop"]["width"], 1440)
        self.assertEqual(self.render["viewports"]["phone"]["width"], 390)
        self.assertGreaterEqual(self.render["viewports"]["desktop"]["page_height"], 2700)

    def test_forms_are_read_not_sent(self):
        form = self.render["viewports"]["desktop"]["forms"][0]
        self.assertEqual(form["fields"], 4)
        self.assertEqual(form["required"], 2)
        self.assertNotIn("/thank-you", [p for _m, p, _ua in self.seen])

    def test_cta_in_first_screen(self):
        ctas = self.render["viewports"]["desktop"]["ctas"]
        match = [c for c in ctas if c["text"] == "Book a call"]
        self.assertTrue(match, ctas)
        self.assertTrue(match[0]["in_first_screen"])


@SKIP
class UnreachableTest(unittest.TestCase):
    def test_unreachable_url_exits_3_with_could_not_check(self):
        import socket
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        with tempfile.TemporaryDirectory() as tmp:
            done = subprocess.run([sys.executable, str(SCRIPT), "http://127.0.0.1:%d/" % port, "--out", tmp, "--timeout", "10"],
                                  capture_output=True, text=True, timeout=120)
            self.assertEqual(done.returncode, 3, done.stderr)
            data = json.loads((Path(tmp) / "render.json").read_text())
            self.assertTrue(data["could_not_check"])


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
        done = subprocess.run([sys.executable, str(SCRIPT), cls.base + path, "--out", str(out)],
                              capture_output=True, text=True, timeout=120)
        return done, out

    @classmethod
    def facts(cls, path, name):
        done, out = cls.render(path, name)
        return done, json.loads((out / "render.json").read_text())


@SKIP
class LeakPathsTest(_LocalPages):
    @classmethod
    def setUpClass(cls):
        cls.start()
        _LeakRecorder.requests.clear()
        cls.logs = []
        cls.renders = []
        for path, name in (("/", "still"), ("/?moves", "moves")):
            done, out = cls.render(path, name)
            cls.renders.append(json.loads((out / "render.json").read_text()))
            cls.logs += json.loads((out / "network-log.json").read_text())
        time.sleep(1.5)  # a send that outlives the run would land here
        cls.seen = list(_LeakRecorder.requests)

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

    def test_page_errors_are_kept_and_the_runs_own_aborts_are_not(self):
        errors = self.renders[0]["errors"]
        self.assertTrue(any("page says boom" in e for e in errors), errors)
        self.assertFalse([e for e in errors if "net::ERR_" in e], errors)


@SKIP
class RenderFactsTest(_LocalPages):
    @classmethod
    def setUpClass(cls):
        cls.start()

    def test_phone_overflow_reads_as_horizontal_scroll(self):
        _done, render = self.facts("/wide", "wide")
        self.assertTrue(render["viewports"]["phone"]["horizontal_scroll"])
        self.assertFalse(render["viewports"]["desktop"]["horizontal_scroll"])

    def test_overflow_the_page_clips_is_not_horizontal_scroll(self):
        _done, render = self.facts("/clipped", "clipped")
        self.assertFalse(render["viewports"]["phone"]["horizontal_scroll"])

    def test_http_error_page_exits_3_with_the_status(self):
        done, render = self.facts("/missing", "missing")
        self.assertEqual(done.returncode, 3, done.stderr)
        self.assertEqual(render["status"], 404)
        self.assertEqual(len(render["could_not_check"]), 1)
        self.assertIn("404", render["could_not_check"][0])

    def test_page_that_keeps_growing_still_finishes(self):
        done, _render = self.facts("/growing", "growing")
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_only_visible_things_are_read(self):
        _done, render = self.facts("/facts", "facts")
        for name, height in (("desktop", 900), ("phone", 844)):
            view = render["viewports"][name]
            self.assertEqual([c["text"] for c in view["ctas"]], ["Filled link", "Low button"], name)
            self.assertTrue(view["ctas"][0]["in_first_screen"], name)
            self.assertFalse(view["ctas"][1]["in_first_screen"], name)
            self.assertGreater(view["ctas"][1]["top"], height, name)
            self.assertIn("Headline words", view["first_screen_text"], name)
            self.assertNotIn("Below the fold words", view["first_screen_text"], name)

    def test_every_blocked_host_is_stopped_at_the_browser(self):
        import cro_runtime
        import render_check
        rules = render_check.host_rules()
        self.assertTrue(rules.startswith("--host-resolver-rules="), rules[:40])
        for host in cro_runtime.BLOCKED_HOSTS:
            self.assertIn("MAP %s ~NOTFOUND" % host, rules)
            self.assertIn("MAP *.%s ~NOTFOUND" % host, rules)


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


@SKIP
class OtherTargetsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _TargetRecorder)
        cls.server.daemon_threads = True
        base = "http://127.0.0.1:%d/" % cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.tmp = tempfile.TemporaryDirectory()
        _TargetRecorder.requests.clear()
        out = Path(cls.tmp.name) / "targets"
        cls.proc = subprocess.run([sys.executable, str(SCRIPT), base, "--out", str(out)],
                                  capture_output=True, text=True, timeout=120)
        time.sleep(1.5)  # a request that outlives the run lands here
        cls.paths = [p for _m, p in _TargetRecorder.requests]
        cls.render = json.loads((out / "render.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_no_redirect_hop_reaches_a_tag_path_from_a_frame_popup_new_page_or_worker(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr)
        self.assertIn("/hop?via=main", self.paths)
        self.assertFalse([p for p in self.paths if p.startswith("/g/collect")], self.paths)

    def test_a_cross_site_frame_still_renders(self):
        self.assertIn("/frame", self.paths)
        self.assertIn("/hop?via=frame", self.paths)

    def test_popups_are_blocked_as_in_a_visitors_chrome(self):
        self.assertIn("/note?opened=null", self.paths)
        for path in ("/popup", "/link-page", "/form-page"):
            self.assertNotIn(path, [p.split("?")[0] for p in self.paths], path)

    def test_no_worker_runs_and_none_is_reported_as_an_error(self):
        self.assertNotIn("/worker.js", self.paths)
        self.assertFalse([e for e in self.render["errors"] if "Worker" in e], self.render["errors"])


@SKIP
class LaunchTest(unittest.TestCase):
    def test_both_launches_carry_the_host_rules_one_process_and_the_popup_blocker(self):
        from types import SimpleNamespace

        from playwright.sync_api import Error as PlaywrightError

        import render_check

        calls = []

        def launch(**options):
            calls.append(options)
            if options.get("channel") == "chrome":
                raise PlaywrightError("no Chrome here")
            return "bundled browser"

        browser = render_check.launch(SimpleNamespace(chromium=SimpleNamespace(launch=launch)))
        self.assertEqual(browser, "bundled browser")
        self.assertEqual([options.get("channel") for options in calls], ["chrome", None])
        for options in calls:
            self.assertIn(render_check.host_rules(), options["args"])
            self.assertIn("--disable-site-isolation-trials", options["args"])
            self.assertIn("--disable-popup-blocking", options["ignore_default_args"])


if __name__ == "__main__":
    unittest.main()
