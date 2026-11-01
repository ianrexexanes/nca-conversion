import contextlib
import io
import subprocess
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


if __name__ == "__main__":
    unittest.main()
