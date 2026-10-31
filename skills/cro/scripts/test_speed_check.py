import contextlib
import datetime
import io
import json
import os
import subprocess
import tempfile
import unittest
import urllib.error
import urllib.parse
from pathlib import Path
from unittest import mock

import cro_runtime
import speed_check

SAMPLE = (Path(__file__).resolve().parent / "fixtures" / "psi-sample.json").read_bytes()
KEY = "SECRET-XYZ"


class _Response:
    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def run_main(argv, key=KEY):
    env = {k: v for k, v in os.environ.items() if k != cro_runtime.KEY_ENV}
    if key:
        env[cro_runtime.KEY_ENV] = key
    out, err = io.StringIO(), io.StringIO()
    with mock.patch.dict(os.environ, env, clear=True), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = speed_check.main(argv)
    return code, out.getvalue(), err.getvalue()


class _NoKeyFile(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        patcher = mock.patch.object(cro_runtime, "KEY_FILE", Path(folder.name) / "pagespeed.key")
        patcher.start()
        self.addCleanup(patcher.stop)


class PagespeedPathTest(_NoKeyFile):
    def test_parses_pagespeed_lab_and_field_values(self):
        with mock.patch.object(speed_check.urllib.request, "urlopen", return_value=_Response(SAMPLE)):
            code, out, _err = run_main(["https://example.com/", "--strategy", "mobile"])
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual((data["source"], data["label"]), ("pagespeed", "PageSpeed Insights"))
        mobile = data["results"]["mobile"]
        self.assertEqual(mobile["performance"], 55)
        self.assertEqual(mobile["lcp_s"], 4.7)
        self.assertEqual(mobile["cls"], 0.05)
        self.assertEqual(mobile["tbt_ms"], 310)
        # CrUX reports layout shift times 100: a percentile of 5 parses as 0.05.
        self.assertEqual(mobile["field"], {"lcp_s": 3.9, "inp_ms": 240, "cls": 0.05})

    def test_key_sent_in_header_not_url(self):
        seen = []

        def fake(req, timeout=None):
            seen.append(req)
            return _Response(SAMPLE)

        with mock.patch.object(speed_check.urllib.request, "urlopen", side_effect=fake):
            run_main(["https://example.com/", "--strategy", "mobile"])
        req = seen[0]
        self.assertNotIn("key=", req.full_url)
        self.assertEqual(req.get_header("X-goog-api-key"), KEY)  # urllib normalises header case

    def test_key_never_printed_on_http_error(self):
        url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?key=%s&url=x" % KEY
        err = urllib.error.HTTPError(url, 403, "Forbidden for url " + url, {}, None)
        failed = subprocess.CompletedProcess([], 1, stdout="", stderr="lighthouse failed " + KEY)
        with mock.patch.object(speed_check.urllib.request, "urlopen", side_effect=err), \
             mock.patch.object(speed_check.subprocess, "run", return_value=failed):
            code, out, errtext = run_main(["https://example.com/", "--strategy", "mobile"])
        self.assertNotIn(KEY, out)
        self.assertNotIn(KEY, errtext)
        self.assertEqual(code, 0)

    def test_quota_error_falls_back_to_lighthouse(self):
        quota = urllib.error.HTTPError("https://x", 429, "Too Many Requests", {}, None)
        lab = subprocess.CompletedProcess([], 0, stdout=lighthouse_report(), stderr="")
        with mock.patch.object(speed_check.urllib.request, "urlopen", side_effect=quota), \
             mock.patch.object(speed_check.subprocess, "run", return_value=lab):
            code, out, _err = run_main(["https://example.com/", "--strategy", "mobile"])
        self.assertEqual(json.loads(out)["source"], "lighthouse-lab")


def lighthouse_report():
    full = json.loads(SAMPLE)
    return json.dumps({"categories": full["lighthouseResult"]["categories"], "audits": full["lighthouseResult"]["audits"]})


class LighthousePathTest(_NoKeyFile):
    def test_without_key_uses_lighthouse_with_block_patterns(self):
        lab = subprocess.CompletedProcess([], 0, stdout=lighthouse_report(), stderr="")
        with mock.patch.object(speed_check.subprocess, "run", return_value=lab) as run:
            code, out, _err = run_main(["https://example.com/", "--strategy", "mobile"], key=None)
        args = run.call_args[0][0]
        for pattern in cro_runtime.lighthouse_block_patterns():
            self.assertIn("--blocked-url-patterns=" + pattern, args)
        data = json.loads(out)
        self.assertEqual((data["source"], data["label"]), ("lighthouse-lab", "lab data"))

    def test_lighthouse_failure_gives_could_not_check(self):
        failed = subprocess.CompletedProcess([], 1, stdout="", stderr="boom")
        with mock.patch.object(speed_check.subprocess, "run", return_value=failed):
            code, out, _err = run_main(["https://example.com/", "--strategy", "mobile"], key=None)
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual((data["source"], data["label"]), ("none", "could not check"))
        self.assertTrue(data["reason"])


def lighthouse_ok():
    return subprocess.CompletedProcess([], 0, stdout=lighthouse_report(), stderr="")


def psi_body(**changes):
    data = json.loads(SAMPLE)
    for name, value in changes.items():
        if value is None:
            data.pop(name, None)
        else:
            data[name] = value
    return json.dumps(data).encode()


def exit_code(argv, key=KEY):
    try:
        code, _out, _err = run_main(argv, key)
    except SystemExit as stop:
        return stop.code
    return code


class RulingsTest(_NoKeyFile):
    def test_both_measures_mobile_then_desktop_on_pagespeed(self):
        seen = []

        def fake(req, timeout=None):
            seen.append(urllib.parse.parse_qs(urllib.parse.urlsplit(req.full_url).query)["strategy"])
            return _Response(SAMPLE)

        with mock.patch.object(speed_check.urllib.request, "urlopen", side_effect=fake):
            code, out, _err = run_main(["https://example.com/"])
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(seen, [["MOBILE"], ["DESKTOP"]])
        self.assertEqual(sorted(data["results"]), ["desktop", "mobile"])
        self.assertEqual((data["source"], data["label"], data["reason"]), ("pagespeed", "PageSpeed Insights", None))

    def test_pagespeed_request_is_the_documented_get(self):
        seen = []

        def fake(req, timeout=None):
            seen.append((req, timeout))
            return _Response(SAMPLE)

        with mock.patch.object(speed_check.urllib.request, "urlopen", side_effect=fake):
            run_main(["https://example.com/a?b=1", "--strategy", "desktop"])
        req, timeout = seen[0]
        parts = urllib.parse.urlsplit(req.full_url)
        self.assertEqual((parts.scheme, parts.netloc, parts.path),
                         ("https", "www.googleapis.com", "/pagespeedonline/v5/runPagespeed"))
        self.assertEqual(urllib.parse.parse_qs(parts.query),
                         {"url": ["https://example.com/a?b=1"], "strategy": ["DESKTOP"], "category": ["PERFORMANCE"]})
        self.assertEqual(req.get_method(), "GET")
        self.assertEqual(timeout, 120)

    def test_key_file_is_read_through_cro_runtime(self):
        cro_runtime.KEY_FILE.write_text("FILE-KEY-123\n", encoding="utf-8")
        cro_runtime.KEY_FILE.chmod(0o600)
        seen = []

        def fake(req, timeout=None):
            seen.append(req.get_header("X-goog-api-key"))
            return _Response(SAMPLE)

        with mock.patch.object(speed_check.urllib.request, "urlopen", side_effect=fake):
            _code, out, err = run_main(["https://example.com/", "--strategy", "mobile"], key=None)
        self.assertEqual(seen, ["FILE-KEY-123"])
        self.assertEqual(json.loads(out)["source"], "pagespeed")
        self.assertNotIn("FILE-KEY-123", out + err)

    def test_lighthouse_command(self):
        with mock.patch.object(speed_check.subprocess, "run", return_value=lighthouse_ok()) as run:
            code, out, _err = run_main(["https://example.com/"], key=None)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["reason"], "pagespeed key missing")
        (mobile, mobile_kwargs), (desktop, desktop_kwargs) = [(c.args[0], c.kwargs) for c in run.call_args_list]
        rules = ", ".join("MAP %s ~NOTFOUND, MAP *.%s ~NOTFOUND" % (s, s) for s in cro_runtime.BLOCKED_HOSTS)
        head = ["npx", "--yes", "lighthouse@" + speed_check.LIGHTHOUSE_VERSION, "https://example.com/",
                "--output=json", "--output-path=stdout", "--quiet", "--only-categories=performance",
                '--chrome-flags=--headless=new --host-resolver-rules="%s"' % rules, "--skip-audits=bf-cache"]
        tail = ["--blocked-url-patterns=" + glob for glob in cro_runtime.lighthouse_block_patterns()]
        self.assertEqual(mobile, head + tail)
        self.assertEqual(desktop, head + ["--preset=desktop"] + tail)
        for kwargs in (mobile_kwargs, desktop_kwargs):
            self.assertEqual(kwargs, {"capture_output": True, "text": True, "timeout": 300})

    def test_pagespeed_failures_fall_back_with_fixed_reasons(self):
        address = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?key=" + KEY
        cases = [
            (urllib.error.HTTPError(address, 429, "quota " + KEY, {}, None), "pagespeed quota"),
            (urllib.error.HTTPError(address, 400, "bad " + KEY, {}, None), "pagespeed refused"),
            (urllib.error.HTTPError(address, 500, "down " + address, {}, None), "pagespeed refused"),
            (urllib.error.URLError("no route to " + address), "pagespeed unreachable"),
            (TimeoutError("timed out " + address), "pagespeed unreachable"),
            (ConnectionResetError("reset " + address), "pagespeed unreachable"),
            (_Response(b"<html>" + KEY.encode()), "pagespeed bad response"),
            (_Response(b'{"error": {"message": "x"}}'), "pagespeed bad response"),
        ]
        for index, (answer, reason) in enumerate(cases):
            with self.subTest(case=index):
                fake = {"return_value": answer} if isinstance(answer, _Response) else {"side_effect": answer}
                with mock.patch.object(speed_check.urllib.request, "urlopen", **fake), \
                     mock.patch.object(speed_check.subprocess, "run", return_value=lighthouse_ok()):
                    code, out, err = run_main(["https://example.com/", "--strategy", "mobile"])
                data = json.loads(out)
                self.assertEqual(code, 0)
                self.assertEqual((data["source"], data["label"], data["reason"]), ("lighthouse-lab", "lab data", reason))
                self.assertNotIn(KEY, out + err)
                self.assertNotIn("googleapis", out + err)

    def test_lighthouse_failures_give_could_not_check_with_fixed_reasons(self):
        cases = [
            (subprocess.CompletedProcess([], 1, stdout="", stderr="Runtime error " + KEY), "lighthouse exited 1"),
            (subprocess.CompletedProcess([], 0, stdout="not json", stderr=""), "lighthouse bad output"),
            (FileNotFoundError(2, "No such file or directory", "npx"), "lighthouse missing"),
            (subprocess.TimeoutExpired(["npx"], 300), "lighthouse timed out"),
        ]
        for index, (answer, reason) in enumerate(cases):
            with self.subTest(case=index):
                fake = {"return_value": answer} if isinstance(answer, subprocess.CompletedProcess) else {"side_effect": answer}
                with mock.patch.object(speed_check.subprocess, "run", **fake):
                    code, out, err = run_main(["https://example.com/", "--strategy", "mobile"], key=None)
                data = json.loads(out)
                self.assertEqual(code, 0)
                self.assertEqual((data["source"], data["label"], data["results"]), ("none", "could not check", {}))
                self.assertEqual(data["reason"], "pagespeed key missing; " + reason)
                self.assertNotIn(KEY, out + err)

    def test_one_source_per_run(self):
        answers = [_Response(SAMPLE), urllib.error.HTTPError("https://x", 503, "down", {}, None)]
        with mock.patch.object(speed_check.urllib.request, "urlopen", side_effect=answers), \
             mock.patch.object(speed_check.subprocess, "run", return_value=lighthouse_ok()) as run:
            _code, out, _err = run_main(["https://example.com/"])
        data = json.loads(out)
        self.assertEqual(run.call_count, 2)
        self.assertEqual((data["source"], data["reason"]), ("lighthouse-lab", "pagespeed refused"))
        self.assertEqual(sorted(data["results"]), ["desktop", "mobile"])
        lab = [lighthouse_ok(), subprocess.CompletedProcess([], 1, stdout="", stderr="")]
        with mock.patch.object(speed_check.subprocess, "run", side_effect=lab):
            _code, out, _err = run_main(["https://example.com/"], key=None)
        data = json.loads(out)
        self.assertEqual((data["source"], data["results"], data["reason"]),
                         ("none", {}, "pagespeed key missing; lighthouse exited 1"))

    def test_field_reads_null_without_the_page_own_crux_data(self):
        sample = json.loads(SAMPLE)
        bodies = [psi_body(loadingExperience=None),
                  psi_body(loadingExperience={"id": "https://example.com/"}),
                  psi_body(loadingExperience=dict(sample["loadingExperience"], origin_fallback=True))]
        for index, body in enumerate(bodies):
            with self.subTest(case=index):
                with mock.patch.object(speed_check.urllib.request, "urlopen", return_value=_Response(body)):
                    _code, out, _err = run_main(["https://example.com/", "--strategy", "mobile"])
                mobile = json.loads(out)["results"]["mobile"]
                self.assertIsNone(mobile["field"])
                self.assertEqual(mobile["performance"], 55)

    def test_a_missing_value_reads_null(self):
        sample = json.loads(SAMPLE)
        del sample["loadingExperience"]["metrics"]["INTERACTION_TO_NEXT_PAINT"]
        sample["lighthouseResult"]["categories"]["performance"]["score"] = None
        del sample["lighthouseResult"]["audits"]["total-blocking-time"]
        with mock.patch.object(speed_check.urllib.request, "urlopen", return_value=_Response(json.dumps(sample).encode())):
            _code, out, _err = run_main(["https://example.com/", "--strategy", "mobile"])
        data = json.loads(out)
        self.assertEqual(data["source"], "pagespeed")
        self.assertEqual(data["results"]["mobile"], {"performance": None, "lcp_s": 4.7, "cls": 0.05, "tbt_ms": None,
                                                     "field": {"lcp_s": 3.9, "inp_ms": None, "cls": 0.05}})

    def test_output_shape_and_out_file(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "audit-data" / "page-2026-10-31" / "speed.json"
            with mock.patch.object(speed_check.urllib.request, "urlopen", return_value=_Response(SAMPLE)):
                code, out, _err = run_main(["https://example.com/", "--strategy", "mobile", "--out", str(target)])
            data = json.loads(out)
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), data)
        self.assertEqual(sorted(data), ["checked_at", "label", "reason", "results", "source", "url"])
        self.assertEqual(sorted(data["results"]), ["mobile"])
        self.assertEqual(sorted(data["results"]["mobile"]), ["cls", "field", "lcp_s", "performance", "tbt_ms"])
        self.assertEqual(data["checked_at"], datetime.date.today().isoformat())
        self.assertEqual(data["url"], "https://example.com/")

    def test_bad_arguments_exit_2_before_anything_is_measured(self):
        with tempfile.TemporaryDirectory() as folder:
            blocker = Path(folder) / "a-file"
            blocker.write_text("x", encoding="utf-8")
            for argv in ([], ["https://example.com/", "--strategy", "fast"],
                         ["https://example.com/", "--out", str(blocker / "speed.json")]):
                with self.subTest(argv=argv):
                    with mock.patch.object(speed_check.urllib.request, "urlopen") as urlopen, \
                         mock.patch.object(speed_check.subprocess, "run") as run:
                        self.assertEqual(exit_code(argv), 2)
                    urlopen.assert_not_called()
                    run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
