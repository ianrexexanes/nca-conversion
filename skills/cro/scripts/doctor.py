"""Report the state of the /cro runtime. Changes nothing."""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import cro_runtime

PLUGINS = ("ui-ux-pro-max", "taste-skill", "impeccable", "hallmark", "frontend-design", "claude-seo")
OPTIONAL = ("emilkowalski-skills",)
SKILLS = ("humanizer",)
BROWSER_SCRIPT = (
    "from playwright.sync_api import sync_playwright as s\n"
    "p = s().start()\n"
    "try:\n"
    "    b = p.chromium.launch(channel='chrome', headless=True)\n"
    "    print('chrome ' + b.version.split('.')[0])\n"
    "except Exception:\n"
    "    b = p.chromium.launch(headless=True)\n"
    "    print('chromium (bundled)')\n"
    "b.close()\n"
    "p.stop()\n"
)
VERSION_SCRIPT = "import importlib.metadata as m; print(m.version('playwright'))"


def row(check, status, detail):
    return {"check": check, "status": status, "detail": detail}


def venv_script(py: Path, script: str):
    try:
        done = subprocess.run([str(py), "-c", script], capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 and done.stdout.strip() else None


def check_companions():
    try:
        done = subprocess.run(["claude", "plugin", "list", "--json"], capture_output=True, text=True, timeout=30)
        if done.returncode != 0:
            raise OSError("claude plugin list failed")
        entries = json.loads(done.stdout)
        enabled = {str(e.get("id", "")).split("@")[0] for e in entries if isinstance(e, dict) and e.get("enabled") is True}
    except (OSError, subprocess.SubprocessError, ValueError, AttributeError, TypeError):
        return row("companions", "WARN", "claude CLI not found, companions not checked")
    missing = [name for name in PLUGINS if name not in enabled]
    for name in SKILLS:
        if not Path(".claude", "skills", name, "SKILL.md").is_file():
            missing.append(name)
    optional = [name for name in OPTIONAL if name not in enabled]
    detail = ("missing: " + ", ".join(missing)) if missing else "all present"
    if optional:
        detail += "; optional, not on: " + ", ".join(optional)
    return row("companions", "WARN" if missing else "OK", detail)


def run_checks(data_dir: Path):
    rows = []
    ok_python = sys.version_info >= (3, 10)
    rows.append(row("python", "OK" if ok_python else "MISSING", sys.version.split()[0] + ("" if ok_python else " (3.10 or later needed)")))

    py = cro_runtime.venv_python(data_dir)
    has_venv = py.exists()
    rows.append(row("venv", "OK" if has_venv else "MISSING", str(data_dir / "venv") if has_venv else "run /cro setup"))

    version = venv_script(py, VERSION_SCRIPT) if has_venv else None
    rows.append(row("playwright", "OK" if version else "MISSING", version or "not installed"))

    browser = venv_script(py, BROWSER_SCRIPT) if version else None
    rows.append(row("browser", "OK" if browser else "MISSING", browser or "no browser launches"))

    _, source = cro_runtime.pagespeed_key()
    status = {"env": "OK", "file": "OK", "file-loose-permissions": "WARN"}.get(source, "MISSING")
    rows.append(row("pagespeed-key", status, source))

    has_npx = shutil.which("npx") is not None
    rows.append(row("lighthouse", "OK" if has_npx else "MISSING", "npx found" if has_npx else "npx not found"))

    rows.append(check_companions())
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check the /cro runtime.")
    parser.add_argument("--data-dir", type=Path, default=cro_runtime.default_data_dir())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    rows = run_checks(args.data_dir)
    if args.json:
        print(json.dumps(rows))
    else:
        for r in rows:
            print(f"{r['status']} {r['check']}: {r['detail']}")
    required = {r["check"]: r["status"] for r in rows}
    return 0 if all(required[c] == "OK" for c in ("python", "venv", "playwright", "browser")) else 1


if __name__ == "__main__":
    sys.exit(main())
