"""Check the model's factor sheet and add up the Conversion Score.

    score.py SHEET.json [--json]

Prints the coverage line, or with --json the whole result. Exit 0 when the sheet is valid; exit 2
when it is not, with one stderr line per problem and nothing on stdout. The score is the sum of the
factors that could be checked, so a factor that was not checked lowers the coverage, not the total.
Stdlib only.
"""
import argparse
import json
import sys

FACTORS = (
    "What's in it for me?",
    "Is it for me?",
    "Does it work?",
    "What do I do next?",
    "Value and how it works",
    "Proof and trust further down the page",
    "Objections and risk",
    "The form and what happens after it",
    "Design that sells",
    "Mobile and speed, measured",
)

MODES = ("search", "direct")
PAGE_ROLES = ("homepage", "service", "landing")
TRAFFIC = ("cold-outreach", "ads", "search", "mixed", "unknown")


def _show(value):
    return json.dumps(value, default=repr)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _whole(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _own_problems(entry):
    """The problems of one factor entry, without the `factor <id>:` prefix."""
    if "score" not in entry:
        return ["score missing"]
    value = entry["score"]
    if value is None:
        return [] if _text(entry.get("not_checked")) else ["not scored but no not_checked reason"]
    problems = []
    if not _whole(value):
        problems.append(f"score {_show(value)} is not a whole number")
    elif not 0 <= value <= 10:
        problems.append(f"score {value} is outside 0 to 10")
    if not _text(entry.get("evidence")):
        problems.append("scored but no evidence")
    return problems


def validate(sheet):
    """Return the problems with a sheet, in a fixed order; an empty list means it can be scored."""
    if not isinstance(sheet, dict):
        return ["sheet: not a JSON object"]
    problems = []
    for key, allowed, label in (
        ("mode", MODES, "search or direct"),
        ("page_role", PAGE_ROLES, "homepage, service or landing"),
        ("traffic", TRAFFIC, "cold-outreach, ads, search, mixed or unknown"),
    ):
        prefix = "sheet: traffic" if key == "traffic" else f"{key}:"
        if key not in sheet:
            problems.append(f"{prefix} missing")
        elif sheet[key] not in allowed:
            problems.append(f"{prefix} {_show(sheet[key])} is not {label}")
    if "factors" not in sheet:
        problems.append("sheet: factors missing")
        return problems
    entries = sheet["factors"]
    if not isinstance(entries, list):
        problems.append("sheet: factors is not a list")
        return problems
    if len(entries) != len(FACTORS):
        problems.append(f"sheet: {len(entries)} factor entries, not {len(FACTORS)}")
    by_id = {}
    for k, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            problems.append(f"sheet: factor entry {k} is not an object")
        elif "id" not in entry:
            problems.append(f"sheet: factor entry {k} has no id")
        elif not _whole(entry["id"]) or not 1 <= entry["id"] <= len(FACTORS):
            problems.append(f"sheet: factor id {_show(entry['id'])} is not a whole number from 1 to 10")
        else:
            by_id.setdefault(entry["id"], []).append(entry)
    for factor_id in range(1, len(FACTORS) + 1):
        found = by_id.get(factor_id)
        if not found:
            problems.append(f"factor {factor_id}: missing")
            continue
        problems.extend(f"factor {factor_id}: {p}" for p in _own_problems(found[0]))
        problems.extend(f"factor {factor_id}: duplicate" for _ in found[1:])
    return problems


def _line(total, scored):
    count = len(FACTORS)
    if scored == 0:
        return f"No score: none of the {count} factors could be checked."
    if scored == count:
        return f"{total}/100, based on all {count} factors."
    if scored == 1:
        return f"{total}/100, based on the 1 factor that could be checked."
    return f"{total}/100, based on the {scored} factors that could be checked."


def score_sheet(sheet):
    """Add up a valid sheet; raise ValueError with the joined problems when it is not valid."""
    problems = validate(sheet)
    if problems:
        raise ValueError("; ".join(problems))
    entries = {entry["id"]: entry for entry in sheet["factors"]}
    factors = []
    total = scored = 0
    for factor_id, name in enumerate(FACTORS, start=1):
        entry = entries[factor_id]
        if entry["score"] is None:
            factors.append({"id": factor_id, "name": name, "score": None, "not_checked": entry["not_checked"]})
        else:
            factors.append({"id": factor_id, "name": name, "score": entry["score"], "evidence": entry["evidence"]})
            total += entry["score"]
            scored += 1
    return {"total": total, "scored": scored, "possible": 10 * scored, "line": _line(total, scored), "factors": factors}


def _fail(lines):
    for line in lines:
        print(line, file=sys.stderr)
    return 2


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check a factor sheet and add up the Conversion Score.")
    parser.add_argument("sheet", metavar="SHEET", help="path to the factor sheet (JSON)")
    parser.add_argument("--json", action="store_true", help="print the whole result instead of the coverage line")
    args = parser.parse_args(argv)
    try:
        with open(args.sheet, encoding="utf-8") as handle:
            sheet = json.load(handle)
    except OSError:
        return _fail([f"sheet: cannot read {args.sheet}"])
    except (ValueError, RecursionError):
        return _fail(["sheet: not valid JSON"])
    try:
        problems = validate(sheet)
        if problems:
            return _fail(problems)
        result = score_sheet(sheet)
        text = json.dumps(result) if args.json else result["line"]
    except RecursionError:
        return _fail(["sheet: not valid JSON"])
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
