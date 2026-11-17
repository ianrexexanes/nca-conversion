#!/usr/bin/env python3
"""Deterministic page facts for conversion audits. Python 3 stdlib only.

Parses static markup. It cannot see what JavaScript renders, what CSS hides, or
what sits behind a consent banner — those checks belong to a rendered capture
(`render_check.py`) and their absence is reported in `notes`, never assumed fine.

LCP: this module reports *candidates*, not a measured Largest Contentful Paint.
Which element is largest and above the fold is a rendered-layout result — it
depends on CSS, viewport and load timing, none of which static markup can see.
`lcp_candidates` is just the first few images in document order, and a `notes`
entry says so. A second, narrower note flags an early `loading="lazy"` image
specifically, because that particular defect — deferring the browser's earliest
candidate behind the lazy-load trigger — IS deterministically visible in markup
even though LCP identification itself is not.

Nesting: the heading/link/button collector is one stack, but every open element on it
receives each text node, as a browser's textContent does. `<h1>See <a href="#">more</a></h1>`
reports as `{"level": 1, "text": "See more"}` and also lists the link "more"; an `<a>` that wraps
a heading carries that heading's text as its label. What remains true: the text of a nested
element counts once for each element that contains it, so a link inside a heading is in both lists,
and the collector reads markup only, not styles or scripts that change what a visitor sees.

Usage:
    python3 page_facts.py <file.html|url> [--url <original-url>] [--out FILE]

Exit codes: 0 when the facts were produced; 2 when the target cannot be read or --out cannot be
written, with one line on stderr (`page_facts: cannot read <target>: <reason>` or `cannot write`).
"""
import argparse
import codecs
import http.client
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
CTA_HINTS = ("sign up", "get started", "book", "buy", "register", "contact",
             "demo", "anmelden", "jetzt", "kontakt", "buchen")
LCP_CANDIDATE_CAP = 3
# Chrome ships a stable release every two weeks since Chrome 153:
# https://developer.chrome.com/blog/chrome-two-week-release (read 2026-11-17). The
# count does not skip the year-end breaks, so from December 2026 it runs up to two
# majors ahead of the real stable release, and further each year: move the anchor
# below at each release of this plugin.
RELEASE_CYCLE_DAYS = 14
# One stable release and its date from Chrome's schedule:
# https://chromiumdash.appspot.com/schedule (read 2026-11-17).
ANCHOR_MAJOR = 158
ANCHOR_DATE = date(2026, 11, 17)


def chrome_major(today: date | None = None) -> int:
    """The Chrome stable major expected on `today`, counted from the anchor release."""
    if today is None:
        today = date.today()
    return ANCHOR_MAJOR + max(0, (today - ANCHOR_DATE).days // RELEASE_CYCLE_DAYS)


CHROME_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/%d.0.0.0 Safari/537.36" % chrome_major()

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
NOT_PAGE_FOOTER_TAGS = frozenset({"article", "aside", "main", "nav", "section"})
NOT_PAGE_FOOTER_ROLES = frozenset({"article", "complementary", "main", "navigation", "region"})

# The meta prescan of https://html.spec.whatwg.org/multipage/parsing.html#prescan-a-byte-stream-to-determine-its-encoding
# (read 2026-11-06): comments are skipped, and each <meta> tag is read attribute by attribute.
_COMMENT = re.compile(rb"<!--.*?(?:-->|\Z)", re.DOTALL)
_META_TAG = re.compile(rb"<meta(?=[\s/])([^>]*)>?", re.IGNORECASE)
_ATTRIBUTE = re.compile(rb"""([^\s/>=][^\s/>=]*)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]*)))?""")
# https://html.spec.whatwg.org/multipage/urls-and-fetching.html#algorithm-for-extracting-a-character-encoding-from-a-meta-element
# (read 2026-11-06)
_CONTENT_CHARSET = re.compile(rb"""charset\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s;]*))""", re.IGNORECASE)


# The 17 labels of the windows-1252 encoding in the Encoding Standard; browsers decode
# them all as Windows-1252, not as Latin-1 or ASCII:
# https://encoding.spec.whatwg.org/#names-and-labels (read 2026-11-06).
_WINDOWS_1252_LABELS = frozenset({
    "ansi_x3.4-1968", "ascii", "cp1252", "cp819", "csisolatin1", "ibm819", "iso-8859-1",
    "iso-ir-100", "iso8859-1", "iso88591", "iso_8859-1", "iso_8859-1:1987", "l1", "latin1",
    "us-ascii", "windows-1252", "x-cp1252",
})


def _try_decode(raw: bytes, label: str | None, from_meta: bool) -> str | None:
    """Decode `raw` with the charset `label` names, or None when the label cannot be used."""
    if not label:
        return None
    label = label.strip().lower()
    if label in _WINDOWS_1252_LABELS:
        name = "cp1252"
    else:
        try:
            name = codecs.lookup(label).name
        except (LookupError, ValueError):  # an unknown name, or one holding a NUL
            return None
        # The Encoding Standard has no UTF-32 label, so "get an encoding" fails for one
        # (https://encoding.spec.whatwg.org/#names-and-labels). The HTML Standard takes a
        # transport-layer charset only "if the transport layer specifies a character encoding,
        # and it is supported", and its prescan says "If charset is failure, then jump to the
        # step below labeled next byte" (https://html.spec.whatwg.org/multipage/parsing.html).
        # A UTF-32 label, from the header or a meta, is passed over like any unusable label.
        if name.startswith("utf-32"):
            return None
        # The HTML prescan reads a meta-declared UTF-16 as UTF-8:
        # https://html.spec.whatwg.org/multipage/parsing.html#prescan-a-byte-stream-to-determine-its-encoding
        # ("If charset is UTF-16BE/LE, then set charset to UTF-8.").
        if from_meta and name.startswith("utf-16"):
            name = "utf-8"
    try:
        return raw.decode(name, errors="replace")
    except (LookupError, UnicodeError):  # the binary transforms, undefined, idna, punycode
        return None


def _meta_labels(window: bytes):
    """The charset labels the page's <meta> tags declare, in document order."""
    for tag in _META_TAG.finditer(_COMMENT.sub(b" ", window)):
        attributes = {}
        for name, double, single, bare in _ATTRIBUTE.findall(tag.group(1)):
            attributes.setdefault(name.lower(), double or single or bare)
        label = attributes.get(b"charset")
        if label is None and attributes.get(b"http-equiv", b"").strip().lower() == b"content-type":
            found = _CONTENT_CHARSET.search(attributes.get(b"content", b""))
            label = (found.group(1) or found.group(2) or found.group(3)) if found else None
        if label:
            yield label.decode("ascii", errors="replace")


def decode_body(raw: bytes, header_charset: str | None) -> str:
    """Decode with the header's charset, else the page's own meta charset, else UTF-8."""
    text = _try_decode(raw, header_charset, False)
    if text is None:
        for label in _meta_labels(raw[:2048]):
            text = _try_decode(raw, label, True)
            if text is not None:
                break
    if text is None:
        text = raw.decode("utf-8", errors="replace")
    return text


def fetch(url: str, timeout: float = 30.0) -> str:
    return fetch_final(url, timeout)[0]


def fetch_final(url: str, timeout: float = 30.0) -> tuple:
    """(page text, the address the fetch ended on after any redirects)."""
    request = urllib.request.Request(url, headers={
        "User-Agent": CHROME_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - operator-supplied URL
        return decode_body(response.read(), response.headers.get_content_charset()), response.geturl()


class FooterScope:
    """The page footer, as every check reads it: feed it each start and end tag in document order.

    A footer is the page footer only when no ancestor is article, aside, main, nav or section, or carries the
    role article, complementary, main, navigation or region (W3C ARIA in HTML, footer row:
    https://www.w3.org/TR/html-aria/#el-footer; HTML-AAM 3.5.43 and 3.5.44:
    https://www.w3.org/TR/html-aam-1.0/#el-footer-ancestorbody). An element with role=contentinfo opens the
    scope wherever it is. A blockquote does not exclude a footer."""

    def __init__(self):
        self._open = {}          # open count per non-void tag name
        self._footer = None      # (tag name, its open count at the start tag) while a footer scope is open
        self.has_footer = False
        self._not_page_footer = []  # (tag name, open count) of each open element that stops a <footer> being the page footer

    @property
    def inside(self):
        return self._footer is not None

    def start(self, tag, attrs):
        """Runs before any early return, so every start tag is counted. `attrs` is a dict."""
        if tag in VOID:
            return
        self._open[tag] = self._open.get(tag, 0) + 1
        role = (attrs.get("role") or "").strip().lower()
        opens = role == "contentinfo" or (tag == "footer" and not self._not_page_footer)
        if self._footer is None and opens:
            self._footer = (tag, self._open[tag])
            self.has_footer = True
        if tag in NOT_PAGE_FOOTER_TAGS or role in NOT_PAGE_FOOTER_ROLES:
            self._not_page_footer.append((tag, self._open[tag]))

    def end(self, tag):
        """An end tag takes one off its tag's count, never below zero; the scope closes with its tag."""
        if tag in VOID or self._open.get(tag, 0) == 0:
            return
        self._open[tag] -= 1
        self._not_page_footer = [(t, n) for t, n in self._not_page_footer if not (t == tag and self._open[tag] < n)]
        if self._footer and tag == self._footer[0] and self._open[tag] < self._footer[1]:
            self._footer = None


class _Collector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = None
        self.meta_description = None
        self.headings = []
        self.links = []
        self.forms = []
        self.images = []
        self.jsonld = []
        self._stack = []
        self._buf = []
        self._svg_depth = 0
        self._in_svg_title = False
        self._scope = FooterScope()

    @property
    def has_footer(self):
        return self._scope.has_footer

    def handle_starttag(self, tag, attrs):
        attrs = {name: "" if value is None else value for name, value in attrs}  # a bare attribute's value is ""
        self._scope.start(tag, attrs)
        in_footer = self._scope.inside
        if tag == "svg":
            self._svg_depth += 1
        elif tag == "title" and self._svg_depth:
            self._in_svg_title = True  # an SVG's <title> labels the graphic: its text goes nowhere
            return
        if tag in HEADING_TAGS or tag in ("title", "a", "button"):
            self._stack.append((tag, attrs, in_footer))
            self._buf.append([])
        elif tag == "meta" and attrs.get("name", "").lower() == "description":
            self.meta_description = attrs.get("content")
        elif tag == "img":
            self.images.append({
                "src": attrs.get("src"),
                "alt": attrs.get("alt"),  # a bare alt is "", decorative; an absent attribute stays None
                "loading": attrs.get("loading"),
                "fetchpriority": attrs.get("fetchpriority"),
            })
        elif tag == "form":
            self.forms.append({"action": attrs.get("action"),
                               "method": (attrs.get("method") or "get").lower(),
                               "fields": []})
        elif tag in ("input", "select", "textarea") and self.forms:
            self.forms[-1]["fields"].append({
                "name": attrs.get("name"),
                "type": attrs.get("type") or tag,
                "required": "required" in attrs,
            })
        elif tag == "script" and attrs.get("type") == "application/ld+json":
            self._stack.append((tag, attrs, in_footer))
            self._buf.append([])

    def handle_data(self, data):
        if self._in_svg_title:
            return
        for buf in self._buf:  # every open element gets the text, as a browser's textContent does
            buf.append(data)

    def handle_endtag(self, tag):
        self._scope.end(tag)
        if tag == "title" and self._in_svg_title:
            self._in_svg_title = False
            return
        if tag == "svg" and self._svg_depth:
            self._svg_depth -= 1
        if not self._stack or self._stack[-1][0] != tag:
            return
        _tag, attrs, in_footer = self._stack.pop()
        text = "".join(self._buf.pop()).strip()
        if tag in HEADING_TAGS:
            self.headings.append({"level": int(tag[1]), "text": text, "in_footer": in_footer})
        elif tag == "title":
            if not self.title:  # keep the first non-empty document title
                self.title = text
        elif tag in ("a", "button"):
            self.links.append({"text": text, "href": attrs.get("href"), "kind": tag, "in_footer": in_footer})
        elif tag == "script":
            self.jsonld.append(text)


def _schema_types(blocks, notes):
    types = []
    for block in blocks:
        try:
            data = json.loads(block)
        except (ValueError, RecursionError):  # not JSON, or nested too deep to read
            notes.append("A JSON-LD block failed to parse; its types could not be read.")
            continue
        for node in _walk(data):
            value = node.get("@type")
            if isinstance(value, list):
                types.extend(item for item in value if isinstance(item, str))
            elif isinstance(value, str):
                types.append(value)
    return sorted(set(types))


def _walk(data):
    if isinstance(data, dict):
        yield data
        for value in data.values():
            yield from _walk(value)
    elif isinstance(data, list):
        for item in data:
            yield from _walk(item)


def extract_facts(html, url=""):
    collector = _Collector()
    collector.feed(html)
    notes = []

    h1_count = sum(1 for h in collector.headings if h["level"] == 1)
    if h1_count == 0:
        notes.append("No h1 found.")
    elif h1_count > 1:
        notes.append("%d h1 elements found; expected one." % h1_count)

    schema_types = _schema_types(collector.jsonld, notes)
    if not schema_types:
        notes.append("No JSON-LD structured data found in the static markup. "
                     "It may be injected by JavaScript — confirm with a rendered capture.")
    if "?" in url:
        notes.append("The URL carried a query string. Some configurations strip JSON-LD "
                     "from parameterised URLs, so a schema result here can be a false "
                     "negative. Re-check the clean URL.")

    notes.append("Static markup only. CSS-hidden text, JS-rendered sections and "
                 "consent-gated tags are NOT covered — route those to 'Could not check' "
                 "unless a rendered capture confirms them.")

    ctas = [link for link in collector.links
            if link["text"] and any(hint in link["text"].lower() for hint in CTA_HINTS)]

    lcp_candidates = collector.images[:LCP_CANDIDATE_CAP]
    if any(img.get("loading") == "lazy" for img in lcp_candidates):
        notes.append("An image among the first %d in document order is marked "
                     "loading=\"lazy\". That is a common LCP regression: it defers the "
                     "browser's earliest, most likely candidate behind the lazy-load "
                     "trigger instead of requesting it immediately. This is deterministically "
                     "visible in markup, so report it as a finding, not a caveat."
                     % LCP_CANDIDATE_CAP)
    notes.append("lcp_candidates are the first images in document order, not a measured "
                 "Largest Contentful Paint element. Which one is actually largest and "
                 "above the fold depends on rendered layout, viewport and load timing — "
                 "none of which static markup can see. Confirm the true LCP element with "
                 "a rendered capture (Lighthouse or DevTools Performance) before naming "
                 "one; until then this belongs under 'Could not check', not 'Not a problem'.")

    return {
        "url": url,
        "title": collector.title,
        "meta_description": collector.meta_description,
        "headings": collector.headings,
        "links": collector.links,
        "has_footer": collector.has_footer,
        "ctas": ctas,
        "forms": collector.forms,
        "schema_types": schema_types,
        "images": collector.images,
        "lcp_candidates": lcp_candidates,
        "notes": notes,
    }


# What reading a file, fetching an address and writing a file can raise; a defect in extract_facts is not here.
_IO_ERRORS = (OSError, urllib.error.URLError, http.client.HTTPException, ValueError, UnicodeError)


def _reason(error):
    """The cause in a few words, on one line."""
    if isinstance(error, urllib.error.URLError):
        error = error.reason  # a URLError holds the failure it wraps
    return (getattr(error, "strerror", None) or str(error) or type(error).__name__).splitlines()[0]


def main(argv):
    parser = argparse.ArgumentParser(description="Deterministic page facts from static markup.")
    parser.add_argument("target", metavar="file.html|url")
    parser.add_argument("--url", default="", help="the original URL, for a saved file")
    parser.add_argument("--out", help="write the JSON to this file and print one summary line")
    args = parser.parse_args(argv)
    target, url, out = args.target, args.url, args.out
    try:
        if target.startswith("http"):
            html = fetch(target)
            url = url or target
        else:
            with open(target, "rb") as handle:
                html = decode_body(handle.read(), None)
    except _IO_ERRORS as error:
        print("page_facts: cannot read %s: %s" % (target, _reason(error)), file=sys.stderr)
        return 2
    text = json.dumps(extract_facts(html, url), indent=2, ensure_ascii=False)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if out:
        try:
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            Path(out).write_text(text + "\n", encoding="utf-8")
        except _IO_ERRORS as error:
            print("page_facts: cannot write %s: %s" % (out, _reason(error)), file=sys.stderr)
            return 2
        facts = json.loads(text)
        print("page_facts: wrote %s: %d headings, %d links, %d forms, %d images"
              % (out, len(facts["headings"]), len(facts["links"]), len(facts["forms"]), len(facts["images"])))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
