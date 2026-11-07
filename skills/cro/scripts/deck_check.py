#!/usr/bin/env python3
"""Deck check: a Markdown copy deck, checked mechanically. Python 3 stdlib only."""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from search_check import matches, normalise  # noqa: E402,F401

SECTIONS = ("header", "hero", "pain", "proof", "value", "compare", "how", "team", "guarantee", "faq", "closer")
KEY_LINE = re.compile(r"^(?P<key>[a-z0-9]+(?:\.[a-z0-9]+)+): (?P<value>\S.*)$")
SECTION_HEAD = re.compile(r"^## (?P<ns>[a-z0-9]+): \S")


class Deck:
    def __init__(self):
        self.values = {}
        self.order = []
        self.headings = []
        self.errors = []
        self.namespaces = []  # the `## ns:` headings, in file order, each once
        self.foreign = set()  # keys filed under another namespace's heading (or none)
        self.register_lines = None  # lines under `## Register notes`, None without the heading

    def variants(self, ns):
        found = []
        for key in self.order:
            m = re.fullmatch(re.escape(ns) + r"\.hero\.([a-z])\.h1", key)
            if m and m.group(1) not in found:
                found.append(m.group(1))
        return found or [""]

    def slot(self, ns, v, slot):
        if v and "%s.hero.%s.%s" % (ns, v, slot) in self.values:
            return self.values["%s.hero.%s.%s" % (ns, v, slot)]
        return self.values.get("%s.hero.%s" % (ns, slot))

    def label(self, ns, v):
        if v and "%s.cta.hook.%s" % (ns, v) in self.values:
            return self.values["%s.cta.hook.%s" % (ns, v)]
        return self.values.get("%s.cta.button" % ns)


def parse_deck(text):
    deck = Deck()
    ns, in_fence, fences, notes, first = None, False, {}, False, {}
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        if not in_fence:
            if line.startswith("## "):
                deck.headings.append(line)
                notes = line.strip().casefold() == "## register notes"
                if notes and deck.register_lines is None:
                    deck.register_lines = []
                head = SECTION_HEAD.match(line)
                if head:
                    ns = head.group("ns")
                    if ns not in deck.namespaces:
                        deck.namespaces.append(ns)
            elif line.strip() == "```copy":
                if ns is None:
                    deck.errors.append(("L%d" % number, "DECK_SYNTAX", "copy fence outside a '## ns: Title' section"))
                fences[ns] = fences.get(ns, 0) + 1
                in_fence = True
            elif notes and line.strip():
                deck.register_lines.append(line.strip())
            continue
        if line.strip() == "```":
            in_fence = False
            continue
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = KEY_LINE.match(line)
        if not m:
            deck.errors.append(("L%d" % number, "DECK_SYNTAX", line[:80]))
            continue
        key, value = m.group("key"), m.group("value")
        if ns is None or key.split(".")[0] != ns:
            deck.foreign.add(key)
            if ns is not None:
                deck.errors.append((key, "KEY_NAMESPACE", "key sits under '## %s:'" % ns))
        if key in deck.values:
            deck.errors.append((key, "DUPLICATE_KEY", "first at L%d" % first[key]))
            continue
        deck.values[key] = value
        deck.order.append(key)
        first[key] = number
    if in_fence:
        deck.errors.append(("EOF", "DECK_SYNTAX", "unclosed copy fence"))
    for name, count in fences.items():
        if count > 1 and name is not None:
            deck.errors.append((name, "DECK_SYNTAX", "%d copy fences in one section" % count))
    return deck


REGISTERS = ("Conservative B2B (DACH)", "Technical / industrial", "Consumer / lifestyle", "Mission / nonprofit", "Direct-response")
LANGUAGE = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$")
META_VALUES = {
    "mode": ("search", "direct"),
    "role": ("homepage", "service", "landing"),
    "traffic": ("cold-outreach", "ads", "search", "email", "mixed"),
    "awareness": ("cold", "warm"),
}
TIME_WORDS = frozenset({"now", "today", "jetzt", "heute", "maintenant", "aujourd'hui", "ora", "oggi", "subito"})
GENERIC_LABELS = frozenset({
    # English
    "submit", "send", "contact", "contact us", "learn more", "read more", "click here", "more info", "get started",
    "let's talk", "sign up", "buy", "shop",
    # German
    "absenden", "senden", "kontakt", "kontaktieren sie uns", "mehr erfahren", "weiterlesen", "hier klicken", "loslegen",
    "starten", "anmelden", "registrieren", "kaufen", "mehr infos", "kontakt aufnehmen",
    # French
    "envoyer", "soumettre", "contact", "contactez-nous", "en savoir plus", "cliquez ici", "commencer", "parlons-en",
    "s'inscrire", "inscrivez-vous", "acheter", "achetez", "lire la suite", "plus d'infos", "nous contacter",
    # Italian
    "invia", "contatto", "contattaci", "scopri di più", "leggi di più", "clicca qui", "inizia", "parliamone",
    "iscriviti", "acquista", "compra", "maggiori informazioni", "contattateci",
})
GAP = re.compile(r"\[NEEDED:[^\]]*\]|\[[A-Z][A-Z0-9 _-]*(?::[^\]]*)?\]|NOT ESTABLISHED")
STOCK = re.compile(r"\bstock\b", re.I)
NOTE_LINE = re.compile(r"^- [^:]+: .+, because .+\.$")
NOTE_NONE = "- None: the register changed no rule."
PAGE_ONLY = ("BUTTON_GAP", "CLOSER_PARTS", "VISUAL_MISSING", "PAIN_ORDER", "HEADER_EXITS", "VALUE_BLOCKS", "FAQ_PAIRS")


def fold_label(label):
    text = label.casefold().replace("’", "'").replace("‘", "'")
    text = " ".join(text.split())
    while text and unicodedata.category(text[-1]).startswith("P"):
        text = text[:-1].rstrip()
    return text


def is_generic(label):
    folded = fold_label(label)
    words = folded.split(" ")
    candidates = [folded]
    if len(words) > 1 and words[0] in TIME_WORDS:
        candidates.append(" ".join(words[1:]))
    if len(words) > 1 and words[-1] in TIME_WORDS:
        candidates.append(" ".join(words[:-1]))
    return any(c in GENERIC_LABELS for c in candidates)


def hero_key(ns, v, slot):
    return "%s.hero.%s.%s" % (ns, v, slot) if v else "%s.hero.%s" % (ns, slot)


def check(deck, part="page", final=False):
    if part not in ("page", "hero"):
        raise ValueError("part must be page or hero")
    out = []

    def add(level, key, rule, detail):
        row = (level, key, rule, detail)
        if row not in out:
            out.append(row)

    for key, rule, detail in deck.errors:
        add("FAIL", key, rule, detail)
    if not deck.namespaces:
        add("FAIL", "-", "DECK_SYNTAX", "no '## ns: Title' section")
    for ns in deck.namespaces:
        check_namespace(deck, ns, part, final, add)
    if deck.register_lines is None:
        add("FAIL", "-", "REGISTER_NOTES", "no '## Register notes' section")
    else:
        for line in deck.register_lines:
            if not (NOTE_LINE.match(line) or line == NOTE_NONE):
                add("WARN", "-", "REGISTER_NOTES", "line fits neither form: %s" % line[:80])
    if part == "hero":
        out = [r for r in out if r[2] not in PAGE_ONLY]
    return out


def check_namespace(deck, ns, part, final, add):
    values = deck.values
    keys = [k for k in deck.order if k.split(".")[0] == ns and k not in deck.foreign]
    pagev = lambda name: values.get("%s.page.%s" % (ns, name)) if "%s.page.%s" % (ns, name) in keys else None  # noqa: E731
    mode = pagev("mode")
    role = pagev("role")
    # META
    for name, allowed in META_VALUES.items():
        v = pagev(name)
        if v is None:
            add("FAIL", "%s.page.%s" % (ns, name), "META", "missing page key %s" % name)
        elif v not in allowed:
            add("FAIL", "%s.page.%s" % (ns, name), "META", "%r is not one of %s" % (v, ", ".join(allowed)))
    v = pagev("register")
    if v is None:
        add("FAIL", ns + ".page.register", "META", "missing page key register")
    elif v not in REGISTERS:
        add("FAIL", ns + ".page.register", "META", "%r is not a register name" % v)
    v = pagev("language")
    if v is None:
        add("FAIL", ns + ".page.language", "META", "missing page key language")
    elif not LANGUAGE.match(v):
        add("FAIL", ns + ".page.language", "META", "%r is not a language code" % v)
    keyword = pagev("keyword")
    if mode == "search" and not keyword:
        add("FAIL", ns + ".page.keyword", "META", "a Search page needs a keyword")
    # sections, in the order of each one's first key
    sections = []
    for k in keys:
        parts = k.split(".")
        if len(parts) > 2 and parts[1] in SECTIONS and parts[1] not in sections:
            sections.append(parts[1])
    variants = deck.variants(ns)
    button = values.get(ns + ".cta.button")
    # ONE_ACTION
    for k in keys:
        parts = k.split(".")
        if len(parts) == 3 and parts[1] in SECTIONS and parts[2] == "cta":
            if button is not None and values[k] != button:
                add("FAIL", k, "ONE_ACTION", "%r differs from the default label %r" % (values[k], button))
        elif len(parts) == 4 and parts[1] == "hero" and parts[3] == "cta":
            want = deck.label(ns, parts[2])
            if want is not None and values[k] != want:
                add("FAIL", k, "ONE_ACTION", "%r differs from variant %s's label %r" % (values[k], parts[2], want))
        elif len(parts) == 4 and parts[1] == "cta" and parts[2] == "hook":
            if parts[3] not in variants:
                add("FAIL", k, "ONE_ACTION", "no hero variant %s carries an h1" % parts[3])
    # BUTTON_WORDS and BUTTON_GENERIC
    labels = [(ns + ".cta.button", button)]
    labels += [(k, values[k]) for k in keys if re.fullmatch(re.escape(ns) + r"\.cta\.hook\.[a-z]", k)]
    if button is None:
        add("FAIL", ns + ".cta.button", "BUTTON_WORDS", "no default button label")
    for k, label in labels:
        if label is None:
            continue
        n = len(label.split())
        if n == 1 or n >= 8:
            add("FAIL", k, "BUTTON_WORDS", "%d word(s) in %r; use two to five" % (n, label))
        elif n >= 6:
            add("WARN", k, "BUTTON_WORDS", "%d words in %r; keep it only when the outcome needs the words" % (n, label))
        if is_generic(label):
            add("FAIL", k, "BUTTON_GENERIC", "%r says nothing about what the reader gets" % label)
    if ns + ".cta.fud" not in keys:
        add("FAIL", ns + ".cta.fud", "FUD_MISSING", "no doubt reducers under the button")
    # BUTTON_GAP
    body = [s for s in sections if s != "header"]

    def has_button(s):
        if s == "hero":
            return all(deck.slot(ns, v, "cta") is not None for v in variants)
        return "%s.%s.cta" % (ns, s) in keys

    if part == "page":
        for i, s in enumerate(body):
            if has_button(s):
                continue
            if s in ("hero", "closer"):
                add("FAIL", "%s.%s" % (ns, s), "BUTTON_GAP", "%s has no button" % s)
            elif i > 0 and not has_button(body[i - 1]):
                add("FAIL", "%s.%s" % (ns, s), "BUTTON_GAP", "%s and %s in a row have no button" % (body[i - 1], s))
    # per variant hero rules
    for v in variants:
        for slot in ("prooftop", "strip"):
            if deck.slot(ns, v, slot) is None:
                add("FAIL", hero_key(ns, v, slot), "PROOF_SLOTS", "variant %s has no %s" % (v or "(default)", slot))
        h1 = deck.slot(ns, v, "h1")
        if h1 is not None:
            n = len(h1)
            if mode == "search":
                if n >= 91:
                    add("FAIL", hero_key(ns, v, "h1"), "HEADLINE_LENGTH", "%d characters; rewrite" % n)
                elif n >= 51:
                    add("WARN", hero_key(ns, v, "h1"), "HEADLINE_LENGTH", "%d characters; set smaller or split at the natural break" % n)
            elif mode == "direct" and n >= 91:
                add("WARN", hero_key(ns, v, "h1"), "HEADLINE_LENGTH", "%d characters; consider a shorter line" % n)
        benefits = {}
        pattern = r"\.hero\.(?:%s\.)?benefit(\d+)" % re.escape(v) if v else r"\.hero\.benefit(\d+)"
        for k in keys:
            m = re.fullmatch(re.escape(ns) + pattern, k)
            if m:
                benefits.setdefault(int(m.group(1)), k)
        if mode == "search" and benefits:
            add("FAIL", benefits[min(benefits)], "BENEFIT_LINES", "a Search page carries no benefit lines")
        elif mode == "direct" and len(benefits) > 5:
            add("FAIL", benefits[sorted(benefits)[5]], "BENEFIT_LINES", "%d benefit lines; five at most" % len(benefits))
    # visuals
    for k in keys:
        if k.split(".")[-1] == "visual" and STOCK.search(values[k]):
            add("WARN", k, "VISUAL_STOCK", "the visual brief says stock: %s" % values[k][:60])
    if part == "page":
        for s in body:
            if s == "faq":
                continue
            if s == "hero":
                missing = any(deck.slot(ns, v, "visual") is None for v in variants)
            else:
                missing = "%s.%s.visual" % (ns, s) not in keys
            if missing:
                add("FAIL", "%s.%s" % (ns, s), "VISUAL_MISSING", "%s has no visual" % s)
        # closer
        bullets = [k for k in keys if re.fullmatch(re.escape(ns) + r"\.closer\.bullet\d+", k)]
        lacks = [n for n in ("h2", "proof", "cta") if "%s.closer.%s" % (ns, n) not in keys]
        if not 3 <= len(bullets) <= 5:
            lacks.append("three to five bullets (has %d)" % len(bullets))
        if lacks:
            add("FAIL", ns + ".closer", "CLOSER_PARTS", "closer lacks " + ", ".join(lacks))
        # pain and proof order
        awareness = pagev("awareness")
        if "pain" in sections and "proof" in sections and awareness in ("cold", "warm"):
            pain_first = sections.index("pain") < sections.index("proof")
            if awareness == "cold" and not pain_first:
                add("FAIL", ns + ".proof", "PAIN_ORDER", "cold visitors: pain comes before proof")
            if awareness == "warm" and pain_first:
                add("FAIL", ns + ".pain", "PAIN_ORDER", "warm visitors: proof comes before pain")
        if role == "landing" and ns + ".header.nav" in keys:
            add("FAIL", ns + ".header.nav", "HEADER_EXITS", "a landing page's header carries no menu links")
        blocks = [k for k in keys if re.fullmatch(re.escape(ns) + r"\.value\.block\d+", k)]
        if not 4 <= len(blocks) <= 8:
            add("WARN", ns + ".value", "VALUE_BLOCKS", "%d value blocks; four to eight" % len(blocks))
        qs = {int(k.rsplit("q", 1)[1]) for k in keys if re.fullmatch(re.escape(ns) + r"\.faq\.q\d+", k)}
        as_ = {int(k.rsplit("a", 1)[1]) for k in keys if re.fullmatch(re.escape(ns) + r"\.faq\.a\d+", k)}
        for n in sorted(qs - as_):
            add("FAIL", "%s.faq.a%d" % (ns, n), "FAQ_PAIRS", "question %d has no answer" % n)
        for n in sorted(as_ - qs):
            add("FAIL", "%s.faq.q%d" % (ns, n), "FAQ_PAIRS", "answer %d has no question" % n)
        both = qs | as_
        if both and sorted(both) != list(range(1, max(both) + 1)):
            add("FAIL", ns + ".faq", "FAQ_PAIRS", "numbering is not 1 to %d without gaps" % max(both))
    # SEARCH_PLACEMENT
    if mode == "search" and keyword:
        terms = [keyword] + [t.strip() for t in (pagev("variants") or "").split(";") if t.strip()]
        places = [("title", ns + ".meta.title", "", None), ("description", ns + ".meta.description", "", None)]
        if role != "homepage":
            places.append(("slug", ns + ".meta.slug", "", None))
        for v in variants:
            places.append(("H1", hero_key(ns, v, "h1"), v, "h1"))
            places.append(("answer", hero_key(ns, v, "answer"), v, "answer"))
        for name, k, v, slot in places:
            if slot:
                value = deck.slot(ns, v, slot)
                if value is not None and k not in values:
                    k = "%s.hero.%s" % (ns, slot)  # read from the shared key
            else:
                value = values.get(k) if k not in deck.foreign else None
            if value is None:
                add("FAIL", k, "SEARCH_PLACEMENT", "%s is missing, so the keyword is not in it" % name)
            elif not matches(value, terms):
                add("FAIL", k, "SEARCH_PLACEMENT", "%s lacks the keyword or a named variant" % name)
        if part == "page":
            h2s = [k for k in keys if k.split(".")[-1] == "h2"]
            if not any(matches(values[k], terms) for k in h2s):
                add("FAIL", ns, "SEARCH_PLACEMENT", "no H2 carries the keyword or a named variant")
    # PLACEHOLDER
    for k in keys:
        m = GAP.search(values[k])
        if m:
            add("FAIL" if final else "WARN", k, "PLACEHOLDER", "gap left open: %s" % m.group(0))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check a Markdown copy deck.")
    parser.add_argument("deck", metavar="DECK.md")
    parser.add_argument("--part", choices=("page", "hero"), default="page")
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        with open(args.deck, encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        print("deck_check: cannot read %s" % args.deck, file=sys.stderr)
        return 2
    except UnicodeDecodeError:
        print("deck_check: %s is not UTF-8 text" % args.deck, file=sys.stderr)
        return 2
    rows = check(parse_deck(text), args.part, args.final)
    fails = sum(1 for r in rows if r[0] == "FAIL")
    warns = len(rows) - fails
    if args.json:
        print(json.dumps({"findings": [dict(zip(("level", "key", "rule", "detail"), r)) for r in rows],
                          "fail": fails, "warn": warns}, ensure_ascii=False))
    else:
        for level, key, rule, detail in rows:
            print("%s %s %s: %s" % (level, key, rule, detail))
        print("deck_check: %d FAIL, %d WARN" % (fails, warns))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
