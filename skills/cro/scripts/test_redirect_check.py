import json
import re
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "conversion-page-audit" / "scripts"))
import page_facts  # noqa: E402
import redirect_check  # noqa: E402

SCRIPT = HERE / "redirect_check.py"
CASE = {"from": "http://a.test/", "to": "https://a.test/new", "status": 200}


def run(*args):
    done = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    return done.returncode, done.stdout + done.stderr


def rules(case, hops):
    return sorted({row[1] for row in redirect_check.judge(case, hops)})


class JudgeTests(unittest.TestCase):
    def test_judge_passes_a_301_chain_to_https(self):
        self.assertEqual(redirect_check.judge(CASE, [("http://a.test/", 301), ("https://a.test/", 301), ("https://a.test/new", 200)]), [])

    def test_judge_fails_a_302_hop_by_default(self):
        self.assertEqual(rules(CASE, [("http://a.test/", 302), ("https://a.test/new", 200)]), ["REDIRECT_STATUS"])

    def test_listed_hops_allow_a_302(self):
        self.assertEqual(rules(dict(CASE, hops=[302, 200]), [("http://a.test/", 302), ("https://a.test/new", 200)]), [])
        self.assertEqual(rules(dict(CASE, hops=[301, 200]), [("http://a.test/", 302), ("https://a.test/new", 200)]), ["REDIRECT_STATUS"])

    def test_sixth_hop_fails(self):
        hops = [("http://a.test/%d" % i, 301) for i in range(6)] + [("https://a.test/new", 200)]
        self.assertEqual(rules(CASE, hops), ["REDIRECT_HOPS"])
        self.assertEqual(rules(CASE, hops[1:]), [])  # five redirects are allowed

    def test_wrong_target_fails(self):
        self.assertEqual(rules(CASE, [("http://a.test/", 301), ("https://a.test/other", 200)]), ["REDIRECT_TARGET"])

    def test_http_end_fails(self):
        self.assertEqual(rules(dict(CASE, to="http://a.test/new"), [("http://a.test/", 301), ("http://a.test/new", 200)]),
                         ["REDIRECT_HTTPS"])

    def test_last_status_must_match(self):
        self.assertEqual(rules(CASE, [("http://a.test/", 301), ("https://a.test/new", 404)]), ["REDIRECT_STATUS"])

    def test_a_chain_that_never_ends_fails_on_hops_and_target(self):
        hops = [("http://a.test/%d" % i, 301) for i in range(6)]
        self.assertEqual(rules(CASE, hops), ["REDIRECT_HOPS", "REDIRECT_HTTPS", "REDIRECT_STATUS", "REDIRECT_TARGET"])


class _Chain(BaseHTTPRequestHandler):
    agents = []
    ftp_port = 0

    def do_GET(self):
        _Chain.agents.append(self.headers.get("User-Agent"))
        port = self.server.server_address[1]
        moves = {"/r1": "/r2", "/r2": "http://127.0.0.1:%d/final" % port, "/loop": "/loop",
                 "/ftp": "ftp://127.0.0.1:%d/x" % _Chain.ftp_port, "/file": "file:///etc/hostname", "/space": "/thank you"}
        odd = {"/m300": 300, "/m305": 305}  # 3xx answers that urllib hands back as an HTTPError
        if self.path in odd:
            self.send_response(odd[self.path])
            self.send_header("Location", "http://[::1")
            self.end_headers()
        elif self.path in moves:
            self.send_response(301)
            self.send_header("Location", moves[self.path])
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


class FollowTests(unittest.TestCase):
    def setUp(self):
        _Chain.agents = []
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _Chain)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]

    def test_follow_reads_a_local_chain_and_sends_an_ordinary_chrome_agent(self):
        hops = redirect_check.follow(self.base + "/r1")
        self.assertEqual(hops, [(self.base + "/r1", 301), (self.base + "/r2", 301), (self.base + "/final", 200)])
        self.assertTrue(_Chain.agents and all(agent == page_facts.CHROME_UA for agent in _Chain.agents), _Chain.agents)

    def test_follow_stops_one_past_the_limit(self):
        hops = redirect_check.follow(self.base + "/loop")
        self.assertEqual(len(hops), 6)
        self.assertTrue(all(status == 301 for _, status in hops))

    def test_a_redirect_to_ftp_or_file_is_not_followed(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(0.5)
        self.addCleanup(listener.close)
        _Chain.ftp_port = listener.getsockname()[1]
        for path, target in (("/ftp", "ftp://127.0.0.1:%d/x" % _Chain.ftp_port), ("/file", "file:///etc/hostname")):
            try:
                hops = redirect_check.follow(self.base + path)
            except Exception as error:  # a crash is a failed assertion here
                self.fail("follow raised %r on %s" % (error, path))
            self.assertEqual(hops, [(self.base + path, 301), (target, 0)])
        with self.assertRaises(socket.timeout):
            listener.accept()  # nothing connected to the ftp address
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        cases = Path(tmp.name) / "cases.json"
        cases.write_text(json.dumps([{"from": self.base + "/file", "to": "https://a.test/", "status": 200}]), encoding="utf-8")
        code, out = run("--cases", str(cases))
        self.assertEqual(code, 1, out)
        self.assertNotIn("Traceback", out)

    def test_a_redirect_that_cannot_be_requested_is_a_fail_row_not_a_crash(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        cases = Path(tmp.name) / "cases.json"
        cases.write_text(json.dumps([{"from": self.base + "/space", "to": self.base + "/final", "status": 200},
                                     {"from": self.base + "/r1", "to": self.base + "/final", "status": 200}]), encoding="utf-8")
        code, out = run("--cases", str(cases))
        self.assertNotIn("Traceback", out)
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"FAIL %s\S* REDIRECT_TARGET" % re.escape(self.base + "/space"))
        self.assertRegex(out, r"FAIL %s\S* REDIRECT_HTTPS" % re.escape(self.base + "/r1"))

    def test_a_300_or_305_with_a_location_that_cannot_be_parsed_ends_the_chain_there(self):
        for path, status in (("/m300", 300), ("/m305", 305)):
            try:
                hops = redirect_check.follow(self.base + path)
            except Exception as error:  # a crash is a failed assertion here
                self.fail("follow raised %r on %s" % (error, path))
            self.assertEqual(hops, [(self.base + path, status)])
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        cases = Path(tmp.name) / "cases.json"
        cases.write_text(json.dumps([{"from": self.base + "/m300", "to": self.base + "/final", "status": 200},
                                     {"from": self.base + "/m305", "to": self.base + "/final", "status": 200}]), encoding="utf-8")
        code, out = run("--cases", str(cases))
        self.assertNotIn("Traceback", out)
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"FAIL %s/m300 REDIRECT_STATUS" % re.escape(self.base))
        self.assertRegex(out, r"FAIL %s/m305 REDIRECT_STATUS" % re.escape(self.base))

    def test_an_unreachable_host_ends_the_chain_with_status_0(self):
        self.assertEqual(redirect_check.follow("http://127.0.0.1:1/x"), [("http://127.0.0.1:1/x", 0)])

    def test_cli_on_an_http_chain_gives_redirect_https_only(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        cases = Path(tmp.name) / "cases.json"
        cases.write_text(json.dumps([{"from": self.base + "/r1", "to": self.base + "/final", "status": 200}]), encoding="utf-8")
        code, out = run("--cases", str(cases))
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"(?m)^FAIL %s/r1 REDIRECT_HTTPS: " % self.base)
        self.assertNotRegex(out, r"REDIRECT_(TARGET|STATUS|HOPS)")
        self.assertTrue(out.rstrip().endswith("redirect_check: 1 FAIL, 0 WARN"), out)

    def test_redirect_code_as_status_gets_a_hint(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        cases = Path(tmp.name) / "cases.json"
        hint = "status is the final answer's status at \"to\" (usually 200), not the redirect's"
        for status, hinted in ((301, True), (200, False)):
            cases.write_text(json.dumps([{"from": self.base + "/r1", "to": self.base + "/final", "status": status}]), encoding="utf-8")
            code, out = run("--cases", str(cases))
            self.assertEqual(code, 1, out)  # the loopback chain is HTTP, so REDIRECT_HTTPS fails either way
            if hinted:
                self.assertRegex(out, r"(?m)^FAIL %s/r1 REDIRECT_STATUS: .*%s" % (self.base, re.escape(hint)))
            else:
                self.assertNotIn("REDIRECT_STATUS", out)
                self.assertEqual(set(re.findall(r"(?m)^FAIL \S+ (\w+)", out)), {"REDIRECT_HTTPS"}, out)
                self.assertNotIn(hint, out)

    def test_bad_cases_exit_2(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "cases.json"
        for text in ("{not json", "{}", '[{"from": "http://a.test/"}]', '[{"from": "x", "to": "y", "status": "200"}]',
                     '[{"from": "x", "to": "y", "status": 200, "hops": "301"}]'):
            path.write_text(text, encoding="utf-8")
            code, out = run("--cases", str(path))
            self.assertEqual(code, 2, (text, out))
            self.assertTrue(out.startswith("redirect_check: "), out)
        self.assertEqual(run("--cases", str(Path(tmp.name) / "absent.json"))[0], 2)
        self.assertEqual(run()[0], 2)


if __name__ == "__main__":
    unittest.main()
