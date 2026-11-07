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


from guard_tests import SKIP, GuardLeakPathsMixin, _LeakRecorder, _LocalPages  # noqa: E402


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

    def test_render_json_notes_say_workers_are_off(self):
        notes = self.render["notes"]
        self.assertEqual(len(notes), 1)
        self.assertIn("web workers are off", notes[0].lower())
        self.assertIn("map, video or 3D viewer", notes[0])

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


class _HangRecorder(_LeakRecorder):
    pages = {"/": '<html><body><h1>Hello</h1><p>Text.</p><img src="/hang" width="10" height="10"></body></html>'}

    def _handle(self):
        if self.path.split("?")[0] == "/hang":
            time.sleep(30)  # longer than the test's --timeout; its thread is a daemon
            return
        super()._handle()

    do_GET = do_POST = do_HEAD = do_OPTIONS = _handle


@SKIP
class SlowLoadEventTest(unittest.TestCase):
    def test_a_file_that_never_arrives_does_not_stop_either_view(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), _HangRecorder)
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with tempfile.TemporaryDirectory() as tmp:
            done = subprocess.run([sys.executable, str(SCRIPT), "http://127.0.0.1:%d/" % server.server_address[1],
                                   "--out", tmp, "--timeout", "5"], capture_output=True, text=True, timeout=120)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            render = json.loads((Path(tmp) / "render.json").read_text())
            log = json.loads((Path(tmp) / "network-log.json").read_text())
        self.assertEqual(sorted(render["viewports"]), ["desktop", "phone"])
        self.assertEqual(render["could_not_check"], [])
        self.assertIs(render["viewports"]["phone"]["load_event"], False)
        hung = [e for e in log if e["url"].endswith("/hang")]
        self.assertTrue(hung)
        self.assertNotIn("completed", {e["outcome"] for e in hung})


@SKIP
class RenderFactsTest(_LocalPages):
    script = SCRIPT

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
        rules = cro_runtime.host_rules()
        self.assertTrue(rules.startswith("--host-resolver-rules="), rules[:40])
        for host in cro_runtime.BLOCKED_HOSTS:
            self.assertIn("MAP %s ~NOTFOUND" % host, rules)
            self.assertIn("MAP *.%s ~NOTFOUND" % host, rules)


@SKIP
class RenderCheckLeakPaths(GuardLeakPathsMixin, unittest.TestCase):
    @classmethod
    def run_route(cls, url, out):
        done = subprocess.run([sys.executable, str(SCRIPT), url, "--out", str(out)],
                              capture_output=True, text=True, timeout=120)
        assert done.returncode == 0, done.stderr
        cls.errors_by_run[out.parent.name] = json.loads((out / "render.json").read_text())["errors"]
        return json.loads((out / "network-log.json").read_text())


if __name__ == "__main__":
    unittest.main()
