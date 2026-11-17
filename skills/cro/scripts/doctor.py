"""Report the state of the /cro runtime. Changes nothing."""
import argparse
import json
import os
import re
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


def puppeteer_roots(script):
    """Where Hallmark's render tier looks for puppeteer-core or puppeteer, in its order: $HALLMARK_PUPPETEER, the current
    folder, the folder of its script, the parent of `npm root -g` (skipped when npm is missing or fails)."""
    roots = [Path(os.environ["HALLMARK_PUPPETEER"])] if os.environ.get("HALLMARK_PUPPETEER") else []
    roots += [Path.cwd(), script.parent]
    try:
        done = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True, timeout=30)
        if done.returncode == 0 and done.stdout.strip():
            roots.append(Path(done.stdout.strip()).parent)
    except (OSError, subprocess.SubprocessError):
        pass
    return roots


def resolves_puppeteer(roots):
    """True when puppeteer-core or puppeteer resolves from a root as Node resolves a bare name: a node_modules/<name>/package.json
    in the root or any parent folder."""
    for root in roots:
        for folder in (root, *root.parents):
            if any((folder / "node_modules" / name / "package.json").is_file() for name in ("puppeteer-core", "puppeteer")):
                return True
    return False


def version_key(script):
    """Sort key for a sloplint.mjs path: its version folder as a tuple of integers; a name that is not dotted numbers sorts below all."""
    name = script.parts[-4]
    if re.fullmatch(r"\d+(\.\d+)*", name):
        return (1, tuple(int(part) for part in name.split(".")))
    return (0, ())


def check_hallmark_lint(roots=None):
    """The sloplint.mjs of the highest Hallmark version under the home's plugin cache (its 2.0.0 layout), OK only when its render
    tier can load puppeteer. roots is the list of folders to resolve from; it defaults to puppeteer_roots(script)."""
    found = sorted(Path.home().glob(".claude/plugins/cache/*/hallmark/*/hallmark/scripts/sloplint.mjs"), key=version_key, reverse=True)
    if not found:
        return row("hallmark-lint", "WARN", "not found")
    if resolves_puppeteer(puppeteer_roots(found[0]) if roots is None else roots):
        return row("hallmark-lint", "OK", str(found[0]))
    return row("hallmark-lint", "WARN", "%s; render tier off: no puppeteer-core found" % found[0])


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

    _, token_source = cro_runtime.clarity_token()
    token_status = {"env": "OK", "file": "OK", "file-loose-permissions": "WARN"}.get(token_source, "MISSING")
    rows.append(row("clarity-token", token_status, token_source))

    has_npx = shutil.which("npx") is not None
    rows.append(row("lighthouse", "OK" if has_npx else "MISSING", "npx found" if has_npx else "npx not found"))

    rows.append(check_companions())
    rows.append(check_hallmark_lint())
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
