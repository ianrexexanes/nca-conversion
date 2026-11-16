"""Check a design's tokens against the measured design rules.

    design_check.py TOKENS.json [--json]

TOKENS.json is `_design/tokens.json`: {"colors": {"text", "background", "action", "action_text", ...},
"type": {"h1_px", "body_px"}}. Colours are #rgb or #rrggbb. Contrast is WCAG 2.2's, on the unrounded ratio
(https://www.w3.org/TR/WCAG22/, 1.4.3 and 1.4.11). Exit 1 on any FAIL, 2 on input it cannot read, else 0.
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

REQUIRED_COLORS = ("text", "background", "action", "action_text")
REQUIRED_SIZES = ("h1_px", "body_px")
TEXT_MIN, CONTROL_MIN = 4.5, 3.0
RATIO_MIN, RATIO_MAX = 3, 4
HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


class BadInput(Exception):
    pass


def normal(color: str) -> str:
    color = color.lower()
    return "#" + "".join(ch * 2 for ch in color[1:]) if len(color) == 4 else color


def luminance(color: str) -> float:
    channels = []
    for i in (1, 3, 5):
        v = int(normal(color)[i:i + 2], 16) / 255
        channels.append(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(a: str, b: str) -> float:
    """WCAG 2.2 contrast ratio of two #rgb or #rrggbb colours, unrounded, the same in either order."""
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def read_tokens(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError:
        raise BadInput("cannot read %s" % path)
    except (UnicodeDecodeError, ValueError):
        raise BadInput("%s is not JSON text" % path)
    colors = data.get("colors") if isinstance(data, dict) else None
    sizes = data.get("type") if isinstance(data, dict) else None
    if not isinstance(colors, dict) or not isinstance(sizes, dict):
        raise BadInput("%s needs a \"colors\" object and a \"type\" object" % path)
    for name in REQUIRED_COLORS:
        if name not in colors:
            raise BadInput("colors.%s is missing" % name)
    for name, value in colors.items():
        if not isinstance(value, str) or not HEX.match(value):
            raise BadInput("colors.%s is not #rgb or #rrggbb" % name)
    for name in REQUIRED_SIZES:
        value = sizes.get(name)
        if name not in sizes:
            raise BadInput("type.%s is missing" % name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise BadInput("type.%s is not a positive number" % name)
    return {k: normal(v) for k, v in colors.items()}, sizes


def check(colors, sizes):
    rows = []

    def add(level, key, rule, detail):
        rows.append((level, key, rule, detail))

    pairs = (("CONTRAST_TEXT", "text", "text", "background", TEXT_MIN, "text on the background"),
             ("CONTRAST_ACTION", "action_text", "action_text", "action", TEXT_MIN, "the button label on the button"),
             ("ACTION_VISIBLE", "action", "action", "background", CONTROL_MIN, "the button against the background"))
    for rule, key, fore, back, minimum, what in pairs:
        ratio = contrast(colors[fore], colors[back])
        if ratio < minimum:
            add("FAIL", "colors." + key, rule, "%s is %.2f:1 (%s on %s); at least %g:1 is needed"
                % (what, ratio, colors[fore], colors[back], minimum))
    for name, value in colors.items():
        if name != "action" and value == colors["action"]:
            add("WARN", "colors." + name, "ACTION_ISOLATED", "equals the action colour %s; the button should be the only thing in it" % value)
    unusable = [name for name in REQUIRED_SIZES if not math.isfinite(sizes[name])]  # JSON allows NaN and Infinity
    for name in unusable:
        add("FAIL", "type." + name, "TYPE_SIZE", "%s is not a finite number of pixels" % name)
    ratio = sizes["h1_px"] / sizes["body_px"]
    if not unusable and not RATIO_MIN <= ratio <= RATIO_MAX:
        add("WARN", "type.h1_px", "HEADLINE_RATIO", "the headline is %.2f times the body size; three to four is the rule" % ratio)
    if colors["text"] == "#000000":
        add("WARN", "colors.text", "BODY_BLACK", "body text is pure black; dark grey reads easier")
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check design tokens against the measured design rules.")
    parser.add_argument("tokens", metavar="TOKENS.json")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        rows = check(*read_tokens(args.tokens))
    except BadInput as error:
        print("design_check: %s" % error, file=sys.stderr)
        return 2
    fails = sum(1 for r in rows if r[0] == "FAIL")
    warns = len(rows) - fails
    if args.json:
        print(json.dumps({"findings": [dict(zip(("level", "key", "rule", "detail"), r)) for r in rows],
                          "fail": fails, "warn": warns}, ensure_ascii=False))
    else:
        for level, key, rule, detail in rows:
            print("%s %s %s: %s" % (level, key, rule, detail))
        print("design_check: %d FAIL, %d WARN" % (fails, warns))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
