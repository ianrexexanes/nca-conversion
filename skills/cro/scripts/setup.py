"""Prepare the /cro runtime: a venv, a pinned Playwright, and a browser that launches."""
import argparse
import shlex
import subprocess
import sys
from pathlib import Path

import cro_runtime

LAUNCH_CHROME = ("from playwright.sync_api import sync_playwright as s; p = s().start(); "
                 "b = p.chromium.launch(channel='chrome', headless=True); b.close(); p.stop()")
LAUNCH_BUNDLED = ("from playwright.sync_api import sync_playwright as s; p = s().start(); "
                  "b = p.chromium.launch(headless=True); b.close(); p.stop()")
VERSION_SCRIPT = "import importlib.metadata as m; print(m.version('playwright'))"


def plan(data_dir: Path) -> dict:
    py = str(cro_runtime.venv_python(data_dir))
    return {
        "venv": [sys.executable, "-m", "venv", str(data_dir / "venv")],
        "pip": [py, "-m", "pip", "install", f"playwright=={cro_runtime.PLAYWRIGHT_VERSION}"],
        "chrome": [py, "-c", LAUNCH_CHROME],
        "fallback_install": [py, "-m", "playwright", "install", "chromium"],
        "fallback_launch": [py, "-c", LAUNCH_BUNDLED],
    }


def installed_version(py: Path) -> str | None:
    try:
        done = subprocess.run([str(py), "-c", VERSION_SCRIPT], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def launches(command: list[str]) -> bool:
    return subprocess.run(command, capture_output=True, text=True).returncode == 0


def step(command: list[str], name: str) -> bool:
    """Run one install step. On failure print one line naming it, never the command or its environment."""
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError:
        print(f"Setup stopped: the {name} step failed. Run it again, or check your network and disk space.")
        return False
    return True


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Set up the /cro runtime.")
    parser.add_argument("--data-dir", type=Path, default=cro_runtime.default_data_dir())
    parser.add_argument("--dry-run", action="store_true", help="print the commands and run none")
    args = parser.parse_args(argv)
    data_dir = args.data_dir
    commands = plan(data_dir)

    if args.dry_run:
        for command in commands.values():
            print(shlex.join(command))
        return 0

    py = cro_runtime.venv_python(data_dir)
    if not py.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        if not step(commands["venv"], "virtual environment"):
            return 1
    if installed_version(py) != cro_runtime.PLAYWRIGHT_VERSION:
        if not step(commands["pip"], "Playwright install"):
            return 1

    if launches(commands["chrome"]):
        print("Browser: Chrome launches.")
        ok = True
    else:
        print("Chrome did not launch; installing Playwright's bundled Chromium.")
        if not step(commands["fallback_install"], "Chromium download"):
            return 1
        ok = launches(commands["fallback_launch"])
        print("Browser: bundled Chromium launches." if ok else "Browser: no browser launches.")

    print("PageSpeed key (optional): see skills/cro/references/setup.md for the steps.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
