"""List the figures in skills/*/references/*.md, and check a ledger accounts for each one."""
import glob
import os
import re
import sys

_NUMBER_WORD = (r"(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen"
                r"|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy"
                r"|eighty|ninety|hundred)")
_WORDS = _NUMBER_WORD + r"(?:[ -]" + _NUMBER_WORD + r")?"
_NUMBER = r"(?:\d+(?:\.\d+)?|" + _WORDS + r")"

PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in (
    # The plan's five.
    r"\d+(\.\d+)?\s?%",
    r"\b\d+(\.\d+)?x\b",
    r"\d+(\.\d+)?\s?times\b",
    r"\b\d+ out of \d+\b",
    r"\d+(\.\d+)?\s?(seconds?|secs?|ms|milliseconds?)\b",
    # R117: the same kinds of figure in the forms the five miss.
    r"\b\d+(\.\d+)?\s?s\b",
    r"\b" + _NUMBER + r"\s?(percent|per cent)\b",
    r"\b\d+(st|nd|rd|th)\s+percentile\b",
    r"\b" + _WORDS + r"\s+times\b",
    r"\b(twice|double[sd]?|triple[sd]?|quadruple[sd]?)\b",
    r"\b(\d+(\.\d+)?|" + _NUMBER_WORD + r")[ -]?fold\b",
    r"\borders? of magnitude\b",
    r"\b(\d+|" + _WORDS + r")\s+(in|out of)\s+(every\s+)?(\d+|" + _WORDS + r")\b",
    r"\b(a|one|two|three)[\s-]+(thirds?|quarters?|fifths?|tenths?)\b(?![ -]part)",
    r"\bhalf(?=\s+(of|the|a|an|as)\b)",
    r"\b" + _WORDS + r"[ -](seconds?|milliseconds?)\b",
    r"\b" + _NUMBER + r"(\s|-)?(minutes?|hours?|days?|weeks?|months?|years?)\b",
    r"\b(thousand|million|billion)\b",
    r"\b\d{1,3}(,\d{3})+\b",
    r"([$£€]|\b(CHF|EUR|USD|GBP)\s?)\d+([.,]\d+)*(\s?(k|m|bn|million|billion)\b)?",
    r"\b\d+(,\d{3})*(\.\d+)?\s+(visitors?|users?|sessions?|people|customers?|buyers?|leads?|clicks?"
    r"|conversions?|companies|households|respondents?|participants?|readers?|shoppers?|visits?"
    r"|page ?views?|sign-?ups?)\b",
)]


def split_row(line):
    cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line.strip())]
    return cells[1:-1] if line.strip().endswith("|") else cells[1:]


def find_rows(root):
    rows = []
    for path in sorted(glob.glob(os.path.join(root, "*", "references", "*.md"))):
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        for number, raw in enumerate(text.split("\n"), 1):
            line = raw.strip()
            hits = []
            for pattern in PATTERNS:
                for m in pattern.finditer(line):
                    hits.append((m.start(), -(m.end() - m.start()), m.end(), m.group(0)))
            hits.sort()
            kept_end = -1
            for start, _neg, end, figure in hits:
                if start < kept_end:
                    continue
                kept_end = end
                rows.append((path, number, figure, line))
    return rows


def read_ledger(path):
    accounted = set()
    with open(path, encoding="utf-8") as handle:
        for raw in handle:
            if not raw.startswith("|"):
                continue
            cells = split_row(raw)
            if len(cells) != 5 or cells[0] == "path" or all(set(c) <= set("-: ") for c in cells):
                continue
            accounted.add((cells[0], cells[1]))
    return accounted


def main(argv):
    args = argv[1:]
    ledger = None
    try:
        if "--ledger" in args:
            i = args.index("--ledger")
            if i + 1 >= len(args):
                raise ValueError("--ledger needs a file")
            ledger = args[i + 1]
            del args[i:i + 2]
        if len(args) != 1:
            raise ValueError("usage: find_figures.py ROOT [--ledger FILE]")
        root = args[0]
        if not os.path.isdir(root):
            raise OSError("not a folder: " + root)
        rows = find_rows(root)
        accounted = read_ledger(ledger) if ledger else set()
    except (OSError, ValueError) as err:
        print("find_figures: " + str(err), file=sys.stderr)
        return 2
    texts = ["%s:%d: %s | %s" % r for r in rows]
    for t in texts:
        print(t)
    if ledger is None:
        return 0
    bad = [t for r, t in zip(rows, texts) if (r[0], r[3]) not in accounted]
    for t in bad:
        print("unaccounted: " + t)
    print("find_figures: %d figures, %d unaccounted" % (len(rows), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
