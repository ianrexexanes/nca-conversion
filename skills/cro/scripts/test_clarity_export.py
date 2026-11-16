import contextlib
import hashlib
import io
import json
import os
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

import clarity_export
import cro_runtime

TOKEN = "test-token-123"


class FakeApi:
    """A local export API on 127.0.0.1 that logs every request it receives."""

    def __init__(self):
        self.log = []
        self.respond = lambda number, path: (200, json.dumps([]).encode(), {})
        api = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                api.log.append({"method": self.command, "path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()}})
                status, body, headers = api.respond(len(api.log), self.path)
                self.send_response(status)
                for key, value in headers.items():
                    self.send_header(key, value)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=0.01), daemon=True)
        self.thread.start()

    @property
    def url(self):
        return "http://127.0.0.1:%d/export" % self.server.server_address[1]

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


def metrics_body(rows=1, name="Traffic"):
    return json.dumps([{"metricName": name, "information": [{"url": "https://example.test/", "n": str(i)} for i in range(rows)]}]).encode()


class ExportCase(unittest.TestCase):
    def setUp(self):
        self.api = FakeApi()
        self.addCleanup(self.api.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = self.root / "data"
        self.token_file = self.root / "project.token"
        self.default_file = self.root / "clarity.token"
        patches = [
            mock.patch.object(cro_runtime, "CLARITY_FILE", self.default_file),
            mock.patch.dict(os.environ, {k: v for k, v in os.environ.items() if k != cro_runtime.CLARITY_ENV}, clear=True),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        os.environ[cro_runtime.CLARITY_ENV] = TOKEN

    def run_main(self, *extra, endpoint=True, project="demo", days="3"):
        argv = ["--project", project, "--days", days, "--data-dir", str(self.data)]
        if endpoint:
            argv += ["--endpoint", self.api.url]
        argv += list(extra)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = clarity_export.main(argv)
            except SystemExit as exit_:
                code = exit_.code
        return code, out.getvalue(), err.getvalue()

    def budget(self):
        return json.loads((self.data / "clarity-budget.json").read_text())

    def key(self, label, where, project="demo"):
        return hashlib.sha256(f"{label}:{where}:{project}".encode()).hexdigest()[:16]


class RequestTest(ExportCase):
    def test_token_sent_only_in_the_bearer_header(self):
        self.api.respond = lambda n, p: (200, metrics_body(), {})
        code, out, err = self.run_main("--dimension", "URL", "--dimension", "Device")
        self.assertEqual(code, 0)
        self.assertEqual(len(self.api.log), 1)
        request = self.api.log[0]
        self.assertEqual(request["headers"]["authorization"], "Bearer " + TOKEN)
        self.assertNotIn(TOKEN, request["path"])
        for name, value in request["headers"].items():
            if name != "authorization":
                self.assertNotIn(TOKEN, value, name)
        self.assertEqual(request["path"], "/export?numOfDays=3&dimension1=URL&dimension2=Device")
        self.assertNotIn(TOKEN, out + err)
        self.assertNotIn(TOKEN, (self.data / "clarity-budget.json").read_text())

    def test_output_maps_each_metric_to_its_rows(self):
        self.api.respond = lambda n, p: (200, json.dumps([
            {"metricName": "Traffic", "information": [{"a": "1"}]},
            {"metricName": "Traffic", "information": [{"a": "2"}]},
            {"metricName": "ScrollDepth", "information": [{"b": "9"}]}]).encode(), {})
        code, out, _ = self.run_main("--dimension", "Device")
        result = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(result["metrics"], {"Traffic": [{"a": "1"}, {"a": "2"}], "ScrollDepth": [{"b": "9"}]})
        self.assertEqual((result["project"], result["days"], result["dimensions"], result["source"], result["truncated"], result["reason"]),
                         ("demo", 3, ["Device"], "clarity", False, None))
        self.assertTrue(result["checked_at"].endswith("+00:00"))

    def test_out_flag_writes_the_file_and_prints_one_line(self):
        self.api.respond = lambda n, p: (200, metrics_body(2), {})
        target = self.root / "sub" / "clarity.json"
        code, out, _ = self.run_main("--out", str(target))
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "clarity_export: wrote %s: 1 metrics, 2 rows" % target)
        self.assertEqual(len(json.loads(target.read_text())["metrics"]["Traffic"]), 2)

    def test_thousand_rows_marks_truncated(self):
        for rows, expected in ((1000, True), (999, False)):
            self.api.respond = lambda n, p, rows=rows: (200, metrics_body(rows), {})
            code, out, _ = self.run_main()
            self.assertEqual(code, 0)
            self.assertIs(json.loads(out)["truncated"], expected, rows)

    def test_a_malformed_answer_is_exit_3_without_the_body(self):
        for body in (b"not json", b'{"metricName": "x"}', b'[{"metricName": 5, "information": []}]', b'[{"metricName": "x", "information": "no"}]'):
            self.api.respond = lambda n, p, body=body: (200, body, {})
            code, out, err = self.run_main()
            self.assertEqual(code, 3, body)
            self.assertEqual(json.loads(out)["metrics"], {})
            self.assertNotIn(TOKEN, out + err)

    def test_unreachable_address_is_exit_3_and_counts(self):
        self.api.stop()
        code, out, err = self.run_main()
        self.assertEqual(code, 3)
        self.assertIn("could not be reached", out)
        self.assertNotIn(TOKEN, out + err)
        self.assertEqual(list(self.budget().values())[0]["count"], 1)


class HttpErrorTest(ExportCase):
    def test_token_never_printed_on_http_error(self):
        for status in (401, 403, 400, 429):
            self.api.respond = lambda n, p, status=status: (status, ("echo " + TOKEN).encode(), {})
            with self.subTest(status=status):
                code, out, err = self.run_main()
                self.assertEqual(code, 3)
                self.assertIn(str(status), out)
                self.assertNotIn(TOKEN, out + err)
                self.assertEqual(json.loads(out)["metrics"], {})

    def test_429_is_reported_even_when_the_local_count_is_low(self):
        self.api.respond = lambda n, p: (429, b"Exceeded daily limit", {})
        code, out, _ = self.run_main()
        self.assertEqual(code, 3)
        self.assertIn("daily limit", out)
        self.assertEqual(list(self.budget().values())[0]["count"], 1)

    def test_redirect_is_not_followed(self):
        self.api.respond = lambda n, p: (302, b"", {"Location": "/elsewhere"}) if p.startswith("/export") else (200, metrics_body(), {})
        code, out, err = self.run_main()
        self.assertEqual(code, 3)
        self.assertIn("302", out)
        self.assertEqual([r["path"].split("?")[0] for r in self.api.log], ["/export"])
        self.assertNotIn(TOKEN, out + err)

    def test_other_status_is_refused(self):
        self.api.respond = lambda n, p: (500, b"", {})
        code, out, _ = self.run_main()
        self.assertEqual(code, 3)
        self.assertIn("HTTP 500", out)


class BudgetTest(ExportCase):
    def test_eleventh_request_is_refused_before_sending(self):
        self.api.respond = lambda n, p: (200, metrics_body(), {})
        for _ in range(10):
            self.assertEqual(self.run_main()[0], 0)
        code, out, _ = self.run_main()
        self.assertEqual(code, 4)
        self.assertEqual(len(self.api.log), 10)
        result = json.loads(out)
        self.assertEqual(result["metrics"], {})
        self.assertIn("ten requests", result["reason"])
        self.assertEqual(list(self.budget().values())[0]["count"], 10)

    def test_budget_resets_at_utc_midnight(self):
        self.run_main()
        key = list(self.budget())[0]
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
        (self.data / "clarity-budget.json").write_text(json.dumps({key: {"day": yesterday, "count": 10}, "other": {"day": yesterday, "count": 3}}))
        self.api.respond = lambda n, p: (200, metrics_body(), {})
        code, _, _ = self.run_main()
        self.assertEqual(code, 0)
        today = datetime.now(timezone.utc).date().isoformat()
        self.assertEqual(self.budget()[key], {"day": today, "count": 1})
        self.assertEqual(self.budget()["other"]["count"], 3)

    def test_budget_key_holds_no_token(self):
        self.run_main()
        text = (self.data / "clarity-budget.json").read_text()
        self.assertNotIn(TOKEN, text)
        self.assertEqual(list(json.loads(text)), [self.key("env", "NCA_CLARITY_TOKEN")])

    def test_each_project_has_its_own_count(self):
        self.run_main(project="one")
        self.run_main(project="two")
        self.assertEqual(sorted(self.budget()), sorted([self.key("env", "NCA_CLARITY_TOKEN", "one"), self.key("env", "NCA_CLARITY_TOKEN", "two")]))

    def test_a_default_file_token_keys_on_the_file_path(self):
        del os.environ[cro_runtime.CLARITY_ENV]
        self.default_file.write_text(TOKEN)
        os.chmod(self.default_file, 0o600)
        self.run_main()
        self.assertEqual(list(self.budget()), [self.key("file", str(self.default_file))])

    def test_an_unreadable_budget_file_is_read_as_empty(self):
        self.data.mkdir()
        (self.data / "clarity-budget.json").write_text("[not an object")
        self.assertEqual(self.run_main()[0], 0)
        self.assertEqual(list(self.budget().values())[0]["count"], 1)


class TokenTest(ExportCase):
    def test_token_file_flag_reads_a_second_project_token(self):
        self.token_file.write_text("second-token-456\n")
        os.chmod(self.token_file, 0o600)
        code, _, _ = self.run_main("--token-file", str(self.token_file))
        self.assertEqual(code, 0)
        self.assertEqual(self.api.log[0]["headers"]["authorization"], "Bearer second-token-456")
        self.assertEqual(list(self.budget()), [self.key("token-file", str(self.token_file.resolve()))])

    def test_missing_token_gives_a_reason_not_a_crash(self):
        del os.environ[cro_runtime.CLARITY_ENV]
        code, out, err = self.run_main()
        result = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(result["metrics"], {})
        self.assertIn("NCA_CLARITY_TOKEN", result["reason"])
        self.assertIn("--token-file", result["reason"])
        self.assertIn("setup.md", result["reason"])
        self.assertEqual(self.api.log, [])
        self.assertFalse((self.data / "clarity-budget.json").exists())

    def test_unusable_token_is_not_sent(self):
        self.token_file.write_text(TOKEN + "\nsecond line\n")
        code, out, err = self.run_main("--token-file", str(self.token_file))
        self.assertEqual(code, 3)
        self.assertEqual(self.api.log, [])
        self.assertFalse((self.data / "clarity-budget.json").exists())
        self.assertIn("not sent", out)
        self.assertNotIn("test-token", out + err)
        self.assertNotIn("second line", out + err)


class ValidationTest(ExportCase):
    def assert_refused(self, *args, **kwargs):
        patched = mock.patch.object(clarity_export.cro_runtime, "clarity_token")
        with patched as token:
            code, out, err = self.run_main(*args, **kwargs)
        self.assertEqual(code, 2, args)
        self.assertEqual(out, "")
        self.assertNotEqual(err, "")
        token.assert_not_called()
        self.assertEqual(self.api.log, [])
        self.assertFalse((self.data / "clarity-budget.json").exists())
        self.assertNotIn(TOKEN, err)

    def test_days_outside_1_to_3_rejected(self):
        for days in ("0", "4", "x"):
            self.assert_refused(days=days)

    def test_more_than_three_dimensions_rejected(self):
        self.assert_refused("--dimension", "URL", "--dimension", "Device", "--dimension", "OS", "--dimension", "Browser")

    def test_unknown_dimension_rejected(self):
        for name in ("Weather", "url", "Country"):
            self.assert_refused("--dimension", name)

    def test_a_repeated_dimension_is_rejected(self):
        self.assert_refused("--dimension", "URL", "--dimension", "URL")

    def test_a_blank_project_is_rejected(self):
        self.assert_refused(project="   ")

    def test_endpoint_override_refuses_a_non_loopback_host(self):
        bad = ("https://example.com/x", "http://127.0.0.1@host.example/x", "http://127.0.0.1.host.example/x",
               "ftp://127.0.0.1/x", "http://127.0.0.2/x", "http:///x", "127.0.0.1",
               "http://evil.example\\@127.0.0.1/x", "http://user@127.0.0.1/x", "http://a@b@127.0.0.1/x", "http://evil.example%2f@127.0.0.1/x")
        for url in bad:
            with self.subTest(url=url), mock.patch.object(clarity_export.cro_runtime, "clarity_token") as token:
                self.assertFalse(clarity_export.loopback_endpoint(url))
                code, out, err = self.run_main("--endpoint", url, endpoint=False)
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                token.assert_not_called()
                self.assertEqual(self.api.log, [])
                self.assertFalse((self.data / "clarity-budget.json").exists())

    def test_loopback_hosts_are_accepted(self):
        self.api.respond = lambda n, p: (200, metrics_body(), {})
        port = self.api.server.server_address[1]
        self.assertTrue(clarity_export.loopback_endpoint("http://LOCALHOST:%d/x" % port))
        self.assertTrue(clarity_export.loopback_endpoint("http://[::1]:%d/x" % port))
        self.assertTrue(clarity_export.loopback_endpoint("https://127.0.0.1/x"))

    def test_out_folder_that_cannot_be_made_is_rejected(self):
        blocker = self.root / "file"
        blocker.write_text("x")
        self.assert_refused("--out", str(blocker / "sub" / "c.json"))


if __name__ == "__main__":
    unittest.main()
