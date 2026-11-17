"""Compare two audit data folders of one page: a before and after only within one mode, one method and one set of anchors.

    compare.py BEFORE_DIR AFTER_DIR [--json]

Reads score.json (required), facts.json or else page_facts.json, speed.json and search.json from each
folder, and prints one finding per line: the score block, the speed block, the search block, then the
facts block. Where two audits did not use the same mode, the same method or the same anchors, it says
so instead of subtracting. Exit 0 when it ran; exit 2 on bad input, with nothing on stdout and
`compare: ` lines on stderr. It reads only, writes no file and makes no network request. Stdlib only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import score  # noqa: E402
import search_check  # noqa: E402

VERSION = re.compile(r"\d+\.\d+\.\d+")
STRATEGIES = ("mobile", "desktop")
MEASURES = ("performance", "lcp_s", "cls", "tbt_ms")
FIELD_MEASURES = ("lcp_s", "inp_ms", "cls")
SIDES = ("before", "after")


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def fmt(value):
    """Three decimals, then trailing zeros and a trailing point stripped."""
    text = f"{round(value, 3):.3f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def signed(before, after):
    change = round(round(after, 3) - round(before, 3), 3)
    if change == 0:
        return "+0"
    return ("+" if change > 0 else "-") + fmt(abs(change))


def _collapse(text):
    return " ".join(text.split())


def _read(folder, name, side, problems):
    """Return (found, object); a file that is there but cannot be used adds a problem."""
    path = folder / name
    if not path.exists():
        return False, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError) as exc:
        problems.append(f"compare: {side}: {name} cannot be read: {exc}")
        return True, None
    if not isinstance(data, dict):
        problems.append(f"compare: {side}: {name} is not a JSON object")
        return True, None
    return True, data


def _check_speed(data, side, problems):
    if not isinstance(data.get("source"), str) or not isinstance(data.get("results"), dict):
        problems.append(f"compare: {side}: speed.json needs a string source and an object results")


def _check_search(data, side, problems):
    placements = data.get("placements")
    ok = (
        "keyword" in data
        and (data["keyword"] is None or isinstance(data["keyword"], str))
        and isinstance(data.get("keyword_confirmed"), bool)
        and isinstance(placements, dict)
        and all(
            isinstance(placements.get(name), dict) and isinstance(placements[name].get("status"), str) and placements[name]["status"] in search_check.LABELS
            for name in search_check.PLACEMENTS
        )
    )
    if not ok:
        problems.append(f"compare: {side}: search.json needs keyword, keyword_confirmed and all six placements with a known status")


def _check_facts(data, name, side, problems):
    headings, forms, links = data.get("headings"), data.get("forms"), data.get("links")
    bad = []
    if not isinstance(headings, list):
        bad.append("headings is not a list")
    elif not all(isinstance(h, dict) and isinstance(h.get("level"), int) and not isinstance(h.get("level"), bool)
                 and isinstance(h.get("text"), str) for h in headings):
        bad.append("a headings entry has no integer level and string text")
    if not isinstance(forms, list):
        bad.append("forms is not a list")
    if "links" in data and not (isinstance(links, list) and all(isinstance(k, dict) and isinstance(k.get("text"), str) for k in links)):
        bad.append("links is not a list of objects with a string text")
    for reason in bad:
        problems.append(f"compare: {side}: {name}: {reason}")


def load_side(folder, side, problems):
    side_data = {"dir": folder, "sheet": None, "facts": None, "speed": None, "search": None}
    if not folder.is_dir():
        problems.append(f"compare: {side}: {folder} is not a folder")
        return None
    found, sheet = _read(folder, "score.json", side, problems)
    if not found:
        problems.append(f"compare: {side}: score.json is missing")
    elif sheet is not None:
        try:
            issues = score.validate(sheet)
        except RecursionError:
            issues = ["sheet: nested too deeply to check"]
        problems.extend(f"compare: {side}: score.json: {issue}" for issue in issues)
        version = sheet.get("plugin_version")
        if version is not None and not (isinstance(version, str) and VERSION.fullmatch(version)):
            problems.append(f"compare: {side}: score.json: plugin_version must look like 0.4.0")
            issues = issues + ["plugin_version"]
        if not issues:
            side_data["sheet"] = sheet
    for key, name, check in (("speed", "speed.json", _check_speed), ("search", "search.json", _check_search)):
        found, data = _read(folder, name, side, problems)
        if data is not None:
            before = len(problems)
            check(data, side, problems)
            if len(problems) == before:
                side_data[key] = data
    facts_name = "facts.json" if (folder / "facts.json").exists() else "page_facts.json"
    found, facts = _read(folder, facts_name, side, problems)
    if facts is not None:
        before = len(problems)
        _check_facts(facts, facts_name, side, problems)
        if len(problems) == before:
            side_data["facts"] = facts
    return side_data


def _anchors(sheet):
    version = sheet.get("plugin_version")
    if version is None:
        return "0.2.x"
    return "0.2.x" if tuple(int(p) for p in version.split(".")) < (0, 3, 0) else "0.3.0"


def _nested_text_reading(sheet):
    """True when the facts beside this sheet were read by 0.4.0 or later, which gives a nested element's text to every element around it.
    A sheet with no plugin_version reads as 0.2.x, as in _anchors."""
    version = sheet.get("plugin_version")
    return version is not None and tuple(int(p) for p in version.split(".")) >= (0, 4, 0)


def score_block(b, a, speed_b=None, speed_a=None):
    out = []
    changed = False
    for key in ("mode", "page_role"):
        if b[key] != a[key]:
            out.append(f"New baseline: {key} changed from {b[key]} to {a[key]}; no before and after.")
            changed = True
    if changed:
        return out
    missing = [side for side, sheet in zip(SIDES, (b, a)) if sheet.get("plugin_version") is None]
    if len(missing) == 2:
        out.append("Neither sheet has plugin_version: both read as 0.2.x.")
        out.append("Caution: 0.2.1 changed factor 10's anchors, so a change in factor 10 may come from the version, not the page.")
    elif missing:
        out.append(f"The {missing[0]} sheet has no plugin_version: read as 0.2.x.")
    same = _anchors(b) == _anchors(a)
    if not same:
        out.append("Anchors changed in 0.3.0: read these scores side by side, not as a change.")
    rb, ra = score.score_sheet(b), score.score_sheet(a)
    out.append(f"Before: {rb['line']}")
    out.append(f"After: {ra['line']}")
    if same:
        for fb, fa in zip(rb["factors"], ra["factors"]):
            head = f"Factor {fb['id']} ({fb['name']}):"
            if fb["id"] == 10 and fb["score"] is not None and fa["score"] is not None and _source(speed_b) != _source(speed_a):
                out.append(f"{head} not compared: {_label(speed_b)} against {_label(speed_a)}")
            elif fb["score"] is not None and fa["score"] is not None:
                out.append(f"{head} {fb['score']} -> {fa['score']}, {fa['score'] - fb['score']:+d}")
            elif fb["score"] is None and fa["score"] is None:
                out.append(f"Factor {fb['id']} ({fb['name']}): not scored on either side")
            else:
                out.append(f"{head} not compared: scored on one side")
    return out


def _source(data):
    return None if data is None else data["source"]


def _label(data):
    if data is None:
        return "no speed.json"
    return data["label"] if isinstance(data.get("label"), str) else data["source"]


def _measure(strategy, name):
    if name.startswith("field "):
        field = strategy.get("field") if isinstance(strategy, dict) else None
        return field.get(name[6:]) if isinstance(field, dict) else None
    return strategy.get(name) if isinstance(strategy, dict) else None


def speed_block(b, a):
    if b is None and a is None:
        return []
    if b is None or a is None or b["source"] != a["source"]:
        return [f"Speed: not compared: {_label(b)} against {_label(a)}"]
    if b["source"] == "none":
        return ["Speed: could not check on either side"]
    out = []
    for strategy in STRATEGIES:
        in_b, in_a = strategy in b["results"], strategy in a["results"]
        if not (in_b or in_a):
            continue
        if not (in_b and in_a):
            out.append(f"Speed {strategy}: not compared: measured on one side")
            continue
        for name in MEASURES + tuple(f"field {m}" for m in FIELD_MEASURES):
            vb, va = _measure(b["results"][strategy], name), _measure(a["results"][strategy], name)
            head = f"Speed {strategy} {name}:"
            if _number(vb) and _number(va):
                out.append(f"{head} {fmt(vb)} -> {fmt(va)}, {signed(vb, va)}")
            elif _number(vb) or _number(va):
                out.append(f"{head} not compared: measured on one side")
    return out


def _variants(data):
    found = data.get("variants")
    return {search_check.normalise(v) for v in found if isinstance(v, str)} if isinstance(found, list) else set()


def search_block(b, a):
    if b is None and a is None:
        return []
    if b is None or a is None:
        return ["Search: not compared: search.json on one side only"]
    if not (b["keyword_confirmed"] and a["keyword_confirmed"]) or b["keyword"] is None or a["keyword"] is None:
        return ["Search: not compared: the keyword is not confirmed"]
    if search_check.normalise(b["keyword"]) != search_check.normalise(a["keyword"]):
        return [f'Search: not compared: keyword "{b["keyword"]}" against "{a["keyword"]}"']
    if _variants(b) != _variants(a):
        return ["Search: not compared: spelling variants differ"]
    labels = search_check.LABELS
    return [f"Search {name}: {labels[b['placements'][name]['status']]} -> {labels[a['placements'][name]['status']]}"
            for name in search_check.PLACEMENTS]


def _text_or_none(value):
    if not isinstance(value, str) or not value.strip():
        return None
    return _collapse(value)


def _quoted(value):
    return "(none)" if value is None else f'"{value}"'


def _headings(facts, level):
    return [_collapse(h["text"]) for h in facts["headings"] if h["level"] == level and h["text"].strip()]


def _surplus(have, other):
    """The entries of `have` that `other` has fewer of, in `have`'s order."""
    left = {}
    for item in other:
        left[item] = left.get(item, 0) + 1
    out = []
    for item in have:
        if left.get(item, 0):
            left[item] -= 1
        else:
            out.append(item)
    return out


def _added_removed(added, removed):
    parts = []
    if added:
        parts.append("added " + ", ".join(f'"{x}"' for x in added))
    if removed:
        parts.append("removed " + ", ".join(f'"{x}"' for x in removed))
    return "; ".join(parts)


def _button_labels(facts):
    seen = []
    for link in facts["links"]:
        text = _collapse(link["text"])
        if link.get("in_footer") is not True and text and text not in seen:
            seen.append(text)
    return seen


def facts_block(b, a, sheets=None):
    if b is None and a is None:
        return []
    if b is None or a is None:
        return ["Facts: not compared: facts on one side only"]
    out = []
    changed = False
    for label, key in (("Title", "title"), ("Meta description", "meta_description")):
        vb, va = _text_or_none(b.get(key)), _text_or_none(a.get(key))
        if vb != va:
            out.append(f"{label}: {_quoted(vb)} -> {_quoted(va)}")
            changed = True
    # no subtraction across a change of method: 0.4.0 reads nested text differently, so these are not compared across it
    method = "facts from before 0.4.0 read nested text differently"
    shifted = sheets is not None and _nested_text_reading(sheets[0]) != _nested_text_reading(sheets[1])
    h1b, h1a = " | ".join(_headings(b, 1)) or None, " | ".join(_headings(a, 1)) or None
    h1_changed = h1b != h1a and not shifted
    if shifted:
        out.append(f"H1: not compared: {method}")
    elif h1_changed:
        out.append(f"H1: {_quoted(h1b)} -> {_quoted(h1a)}")
        changed = True
    h2b, h2a = _headings(b, 2), _headings(a, 2)
    if shifted:
        out.append(f"H2 list: not compared: {method}")
    elif h2b != h2a:
        added, removed = _surplus(h2a, h2b), _surplus(h2b, h2a)
        out.append("H2 list: " + (_added_removed(added, removed) if added or removed else "same headings in a new order"))
        changed = True
    buttons_changed = False
    if "links" not in b or "links" not in a:
        out.append("Button labels: not compared: facts from before 0.3.0 hold no links")
    elif shifted:
        out.append(f"Button labels: not compared: {method}")
    else:
        lb, la = _button_labels(b), _button_labels(a)
        if set(lb) != set(la):
            out.append("Button labels: " + _added_removed(_surplus(la, lb), _surplus(lb, la)))
            changed = buttons_changed = True
    if len(b["forms"]) != len(a["forms"]):
        out.append(f"Form count: {len(b['forms'])} -> {len(a['forms'])}")
        changed = True
    if not changed:
        out.append("Facts: no change in what was compared")
    if h1_changed and buttons_changed:
        out.append("The result cannot be put down to either change.")
    return out


def compare(b, a):
    lines = score_block(b["sheet"], a["sheet"], b["speed"], a["speed"])
    lines += speed_block(b["speed"], a["speed"])
    lines += search_block(b["search"], a["search"])
    lines += facts_block(b["facts"], a["facts"], (b["sheet"], a["sheet"]))
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compare two audit data folders of one page.")
    parser.add_argument("before", metavar="BEFORE_DIR", help="the older audit's data folder")
    parser.add_argument("after", metavar="AFTER_DIR", help="the later audit's data folder")
    parser.add_argument("--json", action="store_true", help="print one JSON object with before, after and lines")
    args = parser.parse_args(argv)
    problems = []
    folders = [Path(args.before), Path(args.after)]
    if all(f.is_dir() for f in folders) and folders[0].resolve() == folders[1].resolve():
        problems.append("compare: both paths are the same folder")
    loaded = [load_side(f, side, problems) for f, side in zip(folders, SIDES)]
    if problems or any(s is None or s["sheet"] is None for s in loaded):
        for line in problems:
            print(line, file=sys.stderr)
        return 2
    lines = compare(*loaded)
    if args.json:
        print(json.dumps({"before": args.before, "after": args.after, "lines": lines}, ensure_ascii=False, indent=2))
    else:
        for line in lines:
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
