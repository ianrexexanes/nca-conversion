#!/usr/bin/env python3
"""Search check: is a page's researched keyword in the six places that matter? Python 3 stdlib only.

    search_check.py TARGET [--keyword KW] [--variant V]... [--url URL] [--out FILE] [--json]

TARGET is a URL (fetched with page_facts.fetch) or a saved HTML file; --url gives a file's address.
The check sits outside the 100-point score and never fails a page: a missed placement is a finding,
and a heading count is only a count. Matching is by whole words after normalise(): case folded,
dashes, hyphens, underscores, slashes and guillemets read as spaces, no stemming. A plural or a
closed form counts only when it is named with --variant.
Without --keyword nothing is checked; the result carries the apparent target instead.
Exit 0 whenever the page was read, 2 on bad arguments, 3 when it could not be fetched or read.
"""
import argparse
import datetime
import http.client
import json
import re
import sys
import urllib.parse
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "conversion-page-audit" / "scripts"))
from page_facts import VOID, extract_facts, fetch  # noqa: E402

PLACEMENTS = ("title", "meta_description", "url_slug", "h1", "first_sentence", "h2")
SKIP = {"script", "style", "noscript", "template", "svg", "title"}
VISIBLE_SKIP = SKIP | {"nav", "footer"}
HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
STOP_WORDS = {
    "the", "a", "an", "and", "or", "of", "in", "on", "at", "to", "for", "with", "by", "from", "is", "are",
    "that", "you", "your", "we", "our",
    "der", "die", "das", "und", "oder", "im", "für", "mit", "von", "zu", "ein", "eine", "ihr", "wir",
}
SPACE_MARKS = dict.fromkeys(map(ord, "-\u2010\u2011\u2012–—_/«»‹›"), " ")
DROP_MARKS = dict.fromkeys(map(ord, "\u00ad\u200b\u200c\u200d\u2060\ufeff"), None)
LANGUAGE_HOME = re.compile(r"/[a-z]{2}(-[a-z]{2})?/?", re.I)
SENTENCE_END = re.compile(r"[.!?](?=\s|$)")


def normalise(text: str) -> str:
    text = text.casefold().translate(SPACE_MARKS).translate(DROP_MARKS)
    return " ".join(text.split())


def _pattern(terms):
    cleaned = sorted({normalise(t) for t in terms if normalise(t)}, key=lambda t: (-len(t), t))
    if not cleaned:
        return None
    return re.compile(r"(?<!\w)(?:" + "|".join(re.escape(t) for t in cleaned) + r")(?!\w)")


def matches(text: str, terms: list) -> bool:
    pattern = _pattern(terms)
    return bool(pattern and pattern.search(normalise(text)))


class _Text(HTMLParser):
    """Visible text nodes, in order, plus the text that follows the first h1."""

    def __init__(self, skip):
        super().__init__(convert_charrefs=True)
        self.skip = skip
        self.stack = []
        self.nodes = []
        self.h1_index = None
        self.h1_state = "none"  # none, inside, after, done
        self.after = []

    def handle_starttag(self, tag, attrs):
        if self.h1_state == "after" and tag in HEADINGS:
            self.h1_state = "done"
        if tag in VOID:
            return
        if tag == "h1" and self.h1_state == "none":
            self.h1_state = "inside"
            self.h1_index = len(self.stack)
        self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        if self.h1_state == "after" and tag in HEADINGS:
            self.h1_state = "done"

    def handle_endtag(self, tag):
        if tag not in self.stack:
            return
        index = len(self.stack) - 1 - self.stack[::-1].index(tag)
        del self.stack[index:]
        if self.h1_state == "inside" and index <= self.h1_index:
            self.h1_state = "after"

    def handle_data(self, data):
        if any(tag in self.skip for tag in self.stack):
            return
        self.nodes.append(data)
        if self.h1_state == "after":
            self.after.append(data)


def _parse(html, skip):
    parser = _Text(skip)
    parser.feed(html)
    parser.close()
    return parser


def visible_text(html: str) -> str:
    return " ".join(" ".join(_parse(html, VISIBLE_SKIP).nodes).split())


def first_sentence_after_h1(html: str):
    text = " ".join(" ".join(_parse(html, SKIP).after).split())
    if not text:
        return None
    end = SENTENCE_END.search(text)
    return text[:end.end()] if end else text


def _line(text):
    text = " ".join(text.split()) if isinstance(text, str) else ""
    return text or None


def _count(pattern, text):
    return len(pattern.findall(text)) if pattern else 0


def _apparent_target(facts):
    title = _line(facts.get("title"))
    h1 = next((_line(h["text"]) for h in facts.get("headings", [])
               if h["level"] == 1 and not h["in_footer"]), None)
    if not title or not h1:
        return None
    h1_tokens = set(re.findall(r"\w+", normalise(h1)))
    shared = []
    for token in re.findall(r"\w+", normalise(title)):
        if token in h1_tokens and token not in STOP_WORDS and token not in shared:
            shared.append(token)
    return " ".join(shared) or None


def check(facts: dict, html: str, url: str, keyword, variants: list) -> dict:
    has_keyword = bool(keyword and normalise(keyword))
    terms = ([keyword] if has_keyword else []) + (list(variants) if has_keyword else [])
    headings = [h for h in facts.get("headings", []) if not h["in_footer"]]
    notes = []

    def place(text, hit=None):
        if not has_keyword:
            return {"status": "not_checked", "text": text}
        if text is None:
            return {"status": "missing", "text": None}
        return {"status": "found" if hit else "missing", "text": text}

    title = _line(facts.get("title"))
    meta = _line(facts.get("meta_description"))
    h1 = next((_line(h["text"]) for h in headings if h["level"] == 1), None)
    sentence = first_sentence_after_h1(html)
    h2_texts = [t for t in (_line(h["text"]) for h in headings if h["level"] == 2) if t]
    h2_hits = [t for t in h2_texts if has_keyword and matches(t, terms)]

    path = urllib.parse.urlsplit(url).path if url else ""
    if not url:
        slug = {"status": "not_checked", "text": None}
        notes.append("No address was given (--url), so the URL placement was not checked.")
    elif not has_keyword:
        slug = {"status": "not_checked", "text": path or None}
    elif path.strip("/") == "" or LANGUAGE_HOME.fullmatch(path):
        slug = {"status": "not_applicable", "text": path or None}
    else:
        slug = place(path, matches(urllib.parse.unquote(path), terms))

    placements = {
        "title": place(title, title is not None and matches(title, terms)),
        "meta_description": place(meta, meta is not None and matches(meta, terms)),
        "url_slug": slug,
        "h1": place(h1, h1 is not None and matches(h1, terms)),
        "first_sentence": place(sentence, sentence is not None and matches(sentence, terms)),
        "h2": ({"status": "found", "text": " | ".join(h2_hits)} if h2_hits
               else place(h2_texts[0] if h2_texts else None, False)),
    }

    counts = {}
    for level in (2, 3, 4):
        total = exact = variant = 0
        for heading in headings:
            if heading["level"] != level:
                continue
            total += 1
            if has_keyword and matches(heading["text"], [keyword]):
                exact += 1
            elif has_keyword and matches(heading["text"], list(variants)):
                variant += 1
        counts["h%d" % level] = {"total": total, "exact": exact, "variant": variant}

    body = {"exact": 0, "variant": 0}
    if has_keyword:
        text = normalise(visible_text(html))
        keyword_pattern = _pattern([keyword])
        body["exact"] = _count(keyword_pattern, text)
        rest = keyword_pattern.sub("\x00", text)
        body["variant"] = _count(_pattern(list(variants)), rest)

    target = _apparent_target(facts)
    if not has_keyword:
        if target:
            notes.insert(0, 'Keyword not confirmed: no placement was checked. Apparent target: "%s".' % target)
        else:
            notes.insert(0, "Keyword not confirmed: the title and the H1 share no topic.")

    return {
        "url": url,
        "checked_at": datetime.date.today().isoformat(),
        "keyword": keyword if has_keyword else None,
        "variants": list(variants),
        "keyword_confirmed": has_keyword,
        "apparent_target": target,
        "placements": placements,
        "headings": counts,
        "headings_scope": "above the footer" if facts.get("has_footer") else "whole page (no footer element found)",
        "body_uses": body,
        "misses": [name for name in PLACEMENTS if placements[name]["status"] == "missing"],
        "notes": notes,
    }


LABELS = {"found": "FOUND", "missing": "MISSING", "not_applicable": "N/A", "not_checked": "NOT CHECKED"}


def _lines(result):
    out = ["%s %s: %s" % (LABELS[result["placements"][n]["status"]], n, result["placements"][n]["text"] or "-")
           for n in PLACEMENTS]
    out.append("search_check: %d misses of %d placements" % (len(result["misses"]), len(PLACEMENTS)))
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="search_check.py", description="Check a page for its researched keyword.")
    parser.add_argument("target", metavar="TARGET")
    parser.add_argument("--keyword")
    parser.add_argument("--variant", action="append", default=[])
    parser.add_argument("--url")
    parser.add_argument("--out", metavar="FILE")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.url is not None and not args.url.startswith(("http://", "https://")):
        parser.error("--url must start with http:// or https://")
    if args.keyword is not None and not normalise(args.keyword):
        parser.error("--keyword is empty")
    if any(not normalise(v) for v in args.variant):
        parser.error("--variant is empty")
    if args.variant and args.keyword is None:
        parser.error("--variant needs --keyword")
    if args.out:
        try:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            parser.error("cannot create the folder for --out " + args.out)
    is_url = args.target.startswith(("http://", "https://"))
    try:
        html = fetch(args.target) if is_url else Path(args.target).read_text(encoding="utf-8")
    except (OSError, ValueError, http.client.HTTPException) as error:
        print("search_check: could not read %s: %s" % (args.target, error), file=sys.stderr)
        return 3
    url = args.url or (args.target if is_url else "")
    result = check(extract_facts(html, url), html, url, args.keyword, args.variant)
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(text if args.json else "\n".join(_lines(result)))
    if args.out:
        try:
            Path(args.out).write_text(text + "\n", encoding="utf-8")
        except OSError:
            print("search_check: cannot write --out " + args.out, file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
