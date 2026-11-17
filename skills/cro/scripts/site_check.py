#!/usr/bin/env python3
"""Site check: a built site or live pages, checked against the launch rules. Python 3 stdlib only.

    site_check.py (--dist DIR | --url URL...) [--deck DECK.md --map URL=NS[.V]...] [--pages FILE] [--forbid FILE]
                  [--visible-text DIR]

--dist reads every .html file under DIR; a page's URL is its path from DIR (`/index.html`). --url fetches each address with
page_facts.fetch, which sends an ordinary Chrome agent. Without --deck the copy rules are skipped, not passed.
--map names the namespace a page shows, and for a deck with variants its letter: `--map /b.html=p.b`. --pages is a JSON list
[{"url": str, "mode": "search" | "direct", "paid": bool, "keyword": str | null}] and switches NOINDEX on. --forbid is one word or
phrase per line, `#` lines and blank lines ignored. --visible-text writes each page's text to DIR/<page slug>.txt.
Every line is `<FAIL|WARN|SKIPPED> <page URL> <RULE>: <detail>`, then `site_check: <f> FAIL, <w> WARN`. Exit 1 on any FAIL, 2 on
bad input.

NOINDEX is a WARN: Google documents that noindex drops a page from Search results, but no page read says that a noindexed page
stays usable as an ad destination, so that half of the rule is UNVERIFIED (skills/cro/references/check.md cites the pages).
"""
import argparse
import json
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "conversion-page-audit" / "scripts"))
from deck_check import parse_deck  # noqa: E402
from page_facts import decode_body, extract_facts, fetch  # noqa: E402
from search_check import normalise, page_text  # noqa: E402
from wire_check import rendered, squash  # noqa: E402

PLACEHOLDER = re.compile(r"(?i:\blorem\b)|\bTODO\b|\bTBD\b|\[NEEDED")
NO_LINK = ("#", "mailto:", "tel:", "sms:", "javascript:", "data:")
NOINDEX_UNVERIFIED = ("UNVERIFIED: Google documents that noindex keeps a page out of Search results, but no page read says a "
                      "noindexed page stays usable as an ad destination")


class BadInput(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        print("%s: %s" % (self.prog, message), file=sys.stderr)
        sys.exit(2)


def read_forbid(path):
    """The words of a --forbid file, one per line; BadInput when it cannot be read."""
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        raise BadInput("cannot read %s as UTF-8 text" % path)
    return [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]


def forbid_pattern(words):
    """Whole words or phrases, case-insensitive, any run of whitespace matching a space."""
    if not words:
        return None
    parts = sorted((r"\s+".join(re.escape(w) for w in word.split()) for word in words), key=lambda p: (-len(p), p))
    return re.compile(r"(?<!\w)(?:%s)(?!\w)" % "|".join(parts), re.IGNORECASE)


def finish(stem, rows):
    """Print the rows and the summary line; the exit code."""
    for level, key, rule, detail in rows:
        print("%s %s %s: %s" % (level, key, rule, detail))
    fails = sum(1 for r in rows if r[0] == "FAIL")
    warns = sum(1 for r in rows if r[0] == "WARN")
    print("%s: %d FAIL, %d WARN" % (stem, fails, warns))
    return 1 if fails else 0


class _SiteFacts(HTMLParser):
    """What page_facts.extract_facts does not return: the canonical link, the robots metas and the JSON-LD bodies."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.canonical = None
        self.robots = []
        self.jsonld = []
        self.attr_text = []  # what a visitor sees that is not a text node: button values and image alt text
        self._ld = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "link" and "canonical" in (a.get("rel") or "").lower().split():
            if self.canonical is None:
                self.canonical = (a.get("href") or "").strip()
        elif tag == "meta" and (a.get("name") or "").lower() in ("robots", "googlebot"):
            self.robots.append((a.get("content") or "").lower())
        elif tag == "script" and (a.get("type") or "").lower() == "application/ld+json":
            self._ld = []
        elif tag == "img" and a.get("alt"):
            self.attr_text.append(a["alt"])
        elif tag == "input" and (a.get("type") or "").lower() in ("submit", "button", "reset") and a.get("value"):
            self.attr_text.append(a["value"])

    def handle_data(self, data):
        if self._ld is not None:
            self._ld.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._ld is not None:
            self.jsonld.append("".join(self._ld))
            self._ld = None

    @property
    def noindex(self):
        return any(t in ("noindex", "none") for content in self.robots for t in re.split(r"[,\s]+", content))


class Page:
    def __init__(self, url, html):
        self.url = url
        self.facts = extract_facts(html, url)
        site = _SiteFacts()
        site.feed(html)
        site.close()
        self.site = site
        self.text = " ".join([page_text(html)] + site.attr_text)
        self.squashed = squash(self.text)
        self.compact = "".join(self.text.split())  # no whitespace at all: inline markup beside punctuation adds spaces

    @property
    def path(self):
        return urllib.parse.urlparse(self.url).path or "/"

    def paths(self):
        """The paths a sitemap may use for this page: its own, and its folder for an index file."""
        found = {self.path}
        for name in ("/index.html", "/index.htm"):
            if self.path.endswith(name):
                found.add(self.path[:-len(name)] + "/")
        return found


def walk(data):
    if isinstance(data, dict):
        yield data
        for value in data.values():
            yield from walk(value)
    elif isinstance(data, list):
        for item in data:
            yield from walk(item)


def faq_entities(page):
    """(questions and answers of every FAQPage in the page's JSON-LD, whether a block failed to parse)."""
    pairs, found, broken = [], False, False
    for body in page.site.jsonld:
        try:
            data = json.loads(body)
        except ValueError:
            broken = True
            continue
        for node in walk(data):
            kind = node.get("@type")
            if "FAQPage" in (kind if isinstance(kind, list) else [kind]):
                found = True
                entities = node.get("mainEntity") or []
                for entity in entities if isinstance(entities, list) else [entities]:
                    if isinstance(entity, dict):
                        answer = entity.get("acceptedAnswer") or {}
                        pairs.append((squash(str(entity.get("name") or "")),
                                      squash(str(answer.get("text") or "")) if isinstance(answer, dict) else ""))
    return pairs, found, broken


def deck_faq(deck, ns):
    pairs, n = [], 1
    while "%s.faq.q%d" % (ns, n) in deck.values and "%s.faq.a%d" % (ns, n) in deck.values:
        pairs.append((squash(deck.values["%s.faq.q%d" % (ns, n)]), squash(deck.values["%s.faq.a%d" % (ns, n)])))
        n += 1
    return pairs


def shorten(text, size=60):
    return text if len(text) <= size else text[:size] + "..."


def page_rows(page, deck, mapped, forbid, add, internal_link):
    facts = page.facts
    url = page.url
    h1s = [h for h in facts["headings"] if h["level"] == 1]
    if len(h1s) != 1:
        add("FAIL", url, "H1", "%d h1 elements; a page has exactly one" % len(h1s))
    if not (facts["title"] or "").strip():
        add("FAIL", url, "TITLE", "no title")
    if not (facts["meta_description"] or "").strip():
        add("FAIL", url, "META_DESCRIPTION", "no meta description")
    canonical = page.site.canonical
    parsed = urllib.parse.urlparse(canonical or "")
    if not canonical:
        add("FAIL", url, "CANONICAL", "no canonical link")
    elif parsed.scheme not in ("http", "https") or not parsed.netloc:
        add("FAIL", url, "CANONICAL", "%r is not an absolute URL" % canonical)
    for image in facts["images"]:
        if image["alt"] is None:
            add("FAIL", url, "ALT", "an image without an alt attribute: %s" % shorten(image["src"] or "(no src)"))
    for found in sorted({m.group(0) for m in PLACEHOLDER.finditer(page.text)}):
        add("FAIL", url, "PLACEHOLDER", "the page text holds %r" % found)
    pattern = forbid_pattern(forbid)
    if pattern:
        for found in sorted({m.group(0).lower() for m in pattern.finditer(page.squashed)}):
            add("FAIL", url, "FORBIDDEN", "the page text holds %r" % found)
    if deck is None:
        add("SKIPPED", url, "PARITY", "no --deck")
        add("SKIPPED", url, "FAQ_SCHEMA", "no --deck")
    elif url not in mapped:
        add("SKIPPED", url, "PARITY", "no --map line for this page")
        add("SKIPPED", url, "FAQ_SCHEMA", "no --map line for this page")
    else:
        ns, v = mapped[url]
        rows = rendered(deck, ns, v)
        has_button = any(kind == "button" for _, kind, _ in rows)
        wanted = {}
        for key, kind, value in rows:
            if kind == "label" and has_button:
                continue  # every button shows the label, and each button is checked on its own row
            have = max(page.squashed.count(squash(value)), page.compact.count("".join(value.split())))
            if kind == "button":  # each button row needs an occurrence of its own, not a share of one
                wanted[squash(value)] = wanted.get(squash(value), 0) + 1
            if have < (wanted[squash(value)] if kind == "button" else 1):
                add("FAIL", url, "PARITY", "%s is not in the page text: %r" % (key, shorten(squash(value))))
        want = deck_faq(deck, ns)
        got, found, broken = faq_entities(page)
        if broken:
            add("FAIL", url, "FAQ_SCHEMA", "a JSON-LD block is not valid JSON")
        if want and not found:
            add("FAIL", url, "FAQ_SCHEMA", "the deck has %d question and answer pairs and the page has no FAQPage JSON-LD" % len(want))
        elif got != want and (want or found):
            at = next((i for i, (g, w) in enumerate(zip(got, want)) if g != w), min(len(got), len(want)))
            add("FAIL", url, "FAQ_SCHEMA", "the FAQPage has %d question and answer pairs and the deck %d; they first differ at pair %d"
                % (len(got), len(want), at + 1))
        for n, (q, a) in enumerate(want, 1):
            if any(t not in page.squashed and "".join(t.split()) not in page.compact for t in (q, a)):
                add("FAIL", url, "FAQ_SCHEMA", "pair %d of the deck is not in the page text" % n)
    seen = set()
    for link in facts["links"]:
        href = (link["href"] or "").strip()
        if not href or href.lower().startswith(NO_LINK) or href in seen:
            continue
        seen.add(href)
        problem = internal_link(page, href)
        if problem:
            add("FAIL", url, "LINK", "%s: %s" % (href, problem))


def check_noindex(pages_list, pages, add):
    by_url = {p.url: p for p in pages}
    search_keywords = {normalise(e["keyword"]) for e in pages_list if e["mode"] == "search" and e.get("keyword")}
    for entry in pages_list:
        page = by_url.get(entry["url"])
        if page is None:
            add("SKIPPED", entry["url"], "NOINDEX", "not among the pages checked")
            continue
        noindex = page.site.noindex
        mode, paid, keyword = entry["mode"], bool(entry.get("paid")), entry.get("keyword")
        if mode == "search" and noindex:
            add("WARN", page.url, "NOINDEX", "a Search page carries noindex and cannot rank; %s" % NOINDEX_UNVERIFIED)
        elif mode == "direct" and not paid and noindex:
            add("WARN", page.url, "NOINDEX", "an unpaid Direct page (a website page) carries noindex; %s" % NOINDEX_UNVERIFIED)
        elif mode == "direct" and paid and not noindex and keyword and normalise(keyword) in search_keywords:
            add("WARN", page.url, "NOINDEX", "a paid Direct page without noindex competes with the Search page for %r; %s"
                % (keyword, NOINDEX_UNVERIFIED))


def sitemap_locs(file):
    """(root kind, loc texts) of one sitemap file."""
    root = ET.parse(file).getroot()
    kind = root.tag.rsplit("}", 1)[-1]
    locs = [c.text.strip() for el in root for c in el if c.tag.rsplit("}", 1)[-1] == "loc" and c.text and c.text.strip()]
    return kind, locs


def load_sitemap(dist, add):
    """The URLs the sitemap lists, or None when there is none; a sitemap index is followed one level."""
    index, single = dist / "sitemap-index.xml", dist / "sitemap.xml"
    top = index if index.is_file() else single if single.is_file() else None
    if top is None:
        add("FAIL", "sitemap.xml", "SITEMAP", "neither sitemap.xml nor sitemap-index.xml is in the dist folder")
        return None
    urls = []
    try:
        kind, locs = sitemap_locs(top)
        if kind != "sitemapindex":
            return locs
        for loc in locs:
            child = dist / urllib.parse.unquote(urllib.parse.urlparse(loc).path).lstrip("/")
            if not child.is_file():
                add("FAIL", top.name, "SITEMAP", "%s lists %s, which is not in the dist folder" % (top.name, loc))
                continue
            child_kind, child_locs = sitemap_locs(child)
            if child_kind == "sitemapindex":
                add("WARN", child.name, "SITEMAP", "a sitemap index inside a sitemap index; only one level is read")
            else:
                urls.extend(child_locs)
    except ET.ParseError as error:
        add("FAIL", top.name, "SITEMAP", "%s is not valid XML: %s" % (top.name, error))
        return None
    return urls


def robots_allows(text, path):
    """Whether Googlebot may fetch `path` under robots.txt: the longest matching rule wins and Allow wins a tie.
    Group rules follow https://developers.google.com/search/docs/crawling-indexing/robots/robots_txt : a group that names
    Googlebot wins over the * group even with no rules, groups naming the same agent combine, and a BOM is ignored."""
    groups, agents, rules, fresh = [], [], [], True
    for raw in text.lstrip("\ufeff").splitlines():
        line = raw.split("#", 1)[0].strip()
        field, _, value = line.partition(":")
        field, value = field.strip().lower(), value.strip()
        if field == "user-agent":
            if not fresh:
                agents, rules, fresh = [], [], True
            if not agents:
                groups.append((agents, rules))
            agents.append(value.lower())
        elif field in ("allow", "disallow"):
            fresh = False
            if value:
                rules.append((field == "allow", value))
    named = [r for a, r in groups if "googlebot" in a] or [r for a, r in groups if "*" in a]
    chosen = [rule for r in named for rule in r]
    best = (-1, True)
    for allow, pattern in chosen:
        body = re.escape(pattern.rstrip("$")).replace(r"\*", ".*") + ("$" if pattern.endswith("$") else "")
        if re.match(body, path) and (len(pattern), allow) > best:
            best = (len(pattern), allow)
    return best[1]


def site_files(dist, pages, add):
    urls = load_sitemap(dist, add)
    listed = {}
    if urls is not None:
        for page in pages:
            canonical = page.site.canonical
            match = [u for u in urls if u == canonical or urllib.parse.urlparse(u).path in page.paths()]
            listed[page.url] = match
            if page.site.noindex and match:
                add("FAIL", page.url, "SITEMAP", "a noindex page is listed in the sitemap as %s" % match[0])
            elif not page.site.noindex and not match:
                add("FAIL", page.url, "SITEMAP", "an indexable page the sitemap does not list")
    robots = dist / "robots.txt"
    if not robots.is_file():
        add("FAIL", "robots.txt", "ROBOTS", "robots.txt is not in the dist folder")
        return
    text = robots.read_text(encoding="utf-8", errors="replace")
    for url in urls or []:
        parsed = urllib.parse.urlparse(url)
        if not robots_allows(text, (parsed.path or "/") + ("?" + parsed.query if parsed.query else "")):
            owner = next((p.url for p in pages if url in listed.get(p.url, [])), url)
            add("FAIL", owner, "ROBOTS", "robots.txt blocks %s, which the sitemap lists" % url)


def make_internal_link(dist, fetch_page):
    cache = {}

    def check(page, href):
        if dist is not None:
            base = "http://dist.invalid" + page.path
            hosts = {"dist.invalid", urllib.parse.urlparse(page.site.canonical or "").netloc} - {""}
            target = urllib.parse.urlparse(urllib.parse.urljoin(base, href))
            if target.netloc not in hosts or target.scheme not in ("http", "https"):
                return None
            path = urllib.parse.unquote(target.path) or "/"
            file = dist / path.lstrip("/")
            if file.is_dir() or path.endswith("/"):
                file = file / "index.html"
            if file.is_file() or (not file.suffix and file.with_name(file.name + ".html").is_file()):
                return None
            return "no such file in the dist folder"
        target = urllib.parse.urljoin(page.url, href)
        parts = urllib.parse.urlparse(target)
        if parts.scheme not in ("http", "https") or parts.netloc != urllib.parse.urlparse(page.url).netloc:
            return None
        target = urllib.parse.urldefrag(target)[0]
        if target not in cache:
            try:
                fetch_page(target)
                cache[target] = None
            except Exception as error:  # noqa: BLE001 - any failure to fetch is the finding
                cache[target] = "the address answered %s" % shorten(str(error), 80)
        return cache[target]

    return check


def parse_maps(maps, deck, urls):
    mapped = {}
    for spec in maps:
        url, eq, name = spec.rpartition("=")
        if not eq or not url or not name:
            raise BadInput("--map %r is not URL=NS" % spec)
        ns, _, v = name.partition(".")
        if ns not in deck.namespaces:
            raise BadInput("--map %r: %r is not a namespace of the deck (it has %s)" % (spec, ns, ", ".join(deck.namespaces) or "none"))
        variants = deck.variants(ns)
        if variants == [""]:
            if v:
                raise BadInput("--map %r: the deck has no variants for %s; map it as %s" % (spec, ns, ns))
        elif not v:
            raise BadInput("--map %r: the deck has variants %s; name the page's, as %s.%s" % (spec, ", ".join(variants), ns, variants[0]))
        elif v not in variants:
            raise BadInput("--map %r: %r is not a variant of the deck (it has %s)" % (spec, v, ", ".join(variants)))
        if url not in urls:
            raise BadInput("--map names %s, which is not one of the pages checked" % url)
        mapped[url] = (ns, v)
    return mapped


def load_pages_list(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise BadInput("cannot read %s as JSON" % path)
    if not isinstance(data, list) or not all(isinstance(e, dict) and isinstance(e.get("url"), str) and e.get("mode") in ("search", "direct")
                                             for e in data):
        raise BadInput('%s must be a JSON list of {"url", "mode": "search" | "direct", "paid", "keyword"}' % path)
    return data


def slug(url):
    path = urllib.parse.urlparse(url).path.strip("/")
    path = re.sub(r"\.html?$", "", path)
    path = re.sub(r"(^|/)index$", "", path).strip("/")
    return re.sub(r"[^\w.-]+", "-", path) or "index"


def write_visible_text(directory, pages):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    used = {}
    for page in pages:
        name = slug(page.url)
        used[name] = used.get(name, 0) + 1
        stem = name if used[name] == 1 else "%s-%d" % (name, used[name])
        (directory / (stem + ".txt")).write_text(page.text + "\n", encoding="utf-8")


def not_a_launch_page(url):
    """Why a --dist file is not a launch page, or None: the error page, or Google's verification file."""
    path = urllib.parse.urlparse(url).path
    if path.endswith("/404.html") or path == "/404/index.html":
        return "the error page is not a launch page"
    if re.fullmatch(r"/(?:.*/)?google[0-9a-f]{16}\.html", path):
        return "a search engine's verification file is not a launch page"
    return None


def load_pages(args, named=(), skipped=None):
    pages = []
    if args.dist:
        dist = Path(args.dist)
        if not dist.is_dir():
            raise BadInput("%s is not a folder" % args.dist)
        for file in sorted(dist.rglob("*.html")):
            url = "/" + file.relative_to(dist).as_posix()
            why = not_a_launch_page(url)
            if why and url not in named and skipped is not None:
                skipped.append((url, why))
                continue
            try:
                pages.append(Page(url, decode_body(file.read_bytes(), None)))
            except OSError as error:
                raise BadInput("cannot read %s: %s" % (file, error.strerror or error))
        if not pages:
            raise BadInput("no .html file under %s" % args.dist)
    else:
        for url in args.url:
            try:
                pages.append(Page(url, fetch(url)))
            except Exception as error:  # noqa: BLE001 - the address could not be read
                raise BadInput("cannot fetch %s: %s" % (url, error))
    return pages


def main(argv=None):
    parser = Parser(prog="site_check", description="Check a built site or live pages against the launch rules.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--dist", metavar="DIR")
    source.add_argument("--url", nargs="+", metavar="URL")
    parser.add_argument("--deck", metavar="DECK.md")
    parser.add_argument("--map", action="append", default=[], metavar="URL=NS")
    parser.add_argument("--pages", metavar="FILE")
    parser.add_argument("--forbid", metavar="FILE")
    parser.add_argument("--visible-text", metavar="DIR")
    args = parser.parse_args(argv)
    rows = []

    def add(level, key, rule, detail):
        row = (level, key, rule, detail)
        if row not in rows:
            rows.append(row)

    try:
        if args.map and not args.deck:
            raise BadInput("--map needs --deck")
        deck = None
        if args.deck:
            try:
                deck = parse_deck(Path(args.deck).read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError):
                raise BadInput("cannot read %s as UTF-8 text" % args.deck)
        forbid = read_forbid(args.forbid) if args.forbid else []
        pages_list = load_pages_list(args.pages) if args.pages else None
        skipped = []
        pages = load_pages(args, {e["url"] for e in pages_list or []}, skipped)
        mapped = parse_maps(args.map, deck, {p.url for p in pages}) if deck else {}
    except BadInput as error:
        print("site_check: %s" % error, file=sys.stderr)
        return 2
    for url, why in skipped:
        add("SKIPPED", url, "LAUNCH_PAGE", why)
    dist = Path(args.dist) if args.dist else None
    internal_link = make_internal_link(dist, fetch)
    for page in pages:
        page_rows(page, deck, mapped, forbid, add, internal_link)
    if dist is not None:
        site_files(dist, pages, add)
    else:
        add("SKIPPED", pages[0].url, "SITEMAP", "needs --dist: a live site's sitemap is not read")
        add("SKIPPED", pages[0].url, "ROBOTS", "needs --dist: a live site's robots.txt is not read")
    if pages_list is not None:
        check_noindex(pages_list, pages, add)
    if args.visible_text:
        try:
            write_visible_text(args.visible_text, pages)
        except OSError as error:
            print("site_check: cannot write %s: %s" % (args.visible_text, error.strerror or error), file=sys.stderr)
            return 2
    return finish("site_check", rows)


if __name__ == "__main__":
    sys.exit(main())
