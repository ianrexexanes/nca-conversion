import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import cro_runtime
import doctor

HERE = Path(__file__).resolve().parent


def run_doctor(argv, env=None):
    out = io.StringIO()
    patches = [mock.patch.dict(os.environ, env or {}, clear=False)]
    with contextlib.ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        with contextlib.redirect_stdout(out):
            code = doctor.main(argv)
    return code, out.getvalue()


def no_claude(*args, **kwargs):
    raise FileNotFoundError("claude")


class DoctorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = self.tmp.name
        key_file = mock.patch.object(cro_runtime, "KEY_FILE", Path(self.tmp.name) / "none.key")
        key_file.start()
        self.addCleanup(key_file.stop)
        token_file = mock.patch.object(cro_runtime, "CLARITY_FILE", Path(self.tmp.name) / "none.token")
        token_file.start()
        self.addCleanup(token_file.stop)
        no_env = mock.patch.dict(os.environ, {k: v for k, v in os.environ.items() if k != cro_runtime.CLARITY_ENV}, clear=True)
        no_env.start()
        self.addCleanup(no_env.stop)

    def test_doctor_reports_missing_venv_and_exits_1(self):
        with mock.patch.object(doctor.subprocess, "run", side_effect=no_claude):
            code, out = run_doctor(["--data-dir", self.data])
        self.assertEqual(code, 1)
        self.assertIn("MISSING venv", out)

    def test_doctor_never_prints_the_key(self):
        with mock.patch.object(doctor.subprocess, "run", side_effect=no_claude):
            code, out = run_doctor(["--data-dir", self.data], env={cro_runtime.KEY_ENV: "SECRET-XYZ"})
        self.assertNotIn("SECRET-XYZ", out)
        self.assertIn("OK pagespeed-key: env", out)

    def test_doctor_never_prints_the_clarity_token_and_names_only_its_source(self):
        with mock.patch.object(doctor.subprocess, "run", side_effect=no_claude):
            code, out = run_doctor(["--data-dir", self.data], env={cro_runtime.CLARITY_ENV: "CLARITY-SECRET"})
        self.assertNotIn("CLARITY-SECRET", out)
        self.assertIn("OK clarity-token: env", out)

    def test_a_missing_clarity_token_leaves_the_exit_code_alone(self):
        with mock.patch.object(doctor.subprocess, "run", side_effect=no_claude):
            code, out = run_doctor(["--data-dir", self.data])
            rows = {r["check"]: r["status"] for r in json.loads(run_doctor(["--data-dir", self.data, "--json"])[1])}
        self.assertIn("MISSING clarity-token: missing", out)
        self.assertEqual(code, 1)
        self.assertEqual(rows["clarity-token"], "MISSING")

    def test_a_loose_clarity_token_file_warns(self):
        loose = Path(self.tmp.name) / "loose.token"
        loose.write_text("x")
        os.chmod(loose, 0o644)
        with mock.patch.object(cro_runtime, "CLARITY_FILE", loose), mock.patch.object(doctor.subprocess, "run", side_effect=no_claude):
            code, out = run_doctor(["--data-dir", self.data])
        self.assertIn("WARN clarity-token: file-loose-permissions", out)

    def test_doctor_json_shape(self):
        with mock.patch.object(doctor.subprocess, "run", side_effect=no_claude):
            code, out = run_doctor(["--data-dir", self.data, "--json"])
        rows = json.loads(out)
        self.assertEqual([r["check"] for r in rows],
                         ["python", "venv", "playwright", "browser", "pagespeed-key", "clarity-token", "lighthouse", "companions", "hallmark-lint"])
        for row in rows:
            self.assertEqual(sorted(row), ["check", "detail", "status"])
            self.assertIn(row["status"], ("OK", "WARN", "MISSING"))

    def test_doctor_companions_warn_without_claude_cli(self):
        with mock.patch.object(doctor.subprocess, "run", side_effect=no_claude):
            code, out = run_doctor(["--data-dir", self.data])
        self.assertIn("WARN companions", out)
        # The exit code comes from python, venv, playwright and browser only.
        self.assertEqual(code, 1)  # venv is missing in this temp folder
        listing = subprocess.CompletedProcess([], 0, stdout=json.dumps([{"id": "impeccable@x", "enabled": False}]), stderr="")
        with mock.patch.object(doctor.subprocess, "run", return_value=listing):
            code2, out2 = run_doctor(["--data-dir", self.data])
        self.assertIn("WARN companions", out2)
        self.assertEqual(code2, code)


class HallmarkLintTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        key_file = mock.patch.object(cro_runtime, "KEY_FILE", Path(self.tmp.name) / "none.key")
        key_file.start()
        self.addCleanup(key_file.stop)

    def _line(self, home):
        with mock.patch.object(doctor.Path, "home", return_value=Path(home)), \
                mock.patch.object(doctor.subprocess, "run", side_effect=no_claude):
            code, out = run_doctor(["--data-dir", self.tmp.name, "--json"])
        rows = json.loads(out)
        return code, next(r for r in rows if r["check"] == "hallmark-lint")

    def test_hallmark_lint_line_names_the_script_or_not_found(self):
        with tempfile.TemporaryDirectory() as home:
            code_none, none = self._line(home)
            script = Path(home, ".claude", "plugins", "cache", "stand-in", "hallmark", "9.9.9", "hallmark", "scripts", "sloplint.mjs")
            script.parent.mkdir(parents=True)
            script.write_text("// stand-in\n", encoding="utf-8")
            code_one, found = self._line(home)
        self.assertEqual(none["detail"], "not found")
        self.assertEqual(found["detail"], str(script))
        self.assertIn(none["status"], ("OK", "WARN"))
        self.assertIn(found["status"], ("OK", "WARN"))
        self.assertEqual(code_none, code_one)


class SetupDryRunTest(unittest.TestCase):
    def test_setup_dry_run_pins_playwright(self):
        with tempfile.TemporaryDirectory() as tmp:
            done = subprocess.run([sys.executable, str(HERE / "setup.py"), "--dry-run", "--data-dir", tmp],
                                  capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertIn("playwright==1.62.0", done.stdout)
            self.assertIn(os.path.join(tmp, "venv"), done.stdout)
            self.assertFalse(os.path.exists(os.path.join(tmp, "venv")), "dry run must change nothing")


class CompanionsEnabledTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        key_file = mock.patch.object(cro_runtime, "KEY_FILE", Path(self.tmp.name) / "none.key")
        key_file.start()
        self.addCleanup(key_file.stop)

    def _companions(self, entries):
        listing = subprocess.CompletedProcess([], 0, stdout=json.dumps(entries), stderr="")
        with mock.patch.object(doctor.subprocess, "run", return_value=listing):
            _, out = run_doctor(["--data-dir", self.tmp.name, "--json"])
        return next(r for r in json.loads(out) if r["check"] == "companions")["detail"]

    def test_disabled_plugin_is_reported_like_a_missing_one(self):
        detail = self._companions([{"id": "impeccable@x", "enabled": False}, {"id": "hallmark@x", "enabled": True}])
        self.assertIn("impeccable", detail)
        self.assertNotIn("missing: hallmark", detail)
        self.assertRegex(detail, r"missing[^;]*impeccable")
        self.assertNotRegex(detail, r"missing[^;]*hallmark")

    def test_companions_name_humanizer_and_no_other_voice_skill(self):
        empty = tempfile.TemporaryDirectory()
        self.addCleanup(empty.cleanup)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(empty.name)
        detail = self._companions([{"id": name + "@x", "enabled": True} for name in doctor.PLUGINS + getattr(doctor, "OPTIONAL", ())])
        self.assertEqual(detail, "missing: humanizer")

    def test_emilkowalski_skills_is_optional(self):
        self.assertIn("emilkowalski-skills", getattr(doctor, "OPTIONAL", ()))
        self.assertNotIn("emilkowalski-skills", doctor.PLUGINS)
        empty = tempfile.TemporaryDirectory()
        self.addCleanup(empty.cleanup)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(empty.name)
        skill = Path(".claude", "skills", "humanizer", "SKILL.md")
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: humanizer\n---\n", encoding="utf-8")
        entries = [{"id": name + "@x", "enabled": True} for name in doctor.PLUGINS if name != "emilkowalski-skills"]
        listing = subprocess.CompletedProcess([], 0, stdout=json.dumps(entries), stderr="")
        with mock.patch.object(doctor.subprocess, "run", return_value=listing):
            _, out = run_doctor(["--data-dir", self.tmp.name, "--json"])
        got = next(r for r in json.loads(out) if r["check"] == "companions")
        self.assertEqual(got, {"check": "companions", "status": "OK",
                               "detail": "all present; optional, not on: emilkowalski-skills"})
