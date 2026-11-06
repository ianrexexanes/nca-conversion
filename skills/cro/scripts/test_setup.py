import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import cro_runtime
import setup


def _fail_on(step_marker):
    def run(command, *args, **kwargs):
        if step_marker(command):
            raise subprocess.CalledProcessError(1, command)
        return subprocess.CompletedProcess(command, 0, "", "")
    return run


class SetupFailureTest(unittest.TestCase):
    def _run(self, fails, py_exists, version, chrome_launches):
        with tempfile.TemporaryDirectory() as tmp:
            out, err = io.StringIO(), io.StringIO()
            with mock.patch.object(setup.subprocess, "run", side_effect=_fail_on(fails)), \
                    mock.patch.object(setup, "installed_version", return_value=version), \
                    mock.patch.object(setup, "launches", return_value=chrome_launches), \
                    mock.patch.object(Path, "exists", return_value=py_exists), \
                    contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = setup.main(["--data-dir", tmp])
            return code, out.getvalue() + err.getvalue()

    def test_a_failed_venv_step_prints_one_line_and_returns_1(self):
        code, text = self._run(lambda c: "venv" in c and "-m" in c and c[2] == "venv", False, None, True)
        self.assertEqual(code, 1)
        self.assertEqual(len(text.strip().splitlines()), 1, text)
        self.assertIn("virtual environment", text)
        self.assertNotIn("Traceback", text)

    def test_a_failed_pip_step_prints_one_line_and_returns_1(self):
        code, text = self._run(lambda c: "pip" in c, True, "0.0.0", True)
        self.assertEqual(code, 1)
        self.assertEqual(len(text.strip().splitlines()), 1, text)
        self.assertIn("Playwright install", text)
        self.assertNotIn("Traceback", text)

    def test_a_failed_fallback_install_names_the_step(self):
        code, text = self._run(lambda c: "playwright" in c and "install" in c and "chromium" in c,
                               True, cro_runtime.PLAYWRIGHT_VERSION, False)
        self.assertEqual(code, 1)
        self.assertIn("Chromium download", text)
        self.assertNotIn("Traceback", text)

    def test_uncreatable_data_folder_is_one_line_and_exit_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            blocker = Path(tmp) / "a-file"
            blocker.write_text("not a folder\n", encoding="utf-8")
            done = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "setup.py"),
                                   "--data-dir", str(blocker)], capture_output=True, text=True)
        self.assertEqual(done.returncode, 1)
        lines = done.stderr.strip().splitlines()
        self.assertEqual(len(lines), 1, done.stderr)
        self.assertTrue(lines[0].startswith("setup: cannot create the data folder"), lines[0])
        self.assertNotIn("Traceback", done.stdout + done.stderr)


SCRIPTS = Path(__file__).resolve().parent
REAL_SKILL_MD = SCRIPTS.parent / "SKILL.md"


def run_setup(args):
    return subprocess.run([sys.executable, str(SCRIPTS / "setup.py"), *args], capture_output=True, text=True)


def allowed_tools_entries():
    for line in REAL_SKILL_MD.read_text(encoding="utf-8").splitlines():
        if line.startswith("allowed-tools:"):
            return re.findall(r"Bash\([^)]*\)", line)
    raise AssertionError("no allowed-tools line in SKILL.md")


class PermissionsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.root = self.tmp / "plugins" / "cache" / "nca-conversion" / "nca-conversion" / "0.3.0"
        (self.root / "skills" / "cro").mkdir(parents=True)
        shutil.copy(REAL_SKILL_MD, self.root / "skills" / "cro" / "SKILL.md")

    def test_root_pattern_keeps_the_version_folder_in_a_plugin_cache(self):
        p = Path("/home/u/.claude/plugins/cache/nca-conversion/nca-conversion/0.3.0")
        self.assertEqual(setup.root_pattern(p), "/home/u/.claude/plugins/cache/nca-conversion/nca-conversion/0.3.0")

    def test_root_pattern_keeps_any_other_path(self):
        self.assertEqual(setup.root_pattern(Path("/work/nca-conversion")), "/work/nca-conversion")

    def test_rules_cover_every_allowed_tools_entry(self):
        entries = allowed_tools_entries()
        rules = setup.permission_rules(self.root, Path("/d"))
        self.assertGreater(len(entries), 0)
        self.assertEqual(len(rules), len(entries))
        for rule, entry in zip(rules, entries):
            self.assertTrue(rule.startswith("Bash("), rule)
            self.assertTrue(rule.endswith(" *)"), rule)
            self.assertNotIn("${", rule)
            self.assertIn(str(self.root), rule)
            self.assertTrue(rule.endswith(entry.rsplit("/", 1)[1]), (rule, entry))

    def test_permissions_flag_prints_json_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            done = run_setup(["--permissions", "--data-dir", str(Path(tmp) / "data")])
            self.assertEqual(done.returncode, 0, done.stderr)
            out = done.stdout
            for text in ('"allow"', "Merge these rules into the permissions.allow list",
                         "keeping the rules already there", "setup writes no settings file",
                         "again after each claude plugin update"):
                self.assertIn(text, out)
            body = out[:out.rindex("}") + 1]
            self.assertTrue(json.loads(body)["permissions"]["allow"])
            self.assertEqual(os.listdir(tmp), [])


if __name__ == "__main__":
    unittest.main()
