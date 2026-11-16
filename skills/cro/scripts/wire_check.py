#!/usr/bin/env python3
"""Wireframe check: an HTML wireframe frame, checked against its copy deck. Python 3 stdlib only."""
import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deck_check import SECTIONS, hero_key, parse_deck  # noqa: E402

LAYOUT_FAMILIES = ("split-media", "stacked", "cards", "logo-strip", "testimonial-wall", "steps", "comparison", "accordion",
                   "form-split", "cta-band")
# The families each deck section may use. The table `## Layout families by section` in
# skills/design-handoff/references/section-to-component.md says the same, and test_repo.py checks the two agree.
LAYOUT_RULES = {
    "header": ("stacked", "cta-band"),
    "hero": ("split-media", "stacked", "form-split"),
    "pain": ("stacked", "split-media", "cards"),
    "proof": ("testimonial-wall", "logo-strip", "cards"),
    "value": ("cards", "split-media", "stacked"),
    "compare": ("comparison", "stacked"),
    "how": ("steps", "split-media"),
    "team": ("cards", "split-media"),
    "guarantee": ("stacked", "split-media"),
    "faq": ("accordion", "stacked"),
    "closer": ("cta-band", "form-split"),
}
NOTES_LINE = re.compile(r"^\s*-\s*([^:\n]+?)\s*:\s*([\w-]+)")
NO_VISUAL = ("header", "faq")  # the sections that need no data-visual
BUTTON_TAGS = ("a", "button")
VOID = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"})
HIDDEN = frozenset({"script", "style", "template", "noscript", "head", "title"})  # their text is never visible


class BadInput(Exception):
    pass


def squash(text):
    return " ".join(text.split())


def differs(shown, wanted):
    """Both texts around the first character where they part, for a PARITY line."""
    at = next((i for i, (a, b) in enumerate(zip(shown, wanted)) if a != b), min(len(shown), len(wanted)))
    start = max(0, at - 20)
    cut = lambda text: ("..." if start else "") + text[start:at + 30] + ("..." if len(text) > at + 30 else "")  # noqa: E731
    return "%r, the deck says %r" % (cut(shown), cut(wanted))


class Frame(HTMLParser):
    """The parts of a wireframe the checks read: <main>, sections, keyed elements, visuals, loose text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.main = None
        self.sections = []  # one dict per data-section element, in document order
        self.keyed = []  # (key, tag, text) per data-key element
        self.visuals = []  # (visual key, text, owning section dict or None) per data-visual element
        self.loose = []  # (section dict, text) for visible text inside a section and outside every key and visual
        self.order = []  # the data-key values in the order their elements open
        self.notes = None  # the comments after the last </main>, one string each; None while no </main> has closed
        self.stack = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "main" and self.main is None:
            self.main = attrs
        if tag == "br":
            self.handle_data(" ")
        if "data-key" in attrs:
            self.order.append(attrs["data-key"])
        if tag in VOID:
            if "data-key" in attrs:
                self.keyed.append((attrs["data-key"], tag, ""))
            if "data-visual" in attrs:
                self.seal({"key": None, "visual": attrs["data-visual"], "text": []})
            return
        entry = {"tag": tag, "key": attrs.get("data-key"), "visual": attrs.get("data-visual"), "text": []}
        if "data-section" in attrs:
            entry["section"] = {"name": attrs["data-section"], "layout": attrs.get("data-layout"), "visuals": 0}
            self.sections.append(entry["section"])
        self.stack.append(entry)

    def handle_comment(self, data):
        if self.notes is not None:
            self.notes.append(data)

    def handle_endtag(self, tag):
        if tag == "main":
            self.notes = []  # only the comments after the last </main> are the notes block
        for at in range(len(self.stack) - 1, -1, -1):
            if self.stack[at]["tag"] == tag:
                while len(self.stack) > at:
                    self.seal(self.stack.pop())
                return

    def seal(self, entry):
        text = squash("".join(entry["text"]))
        if entry["key"] is not None:
            self.keyed.append((entry["key"], entry["tag"], text))
        if entry["visual"] is not None:
            owner = self.owner()
            if owner is not None:
                owner["visuals"] += 1
            self.visuals.append((entry["visual"], text, owner))

    def owner(self):
        return next((e["section"] for e in reversed(self.stack) if "section" in e), None)

    def handle_data(self, data):
        if any(e["tag"] in HIDDEN for e in self.stack):
            return
        covered = False
        for entry in self.stack:
            if entry["key"] is not None or entry["visual"] is not None:
                entry["text"].append(data)
                covered = True
        owner = self.owner()
        if owner is not None and not covered and data.strip():
            self.loose.append((owner, squash(data)))

    def finish(self):
        while self.stack:  # elements the markup never closed
            self.seal(self.stack.pop())


def parse_frame(text):
    frame = Frame()
    frame.feed(text)
    frame.close()
    frame.finish()
    return frame


def frame_variant(deck, ns, asked, main):
    """The variant the frame is for; BadInput when --variant and <main data-variant> do not settle on one of the deck's."""
    variants = deck.variants(ns)
    shown = main.get("data-variant", "")
    if asked is None:
        if len(variants) != 1:
            raise BadInput("the deck has variants %s; name the frame's with --variant" % ", ".join(variants))
        asked = variants[0]
    elif asked not in variants:
        raise BadInput("%r is not a variant of the deck (it has %s)" % (asked, ", ".join(repr(v) for v in variants)))
    if asked != shown:
        raise BadInput("--variant %r differs from <main data-variant=%r>" % (asked, shown))
    return asked


def rendered(deck, ns, v):
    """What the frame must show for variant v, in deck order: (key, kind, text).

    kind is "text", "button" (an <a> or <button> showing the frame's label) or "label" (the label's own key, where an
    element is optional). Page, meta, other variants' keys and visuals are left out: a visual is read from its section."""
    label = deck.label(ns, v)
    rows = []
    for key in deck.order:
        parts = key.split(".")
        if parts[0] != ns or key in deck.foreign or len(parts) < 3 or parts[1] in ("page", "meta") or parts[-1] == "visual":
            continue
        value = deck.values[key]
        if parts[1] == "cta":
            if key == ns + ".cta.button" or key == "%s.cta.hook.%s" % (ns, v):
                rows.append((key, "label", label if label is not None else value))
            elif parts[2] != "hook":
                rows.append((key, "text", value))
        elif parts[1] == "hero":
            own = len(parts) > 3 and re.fullmatch("[a-z]", parts[2])
            slot = ".".join(parts[3:] if own else parts[2:])
            if own and parts[2] != v or not own and v and hero_key(ns, v, slot) in deck.values:
                continue  # another variant's slot, or the shared one this variant's own replaces
            rows.append((key, "button" if slot == "cta" else "text", label if slot == "cta" and label is not None else value))
        elif len(parts) == 3 and parts[2] == "cta" and parts[1] in SECTIONS:
            rows.append((key, "button", label if label is not None else value))
        else:
            rows.append((key, "text", value))
    return rows


def visual_key(deck, ns, section, v):
    if section == "hero" and v and hero_key(ns, v, "visual") in deck.values:
        return hero_key(ns, v, "visual")
    return "%s.%s.visual" % (ns, section)


def notes_families(frame):
    """{section name: family} from the notes lines `- <section>: <family>, because ...` in the comments after </main>. <section>
    is a section's data-section value or the part after its first dot; a line that names no section of the frame is no note."""
    names = {}
    for section in frame.sections:
        name = section["name"]
        names[name] = names[name.split(".", 1)[-1]] = name
    families = {}
    for comment in frame.notes or []:
        for line in comment.splitlines():
            found = NOTES_LINE.match(line)
            if found and found.group(1) in names:
                families.setdefault(names[found.group(1)], found.group(2))
    return families


def check_notes(frame, add):
    if not frame.notes:
        add("WARN", "main", "NOTES", "no comment after </main>")
        return
    families = notes_families(frame)
    for section in frame.sections:
        name = section["name"]
        if name not in families:
            add("WARN", name, "NOTES", "no notes line for this section")
        elif section["layout"] and families[name] != section["layout"]:
            add("FAIL", name, "NOTES", "notes say %s, the frame says %s" % (families[name], section["layout"]))


def check(deck, frame, ns, v):
    out = []

    def add(level, key, rule, detail):
        row = (level, key, rule, detail)
        if row not in out:
            out.append(row)

    for section in frame.sections:
        name = section["name"]
        short = name.rsplit(".", 1)[-1]
        layout = section["layout"]
        if not layout:
            add("FAIL", name, "LAYOUT", "no data-layout")
        elif layout not in LAYOUT_FAMILIES:
            add("FAIL", name, "LAYOUT", "%r is not one of %s" % (layout, ", ".join(LAYOUT_FAMILIES)))
        elif short not in LAYOUT_RULES:
            add("FAIL", name, "LAYOUT", "no layout row for the section %r" % short)
        elif layout not in LAYOUT_RULES[short]:
            add("FAIL", name, "LAYOUT", "%r is not for the %s section; it may use %s" % (layout, short, ", ".join(LAYOUT_RULES[short])))
        want = visual_key(deck, ns, short, v)
        plain = re.match(r"none\b", deck.values.get(want, ""), re.I)  # the deck's visual is `none, <reason>`: no figure
        if short not in NO_VISUAL and not plain and not section["visuals"]:
            add("FAIL", name, "VISUAL", "the section has no data-visual")
        for key, text, owner in frame.visuals:
            if owner is not section:
                continue
            if key != want:
                add("FAIL", name, "VISUAL", "the figure names %s; this frame's visual is %s" % (key, want))
            elif text and key in deck.values and text != squash(deck.values[key]):
                add("FAIL", key, "PARITY", differs(text, squash(deck.values[key])))
    check_notes(frame, add)
    for key, kind, text in rendered(deck, ns, v):
        found = [(tag, shown) for k, tag, shown in frame.keyed if k == key]
        if not found:
            if kind != "label":
                add("FAIL", key, "MISSING_KEY", "no element carries this key")
            continue
        for tag, shown in found:
            if kind != "text" and tag not in BUTTON_TAGS:
                add("FAIL", key, "BUTTON", "a <%s>; a button is an <a> or a <button>" % tag)
            if shown != squash(text):
                add("FAIL", key, "PARITY", differs(shown, squash(text)))
    shown = {key for key, _, _ in rendered(deck, ns, v)}
    for key in dict.fromkeys(k for k, _, _ in frame.keyed):
        parts = key.split(".")
        if key not in deck.values:
            add("FAIL", key, "NOT_IN_DECK", "no key of this name in the deck: copy the deck never approved")
        elif key not in shown and parts[0] == ns and len(parts) > 2 and parts[1] not in ("page", "meta") and parts[-1] != "visual":
            add("WARN", key, "FOREIGN_KEY", "this key is another variant's, or the shared slot this variant replaces")
    top, h1 = (hero_key(ns, v, slot) if hero_key(ns, v, slot) in deck.values else "%s.hero.%s" % (ns, slot) for slot in ("prooftop", "h1"))
    mode = deck.values.get(ns + ".page.mode", "")
    if top in deck.values and top in frame.order and h1 in frame.order and mode in ("direct", "search"):
        before = frame.order.index(top) < frame.order.index(h1)
        if before != (mode == "direct"):
            add("WARN", top, "PROOFTOP_POSITION", "on a %s page prooftop comes %s the H1" % (mode, "before" if mode == "direct" else "after"))
    for section, text in frame.loose:
        add("WARN", section["name"], "EXTRA_TEXT", "text outside every key: %s" % text[:60])
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check an HTML wireframe frame against its copy deck.")
    parser.add_argument("wireframe", metavar="WIREFRAME.html")
    parser.add_argument("--deck", required=True, metavar="DECK.md")
    parser.add_argument("--variant")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        texts = []
        for path in (args.wireframe, args.deck):
            try:
                texts.append(Path(path).read_text(encoding="utf-8"))
            except OSError:
                raise BadInput("cannot read %s" % path)
            except UnicodeDecodeError:
                raise BadInput("%s is not UTF-8 text" % path)
        frame, deck = parse_frame(texts[0]), parse_deck(texts[1])
        if frame.main is None:
            raise BadInput("%s has no <main> element" % args.wireframe)
        ns = frame.main.get("data-ns")
        if ns not in deck.namespaces:
            raise BadInput("<main data-ns=%r> is not a namespace of the deck (it has %s)" % (ns, ", ".join(deck.namespaces) or "none"))
        rows = check(deck, frame, ns, frame_variant(deck, ns, args.variant, frame.main))
    except BadInput as error:
        print("wire_check: %s" % error, file=sys.stderr)
        return 2
    fails = sum(1 for r in rows if r[0] == "FAIL")
    warns = len(rows) - fails
    if args.json:
        print(json.dumps({"findings": [dict(zip(("level", "key", "rule", "detail"), r)) for r in rows],
                          "fail": fails, "warn": warns}, ensure_ascii=False))
    else:
        for level, key, rule, detail in rows:
            print("%s %s %s: %s" % (level, key, rule, detail))
        print("wire_check: %d FAIL, %d WARN" % (fails, warns))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
