#!/usr/bin/env python3
"""Guard: every SKILL.md carries only the six frontmatter keys the Agent Skills spec allows.

Outside Claude Code (claude.ai uploads, the Skills API, package_skill.py) any other
key is a hard failure, not a silent ignore. This catches it at commit time instead.
"""
import os
import re
import sys

ALLOWED_KEYS = {"allowed-tools", "compatibility", "description", "license", "metadata", "name"}

_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.S)
_TOP_LEVEL_KEY = re.compile(r"^([A-Za-z0-9_-]+):")


def check_frontmatter(text):
    """Return the disallowed top-level keys, in file order. Empty list means valid.

    Fails CLOSED. A column-0 line this cannot read as a plain `key:` — a quoted key,
    a flow mapping — is reported as an offender rather than skipped. A guard that
    silently passes what it cannot parse is worse than no guard: it converts an
    upload failure you would have seen into one you find out about from a user.
    """
    match = _FRONTMATTER.match(text)
    if match is None:
        return ["<no frontmatter>"]
    offenders = []
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line[:1].isspace() or stripped.startswith("- "):
            continue                       # nested under a key, not top level
        key_match = _TOP_LEVEL_KEY.match(line)
        if key_match is None:
            offenders.append("<unreadable: %s>" % stripped[:40])
            continue
        key = key_match.group(1)
        if key not in ALLOWED_KEYS:
            offenders.append(key)
    return offenders


def main(root):
    failures = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        if "SKILL.md" not in filenames:
            continue
        path = os.path.join(dirpath, "SKILL.md")
        with open(path, encoding="utf-8") as handle:
            offenders = check_frontmatter(handle.read())
        if offenders:
            failures += 1
            print("FAIL %s: disallowed frontmatter key(s): %s"
                  % (os.path.relpath(path, root), ", ".join(offenders)))
    if failures:
        print("\n%d SKILL.md file(s) outside the six-key spec. Allowed: %s"
              % (failures, ", ".join(sorted(ALLOWED_KEYS))))
        return 1
    print("OK: every SKILL.md is within the six-key spec.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
