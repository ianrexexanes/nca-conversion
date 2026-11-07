"""Shared pieces for the form tests: a local server that records every request, and a runner for the two form scripts.

The server answers on 127.0.0.1 with the archetype pages in fixtures/form-*.html. It counts each request's method and path
and keeps the agent and the body, so a test can say what reached it and what did not. Nothing here points at a live site.
"""
import json
import re
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript"}
CORS = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
        "Access-Control-Allow-Headers": "content-type"}
LINE = re.compile(r"^(FAIL|WARN|SKIPPED) (form\d+) ([A-Z][A-Z0-9_]*)\b:?\s?(.*)$")


class FormServer(BaseHTTPRequestHandler):
    requests = []
    lock = threading.Lock()

    def _go(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode("utf-8", "replace") if length else ""
        with FormServer.lock:
            FormServer.requests.append((self.command, self.path, self.headers.get("User-Agent", ""), body))
        path = self.path.split("?", 1)[0]
        target = FIXTURES / path.lstrip("/")
        if self.command == "OPTIONS":
            self._send(204, b"", None, CORS)
        elif self.command == "POST" and path in ("/lead", "/lead-cors", "/lead-twice"):
            self._send(200, b'{"ok": true}', "application/json", CORS)
        elif self.command == "POST" and path in ("/sink", "/api/event"):
            self._send(200, b"{}", "application/json", CORS)
        elif self.command == "POST" and path == "/lead-prg":
            self._send(303, b"", None, {"Location": "/lead-prg"})
        elif self.command == "GET" and path == "/lead-prg":
            self._send(200, (FIXTURES / "form-thanks.html").read_bytes(), TYPES[".html"])
        elif self.command == "POST" and path == "/lead-307":
            self._send(307, b"", None, {"Location": "/sink"})
        elif self.command == "POST" and path == "/lead-303":
            self._send(303, b"", None, {"Location": "/form-thanks.html"})
        elif path == "/favicon.ico":
            self._send(204, b"", None)
        elif self.command in ("GET", "HEAD") and target.is_file() and target.parent == FIXTURES and target.name.startswith("form-"):
            text = target.read_text(encoding="utf-8").replace("{{PORT}}", str(self.server.server_address[1]))
            self._send(200, text.encode("utf-8"), TYPES.get(target.suffix, "text/plain"))
        else:
            self._send(404, b"<!doctype html><title>Not found</title><p>Not found</p>", "text/html; charset=utf-8")

    def _send(self, status, body, ctype, headers=None):
        self.send_response(status)
        if ctype:
            self.send_header("Content-Type", ctype)
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD" and body:
            self.wfile.write(body)

    do_GET = do_HEAD = do_POST = do_OPTIONS = _go

    def log_message(self, *args):
        pass


def start_server():
    """(server, base address). The caller registers server_close and shutdown as cleanups."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), FormServer)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, "http://127.0.0.1:%d" % server.server_address[1]


class Run:
    """One run of a form script: its exit code and output, the files it wrote and the requests the server saw meanwhile."""

    def __init__(self, code, out, err, seen, folder):
        self.code, self.out, self.err, self.seen, self.dir = code, out, err, seen, Path(folder)
        self.lines = [(m.group(1), m.group(2), m.group(3), m.group(4)) for m in map(LINE.match, out.splitlines()) if m]
        self.data = self._json("form.json", {})
        self.log = self._json("network-log.json", [])

    def _json(self, name, default):
        try:
            return json.loads((self.dir / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return default

    @property
    def form(self):
        forms = self.data.get("forms") or []
        return forms[0] if forms else {}

    def posts(self, prefix=""):
        return [(m, p) for m, p, _a, _b in self.seen if m == "POST" and p.startswith(prefix)]

    def paths(self):
        return [p for _m, p, _a, _b in self.seen]

    def rules(self, levels=("FAIL", "WARN")):
        return {(lv, r) for lv, _f, r, _d in self.lines if lv in levels}

    def logged(self, url_part, outcome, rule_prefix=""):
        return [e for e in self.log if url_part in e["url"] and e["outcome"] == outcome and (e["rule"] or "").startswith(rule_prefix)]


def run_script(script, url, *args, tmp):
    """Run a form script with the venv's Python (the caller's) into a fresh folder under tmp."""
    folder = tempfile.mkdtemp(dir=tmp)
    with FormServer.lock:
        mark = len(FormServer.requests)
    done = subprocess.run([sys.executable, str(script), url, "--out", folder, *args], capture_output=True, text=True, timeout=300)
    with FormServer.lock:
        seen = list(FormServer.requests[mark:])
    return Run(done.returncode, done.stdout, done.stderr, seen, folder)
