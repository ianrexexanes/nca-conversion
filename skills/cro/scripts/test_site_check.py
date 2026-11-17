import html as html_lib
import json
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "conversion-page-audit" / "scripts"))
import deck_check  # noqa: E402
import page_facts  # noqa: E402
import site_check  # noqa: E402

SCRIPT = HERE / "site_check.py"
FIXTURES = HERE / "fixtures"
CLEAN = str(FIXTURES / "site-clean")
CLEAN_DECK = str(FIXTURES / "deck-clean-direct.md")
CLEAN_PAGES = str(FIXTURES / "site-clean" / "pages.json")
PLANTED = str(FIXTURES / "site-planted")
PLANTED_DECK = str(FIXTURES / "site-planted" / "deck.md")
PLANTED_PAGES = str(FIXTURES / "site-planted" / "pages.json")
FORBID = str(FIXTURES / "site-planted" / "forbid.txt")
VARIANTS_DECK = str(FIXTURES / "deck-variants.md")
ORIGIN = "https://example.test"
SUMMARY_0 = "site_check: 0 FAIL, 0 WARN"


def run(*args):
    done = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    return done.returncode, done.stdout + done.stderr


def rules_in(output, levels=("FAIL", "WARN")):
    return {m.group(2) for m in re.finditer(r"^(%s) \S+ ([A-Z_0-9]+):" % "|".join(levels), output, re.M)}


def faq_pairs(deck, ns):
    pairs, n = [], 1
    while "%s.faq.q%d" % (ns, n) in deck.values and "%s.faq.a%d" % (ns, n) in deck.values:
        pairs.append((deck.values["%s.faq.q%d" % (ns, n)], deck.values["%s.faq.a%d" % (ns, n)]))
        n += 1
    return pairs


def page_html(deck_path, v="", canonical=ORIGIN + "/", noindex=False, footer="Example Co, all rights reserved.", body_extra="",
              schema_answer=None):
    """A page that shows a deck the way the Interfaces table says: the variant's slots and the label on every button."""
    deck = deck_check.parse_deck(Path(deck_path).read_text(encoding="utf-8"))
    ns = deck.namespaces[0]
    vals = deck.values
    label = deck.label(ns, v)
    esc = html_lib.escape
    head = ['<meta charset="utf-8">', "<title>%s</title>" % esc(vals[ns + ".meta.title"]),
            '<meta name="description" content="%s">' % esc(vals[ns + ".meta.description"])]
    if canonical:
        head.append('<link rel="canonical" href="%s">' % canonical)
    if noindex:
        head.append('<meta name="robots" content="noindex">')
    entities = [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq_pairs(deck, ns)]
    if schema_answer is not None and entities:
        entities[0]["acceptedAnswer"]["text"] = schema_answer
    head.append('<script type="application/ld+json">%s</script>'
                % json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": entities}))
    sections = []
    for key in deck.order:
        parts = key.split(".")
        if len(parts) > 2 and parts[0] == ns and parts[1] in deck_check.SECTIONS and parts[1] not in sections:
            sections.append(parts[1])
    body = []
    for section in sections:
        rows = []
        for key in deck.order:
            parts = key.split(".")
            if parts[0] != ns or len(parts) < 3 or parts[1] != section:
                continue
            if section == "hero" and len(parts) >= 4 and len(parts[2]) == 1 and parts[2] != v:
                continue  # another variant's slot
            if section == "hero" and len(parts) == 3 and v and "%s.hero.%s.%s" % (ns, v, parts[2]) in vals:
                continue  # the shared slot this variant's own replaces
            rows.append((parts[-1], vals[key]))
        if section == "header":
            nav = "".join(('<a href="#form">%s</a>' % esc(label)) if slot == "cta" else "<span>%s</span>" % esc(val)
                          for slot, val in rows if slot in ("cta", "phone"))
            body.append("<header>%s<nav>%s</nav></header>" % ("".join("<p>%s</p>" % esc(val) for slot, val in rows
                                                                      if slot not in ("cta", "phone")), nav))
            continue
        body.append('<section id="%s">' % section)
        for slot, val in rows:
            if slot == "visual":
                body.append('<img src="/img/%s.png" alt="%s picture">' % (section, section))
            elif slot == "cta":
                body.append('<a href="#form">%s</a>' % esc(label))
            elif slot in ("h1", "h2"):
                body.append("<%s>%s</%s>" % (slot, esc(val), slot))
            else:
                body.append("<p>%s</p>" % esc(val))
        if section == "hero":
            body.append("<p>%s</p>" % esc(vals[ns + ".cta.fud"]))
        body.append("</section>")
    body.append('<form id="form"><label>Email <input type="email" name="email"></label><button type="submit">%s</button></form>'
                % esc(label))
    body.append(body_extra)
    body.append("<footer><p>%s</p></footer>" % esc(footer))
    return '<!doctype html>\n<html lang="en"><head>%s</head><body>\n%s\n</body></html>\n' % ("".join(head), "\n".join(body))


def urlset(urls):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + "".join("<url><loc>%s</loc></url>" % u for u in urls) + "</urlset>\n")


def sitemap_index(urls):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + "".join("<sitemap><loc>%s</loc></sitemap>" % u for u in urls) + "</sitemapindex>\n")


ROBOTS_OK = "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % ORIGIN


def write_site(root, pages, files=None):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    for path, text in pages.items():
        target = root / path.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    defaults = {"sitemap.xml": urlset([ORIGIN + "/"]), "robots.txt": ROBOTS_OK}
    for name, text in dict(defaults, **(files or {})).items():
        if text is not None:
            (root / name).write_text(text, encoding="utf-8")
    return root


class SiteCheckTests(unittest.TestCase):
    def site(self, pages, files=None, *args):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return run("--dist", str(write_site(Path(tmp.name) / "dist", pages, files)), *args)

    def test_clean_site_passes(self):
        code, out = run("--dist", CLEAN, "--deck", CLEAN_DECK, "--map", "/index.html=p", "--pages", CLEAN_PAGES)
        self.assertEqual(code, 0, out)
        self.assertTrue(out.rstrip().endswith(SUMMARY_0), out)

    def test_each_planted_rule_fires(self):
        code, out = run("--dist", PLANTED, "--deck", PLANTED_DECK, "--map", "/index.html=p", "--pages", PLANTED_PAGES,
                        "--forbid", FORBID)
        self.assertEqual(code, 1, out)
        self.assertTrue({"H1", "TITLE", "META_DESCRIPTION", "CANONICAL", "ALT", "PLACEHOLDER", "FORBIDDEN", "PARITY",
                         "FAQ_SCHEMA", "NOINDEX", "LINK", "SITEMAP", "ROBOTS"} <= rules_in(out), out)

    def test_output_lines_and_summary_count_levels(self):
        code, out = run("--dist", PLANTED, "--deck", PLANTED_DECK, "--map", "/index.html=p", "--pages", PLANTED_PAGES,
                        "--forbid", FORBID)
        lines = [l for l in out.splitlines() if l]
        for line in lines[:-1]:
            self.assertRegex(line, r"^(FAIL|WARN|SKIPPED) \S+ [A-Z_0-9]+: .+")
        fails = sum(1 for l in lines if l.startswith("FAIL "))
        warns = sum(1 for l in lines if l.startswith("WARN "))
        self.assertEqual(lines[-1], "site_check: %d FAIL, %d WARN" % (fails, warns))
        self.assertRegex(out, r"(?m)^FAIL /index\.html H1: ")

    def test_parity_ignores_page_meta_visual_and_other_variants(self):
        page = page_html(VARIANTS_DECK, "a")
        code, out = self.site({"/index.html": page}, None, "--deck", VARIANTS_DECK, "--map", "/index.html=p.a")
        self.assertEqual(code, 0, out)
        self.assertNotIn("PARITY", out)
        deck = deck_check.parse_deck(Path(VARIANTS_DECK).read_text(encoding="utf-8"))
        text = page.lower()
        for key in ("p.hero.b.h1", "p.hero.c.h1", "p.cta.hook.b", "p.meta.slug"):
            self.assertNotIn(deck.values[key].lower(), re.sub(r"<title>.*?</title>", "", text), key)

    def test_nav_labels_are_found_one_each(self):
        text = Path(VARIANTS_DECK).read_text(encoding="utf-8").replace("p.header.logo:", "p.header.nav: Pump care; Plans; Help centre\np.header.logo:", 1)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        deck = Path(tmp.name) / "deck.md"
        deck.write_text(text, encoding="utf-8")
        page = page_html(str(deck), "a").replace("Pump care; Plans; Help centre", "Pump care | Plans | Help centre")
        code, out = self.site({"/index.html": page}, None, "--deck", str(deck), "--map", "/index.html=p.a")
        self.assertNotIn("PARITY", out)
        code, out = self.site({"/index.html": page.replace("Plans", "Offers")}, None, "--deck", str(deck), "--map", "/index.html=p.a")
        self.assertRegex(out, r"(?m)^FAIL /index\.html PARITY: p\.header\.nav is not in the page text: 'Plans'")

    def test_parity_fails_a_changed_word_and_a_missing_button_label(self):
        page = page_html(VARIANTS_DECK, "b")
        code, out = self.site({"/index.html": page.replace("Know which pump fails next", "Know which pump breaks next")}, None,
                              "--deck", VARIANTS_DECK, "--map", "/index.html=p.b")
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"(?m)^FAIL /index\.html PARITY: p\.hero\.b\.h1")
        code, out = self.site({"/index.html": page}, None, "--deck", VARIANTS_DECK, "--map", "/index.html=p.a")
        self.assertIn("PARITY", rules_in(out), out)  # variant b's page read as variant a's

    def test_map_with_variants_needs_the_letter_and_a_known_one(self):
        page = page_html(VARIANTS_DECK, "a")
        for mapping in ("/index.html=p", "/index.html=p.z", "/index.html=q.a", "/nothing.html=p.a", "/index.html"):
            code, out = self.site({"/index.html": page}, None, "--deck", VARIANTS_DECK, "--map", mapping)
            self.assertEqual(code, 2, (mapping, out))
            self.assertTrue(out.startswith("site_check: "), out)
        code, out = self.site({"/index.html": page_html(CLEAN_DECK)}, None, "--deck", CLEAN_DECK, "--map", "/index.html=p.a")
        self.assertEqual(code, 2, out)  # a one-variant deck takes the bare namespace
        code, out = self.site({"/index.html": page}, None, "--map", "/index.html=p.a")
        self.assertEqual(code, 2, out)  # --map without --deck

    def test_unmapped_page_is_skipped_with_its_reason(self):
        pages = {"/index.html": page_html(CLEAN_DECK), "/about.html": page_html(CLEAN_DECK, canonical=ORIGIN + "/about.html")}
        code, out = self.site(pages, {"sitemap.xml": urlset([ORIGIN + "/", ORIGIN + "/about.html"])}, "--deck", CLEAN_DECK,
                              "--map", "/index.html=p")
        self.assertEqual(code, 0, out)
        self.assertRegex(out, r"(?m)^SKIPPED /about\.html PARITY: no --map line")
        self.assertRegex(out, r"(?m)^SKIPPED /about\.html FAQ_SCHEMA: no --map line")

    def test_faq_schema_matches_the_deck_pairs(self):
        good = page_html(CLEAN_DECK)
        code, out = self.site({"/index.html": good}, None, "--deck", CLEAN_DECK, "--map", "/index.html=p")
        self.assertEqual(code, 0, out)
        code, out = self.site({"/index.html": page_html(CLEAN_DECK, schema_answer="Not what the deck says.")}, None,
                              "--deck", CLEAN_DECK, "--map", "/index.html=p")
        self.assertIn("FAQ_SCHEMA", rules_in(out), out)
        no_schema = re.sub(r'<script type="application/ld\+json">.*?</script>', "", good, flags=re.S)
        code, out = self.site({"/index.html": no_schema}, None, "--deck", CLEAN_DECK, "--map", "/index.html=p")
        self.assertIn("FAQ_SCHEMA", rules_in(out), out)
        shown_gone = good.replace("<p>A fixed yearly fee per pump, quoted in writing after the report.</p>", "")
        code, out = self.site({"/index.html": shown_gone}, None, "--deck", CLEAN_DECK, "--map", "/index.html=p")
        self.assertRegex(out, r"(?m)^FAIL /index\.html FAQ_SCHEMA: .*page text")
        code, out = self.site({"/index.html": good}, None)
        self.assertRegex(out, r"(?m)^SKIPPED /index\.html FAQ_SCHEMA: no --deck")

    def noindex(self, entries):
        pages = {e["url"]: page_html(CLEAN_DECK, canonical=ORIGIN + e["url"], noindex=e.pop("noindex")) for e in entries}
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        listing = Path(tmp.name) / "pages.json"
        listing.write_text(json.dumps(entries), encoding="utf-8")
        site = write_site(Path(tmp.name) / "dist", pages, {"sitemap.xml": urlset([ORIGIN + u for u in pages])})
        return run("--dist", str(site), "--pages", str(listing))[1]

    def test_noindex_cases(self):
        direct = {"url": "/direct.html", "mode": "direct"}
        search = {"url": "/search.html", "mode": "search", "paid": False}
        fires = [
            [dict(direct, paid=True, keyword="Pump check", noindex=False), dict(search, keyword="pump-check", noindex=False)],
            [dict(direct, paid=False, keyword="Pump check", noindex=True)],
            [dict(search, keyword="pump check", noindex=True)],
        ]
        quiet = [
            [dict(direct, paid=True, keyword="Pump check", noindex=True), dict(search, keyword="pump check", noindex=False)],
            [dict(direct, paid=True, keyword="Pump check", noindex=False), dict(search, keyword="boiler service", noindex=False)],
            [dict(search, keyword="pump check", noindex=False)],
        ]
        for entries in fires:
            out = self.noindex(entries)
            self.assertIn("NOINDEX", rules_in(out), out)
        for entries in quiet:
            out = self.noindex(entries)
            self.assertNotIn("NOINDEX", rules_in(out), out)

    def test_noindex_is_a_warn_that_says_the_rule_is_unverified(self):
        out = self.noindex([{"url": "/s.html", "mode": "search", "paid": False, "keyword": "pump check", "noindex": True}])
        lines = [l for l in out.splitlines() if " NOINDEX:" in l]
        self.assertTrue(lines and all(l.startswith("WARN ") and "UNVERIFIED" in l for l in lines), out)

    def test_the_error_page_and_a_verification_file_are_skipped_not_checked(self):
        err = page_html(CLEAN_DECK, canonical=ORIGIN + "/404.html")
        verify = "google-site-verification: google0123456789abcdef.html\n"
        other = page_html(CLEAN_DECK, canonical=ORIGIN + "/other.html")
        out = self.site({"/index.html": page_html(CLEAN_DECK), "/404.html": err, "/docs/404.html": err, "/404/index.html": err,
                         "/google0123456789abcdef.html": verify})[1]
        self.assertNotRegex(out, r"(?m)^(FAIL|WARN) /(docs/)?404", out)
        self.assertNotRegex(out, r"(?m)^(FAIL|WARN) /google", out)
        for url in ("/404.html", "/docs/404.html", "/404/index.html", "/google0123456789abcdef.html"):
            self.assertEqual(len(re.findall(r"(?m)^SKIPPED %s " % re.escape(url), out)), 1, out)
        out = self.site({"/index.html": page_html(CLEAN_DECK), "/other.html": other})[1]
        self.assertRegex(out, r"(?m)^FAIL /other\.html SITEMAP: ")

    def test_an_error_page_in_a_language_folder_is_skipped_too(self):
        err = page_html(CLEAN_DECK, canonical=ORIGIN + "/en/404/")
        out = self.site({"/index.html": page_html(CLEAN_DECK), "/en/404/index.html": err})[1]
        self.assertNotRegex(out, r"(?m)^FAIL /en/404", out)
        self.assertEqual(len(re.findall(r"(?m)^SKIPPED /en/404/index\.html .*LAUNCH_PAGE", out)), 1, out)

    def test_a_skipped_kind_of_file_is_checked_when_the_pages_list_names_it(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        listing = Path(tmp.name) / "pages.json"
        listing.write_text(json.dumps([{"url": "/404.html", "mode": "direct", "paid": False}]), encoding="utf-8")
        out = self.site({"/index.html": page_html(CLEAN_DECK), "/404.html": page_html(CLEAN_DECK, canonical=ORIGIN + "/404.html")},
                        None, "--pages", str(listing))[1]
        self.assertRegex(out, r"(?m)^FAIL /404\.html SITEMAP: ")
        self.assertNotRegex(out, r"(?m)^SKIPPED /404\.html LAUNCH_PAGE")

    def test_a_pages_entry_with_no_page_is_skipped(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        listing = Path(tmp.name) / "pages.json"
        listing.write_text(json.dumps([{"url": "/gone.html", "mode": "search", "paid": False, "keyword": "x"}]), encoding="utf-8")
        code, out = self.site({"/index.html": page_html(CLEAN_DECK)}, None, "--pages", str(listing))
        self.assertRegex(out, r"(?m)^SKIPPED /gone\.html NOINDEX: ")

    def test_sitemap_lists_indexable_pages_and_no_noindex_page(self):
        out = self.site({"/index.html": page_html(CLEAN_DECK, noindex=True)})[1]
        self.assertRegex(out, r"(?m)^FAIL /index\.html SITEMAP: .*noindex")
        out = self.site({"/index.html": page_html(CLEAN_DECK)}, {"sitemap.xml": urlset([ORIGIN + "/other/"])})[1]
        self.assertRegex(out, r"(?m)^FAIL /index\.html SITEMAP: ")
        out = self.site({"/index.html": page_html(CLEAN_DECK)}, {"sitemap.xml": None})[1]
        self.assertRegex(out, r"(?m)^FAIL sitemap\.xml SITEMAP: ")

    def test_robots_must_exist_and_block_nothing_the_sitemap_lists(self):
        out = self.site({"/index.html": page_html(CLEAN_DECK)}, {"robots.txt": "User-agent: *\nDisallow: /\n"})[1]
        self.assertRegex(out, r"(?m)^FAIL /index\.html ROBOTS: ")
        out = self.site({"/index.html": page_html(CLEAN_DECK)}, {"robots.txt": None})[1]
        self.assertRegex(out, r"(?m)^FAIL robots\.txt ROBOTS: ")
        out = self.site({"/index.html": page_html(CLEAN_DECK)}, {"robots.txt": "User-agent: *\nDisallow: /private/\nAllow: /\n"})[1]
        self.assertNotIn("ROBOTS", rules_in(out), out)
        longest = "User-agent: *\nDisallow: /\nAllow: /$\n"
        out = self.site({"/index.html": page_html(CLEAN_DECK)}, {"robots.txt": longest})[1]
        self.assertNotIn("ROBOTS", rules_in(out), out)
        # a Googlebot group with no rules lets Googlebot fetch everything, whatever the * group says
        empty_group = "User-agent: *\nDisallow: /\n\nUser-agent: Googlebot\n"
        out = self.site({"/index.html": page_html(CLEAN_DECK)}, {"robots.txt": empty_group})[1]
        self.assertNotIn("ROBOTS", rules_in(out), out)
        # groups naming the same agent combine, and a named group never takes the * group's rules
        split = "User-agent: Googlebot\nAllow: /private/\n\nUser-agent: *\nAllow: /\n\nUser-agent: Googlebot\nDisallow: /\n"
        out = self.site({"/index.html": page_html(CLEAN_DECK)}, {"robots.txt": split})[1]
        self.assertRegex(out, r"(?m)^FAIL /index\.html ROBOTS: ")
        # a byte order mark at the start of the file is ignored
        out = self.site({"/index.html": page_html(CLEAN_DECK)}, {"robots.txt": "\ufeffUser-agent: *\nDisallow: /\n"})[1]
        self.assertRegex(out, r"(?m)^FAIL /index\.html ROBOTS: ")

    def test_inline_markup_does_not_break_parity(self):
        page = page_html(CLEAN_DECK)
        marked = page.replace("One technician, one", "One <b>technician</b>, one", 1)
        self.assertNotEqual(marked, page)
        out = self.site({"/index.html": marked}, None, "--deck", CLEAN_DECK, "--map", "/index.html=p")[1]
        self.assertNotIn("PARITY", out)

    def test_inline_markup_beside_a_comma_in_a_faq_answer_still_counts_as_on_the_page(self):
        page = page_html(CLEAN_DECK)
        marked = page.replace("<p>A fixed yearly fee per pump, quoted", "<p>A fixed yearly fee per <b>pump</b>, quoted", 1)
        self.assertNotEqual(marked, page)
        out = self.site({"/index.html": marked}, None, "--deck", CLEAN_DECK, "--map", "/index.html=p")[1]
        self.assertNotRegex(out, r"(?m)^FAIL /index\.html FAQ_SCHEMA: .*page text")
        gone = page.replace("<p>A fixed yearly fee per pump, quoted in writing after the report.</p>", "")
        out = self.site({"/index.html": gone}, None, "--deck", CLEAN_DECK, "--map", "/index.html=p")[1]
        self.assertRegex(out, r"(?m)^FAIL /index\.html FAQ_SCHEMA: .*page text")

    def test_input_value_and_logo_alt_count_for_parity(self):
        deck = deck_check.parse_deck(Path(CLEAN_DECK).read_text(encoding="utf-8"))
        label, logo = deck.values["p.cta.button"], deck.values["p.header.logo"]
        page = page_html(CLEAN_DECK)
        logo_img = page.replace("<p>%s</p>" % logo, '<img src="/logo.svg" alt="%s">' % logo, 1)
        button_input = logo_img.replace('<a href="#form">%s</a>' % label, '<input type="submit" value="%s">' % label, 1)
        self.assertNotEqual(page, logo_img)
        self.assertNotEqual(logo_img, button_input)
        out = self.site({"/index.html": button_input}, None, "--deck", CLEAN_DECK, "--map", "/index.html=p")[1]
        self.assertNotIn("PARITY", out)
        typed = page.replace("<p>%s</p>" % logo, '<input type="text" value="%s">' % logo, 1)
        out = self.site({"/index.html": typed}, None, "--deck", CLEAN_DECK, "--map", "/index.html=p")[1]
        self.assertRegex(out, r"(?m)^FAIL /index\.html PARITY: p\.header\.logo")  # a typed-in field's value is not shown text

    def test_a_button_that_does_not_show_the_label_fails_parity(self):
        label = deck_check.parse_deck(Path(CLEAN_DECK).read_text(encoding="utf-8")).values["p.cta.button"]
        page = page_html(CLEAN_DECK)
        wrong = page.replace('<a href="#form">%s</a>' % label, '<a href="#form">Submit</a>', 2)  # the form shows the label once more
        self.assertNotEqual(page, wrong)
        code, out = self.site({"/index.html": wrong}, None, "--deck", CLEAN_DECK, "--map", "/index.html=p")
        self.assertRegex(out, r"(?m)^FAIL /index\.html PARITY: p\.\w+\.cta ")
        self.assertEqual(code, 1, out)

    def test_an_unreadable_page_file_exits_2_without_a_traceback(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        dist = write_site(Path(tmp.name) / "dist", {"/index.html": page_html(CLEAN_DECK)})
        (dist / "index.html").chmod(0)
        self.addCleanup((dist / "index.html").chmod, 0o644)
        code, out = run("--dist", str(dist))
        self.assertEqual(code, 2, out)
        self.assertNotIn("Traceback", out)
        self.assertTrue(out.startswith("site_check: "), out)

    def test_sitemap_index_is_followed_one_level(self):
        files = {"sitemap.xml": None, "sitemap-index.xml": sitemap_index([ORIGIN + "/sitemap-pages.xml"]),
                 "sitemap-pages.xml": urlset([ORIGIN + "/"]),
                 "robots.txt": "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap-index.xml\n" % ORIGIN}
        code, out = self.site({"/index.html": page_html(CLEAN_DECK)}, files)
        self.assertEqual(code, 0, out)
        files["sitemap-pages.xml"] = urlset([ORIGIN + "/other/"])
        out = self.site({"/index.html": page_html(CLEAN_DECK)}, files)[1]
        self.assertIn("SITEMAP", rules_in(out), out)
        files["sitemap-pages.xml"] = sitemap_index([ORIGIN + "/sitemap-deeper.xml"])
        files["sitemap-deeper.xml"] = urlset([ORIGIN + "/"])
        out = self.site({"/index.html": page_html(CLEAN_DECK)}, files)[1]
        self.assertIn("SITEMAP", rules_in(out), out)  # a second level is not read

    def test_a_missing_deck_is_skipped_not_passed(self):
        code, out = self.site({"/index.html": page_html(CLEAN_DECK)})
        self.assertEqual(code, 0, out)
        self.assertRegex(out, r"(?m)^SKIPPED /index\.html PARITY: no --deck")
        self.assertRegex(out, r"(?m)^SKIPPED /index\.html FAQ_SCHEMA: no --deck")

    def test_a_json_ld_block_that_is_not_json_fails_faq_schema(self):
        page = page_html(CLEAN_DECK, body_extra='<script type="application/ld+json">{"@type": </script>')
        out = self.site({"/index.html": page}, None, "--deck", CLEAN_DECK, "--map", "/index.html=p")[1]
        self.assertRegex(out, r"(?m)^FAIL /index\.html FAQ_SCHEMA: a JSON-LD block is not valid JSON")

    def test_a_sitemap_index_that_lists_a_missing_file_fails(self):
        files = {"sitemap.xml": None, "sitemap-index.xml": sitemap_index([ORIGIN + "/sitemap-gone.xml"])}
        out = self.site({"/index.html": page_html(CLEAN_DECK)}, files)[1]
        self.assertRegex(out, r"(?m)^FAIL sitemap-index\.xml SITEMAP: sitemap-index\.xml lists .*sitemap-gone\.xml, which is not in the dist")

    def test_a_sitemap_index_inside_a_sitemap_index_warns(self):
        files = {"sitemap.xml": None, "sitemap-index.xml": sitemap_index([ORIGIN + "/sitemap-pages.xml"]),
                 "sitemap-pages.xml": sitemap_index([ORIGIN + "/sitemap-deeper.xml"])}
        out = self.site({"/index.html": page_html(CLEAN_DECK)}, files)[1]
        self.assertRegex(out, r"(?m)^WARN sitemap-pages\.xml SITEMAP: a sitemap index inside a sitemap index")

    def test_a_sitemap_that_is_not_xml_fails(self):
        out = self.site({"/index.html": page_html(CLEAN_DECK)}, {"sitemap.xml": "<urlset><url>"})[1]
        self.assertRegex(out, r"(?m)^FAIL sitemap\.xml SITEMAP: sitemap\.xml is not valid XML")

    def test_links_to_a_missing_local_file_fail_and_other_links_do_not(self):
        extra = ('<a href="/missing.html">Gone</a><a href="mailto:a@example.test">Mail</a><a href="https://elsewhere.test/x">Out</a>'
                 '<a href="#top">Top</a><a href="/index.html#form">Home</a><a href="tel:+000">Call</a>')
        out = self.site({"/index.html": page_html(CLEAN_DECK, body_extra=extra)})[1]
        links = [l for l in out.splitlines() if " LINK:" in l]
        self.assertEqual(len(links), 1, out)
        self.assertIn("/missing.html", links[0])

    def test_head_rules_fire_on_their_own(self):
        good = page_html(CLEAN_DECK)
        cases = {
            "H1": good.replace("</body>", "<h1>Another</h1></body>"),
            "TITLE": re.sub(r"<title>.*?</title>", "", good),
            "META_DESCRIPTION": re.sub(r'<meta name="description"[^>]*>', "", good),
            "CANONICAL": good.replace('href="%s/"' % ORIGIN, 'href="/"'),
            "ALT": good.replace(' alt="hero picture"', ""),
        }
        for rule, page in cases.items():
            out = self.site({"/index.html": page})[1]
            self.assertIn(rule, rules_in(out), (rule, out))
        out = self.site({"/index.html": re.sub(r'<link rel="canonical"[^>]*>', "", good)})[1]
        self.assertIn("CANONICAL", rules_in(out), out)
        out = self.site({"/index.html": good.replace(' alt="hero picture"', ' alt=""')})[1]
        self.assertNotIn("ALT", rules_in(out), out)  # an empty alt marks a decorative image

    def test_valueless_alt_is_no_alt_fail(self):
        good = page_html(CLEAN_DECK)
        page = good.replace("</body>", '<img src="a.png" alt><img src="b.png" alt=""><img src="c.png"></body>')
        out = self.site({"/index.html": page})[1]
        alts = [l for l in out.splitlines() if " ALT:" in l]
        self.assertEqual(len(alts), 1, out)
        self.assertIn("c.png", alts[0])

    def test_forbidden_words_match_whole_words_case_insensitively(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        forbid = Path(tmp.name) / "forbid.txt"
        forbid.write_text("# words\n\nZorblat\nbad phrase\n", encoding="utf-8")
        for extra, fires in (("<p>Ask about zorblat.</p>", True), ("<p>This is a BAD   phrase.</p>", True),
                             ("<p>Zorblatron is fine.</p>", False)):
            out = self.site({"/index.html": page_html(CLEAN_DECK, body_extra=extra)}, None, "--forbid", str(forbid))[1]
            self.assertEqual("FORBIDDEN" in rules_in(out), fires, (extra, out))
        code, out = self.site({"/index.html": page_html(CLEAN_DECK)}, None, "--forbid", str(Path(tmp.name) / "none.txt"))
        self.assertEqual(code, 2, out)

    def test_visible_text_path_that_is_a_file_exits_2_without_a_traceback(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        blocker = Path(tmp.name) / "text"
        blocker.write_text("a file, not a folder", encoding="utf-8")
        code, out = self.site({"/index.html": page_html(CLEAN_DECK)}, None, "--visible-text", str(blocker))
        self.assertEqual(code, 2, out)
        self.assertNotIn("Traceback", out)
        self.assertIn("cannot write", out)

    def test_visible_text_written_per_page(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        pages = {"/index.html": page_html(CLEAN_DECK), "/about/index.html": page_html(CLEAN_DECK, canonical=ORIGIN + "/about/"),
                 "/team.html": page_html(CLEAN_DECK, canonical=ORIGIN + "/team.html")}
        self.site(pages, None, "--visible-text", str(Path(tmp.name) / "text"))
        written = sorted(p.name for p in (Path(tmp.name) / "text").glob("*.txt"))
        self.assertEqual(written, ["about.txt", "index.txt", "team.txt"])
        text = (Path(tmp.name) / "text" / "index.txt").read_text(encoding="utf-8")
        self.assertIn("Cut unplanned pump downtime by half", text)
        self.assertIn("Example Co, all rights reserved.", text)
        self.assertNotIn("<", text)

    def test_parity_and_placeholder_read_nav_and_footer(self):
        deck = deck_check.parse_deck(Path(CLEAN_DECK).read_text(encoding="utf-8"))
        code, out = self.site({"/index.html": page_html(CLEAN_DECK)}, None, "--deck", CLEAN_DECK, "--map", "/index.html=p")
        self.assertEqual(code, 0, out)  # the header button and the phone sit inside <nav>
        self.assertIn("<nav>", page_html(CLEAN_DECK))
        self.assertIn(deck.values["p.header.phone"], page_html(CLEAN_DECK))
        label = deck.values["p.cta.button"]
        page = page_html(CLEAN_DECK)
        head, nav, rest = re.split(r"(?s)(<nav>.*?</nav>)", page, maxsplit=1)
        one_short = head + nav + rest.replace(">%s<" % label, ">Elsewhere<", 1)  # the nav button is one of the ten
        code, out = self.site({"/index.html": one_short}, None, "--deck", CLEAN_DECK, "--map", "/index.html=p")
        self.assertNotIn("PARITY", out)  # a button inside <nav> counts
        nav_gone = head + nav.replace(">%s<" % label, ">Elsewhere<") + rest.replace(">%s<" % label, ">Elsewhere<", 1)
        code, out = self.site({"/index.html": nav_gone}, None, "--deck", CLEAN_DECK, "--map", "/index.html=p")
        self.assertIn("PARITY", out)  # without the nav button the other nine are one short
        nowhere = head + nav.replace(">%s<" % label, ">Elsewhere<") + rest.replace(">%s<" % label, ">Elsewhere<")
        code, out = self.site({"/index.html": nowhere}, None, "--deck", CLEAN_DECK, "--map", "/index.html=p")
        self.assertRegex(out, r"(?m)^FAIL /index\.html PARITY: p\.header\.cta")
        out = self.site({"/index.html": page_html(CLEAN_DECK, footer="TODO: write the footer")})[1]
        self.assertRegex(out, r"(?m)^FAIL /index\.html PLACEHOLDER: ")
        for word in ("Lorem ipsum dolor", "TBD", "[NEEDED: address]"):
            out = self.site({"/index.html": page_html(CLEAN_DECK, body_extra="<p>%s</p>" % word)})[1]
            self.assertIn("PLACEHOLDER", rules_in(out), (word, out))

    def test_bad_input_exits_2(self):
        for args in ((), ("--dist", "/nonexistent-dir-for-site-check"), ("--url",)):
            code, out = run(*args)
            self.assertEqual(code, 2, (args, out))
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        code, out = run("--dist", tmp.name)
        self.assertEqual((code, out.startswith("site_check: ")), (2, True), out)  # no HTML page in it
        bad = Path(tmp.name) / "pages.json"
        bad.write_text("{not json", encoding="utf-8")
        code, out = self.site({"/index.html": page_html(CLEAN_DECK)}, None, "--pages", str(bad))
        self.assertEqual(code, 2, out)

    def test_a_pages_entry_with_a_wrong_type_is_bad_input(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        listing = Path(tmp.name) / "pages.json"
        entry = {"url": "/index.html", "mode": "search"}
        for label, bad in (("keyword", dict(entry, keyword=5)), ("paid", dict(entry, paid="yes")), ("paid null", dict(entry, paid=None))):
            with self.subTest(label):
                listing.write_text(json.dumps([bad]), encoding="utf-8")
                code, out = self.site({"/index.html": page_html(CLEAN_DECK)}, None, "--pages", str(listing))
                self.assertEqual(code, 2, out)
                self.assertTrue(out.startswith("site_check: "), out)
                self.assertNotIn("Traceback", out)
                self.assertEqual(len(out.strip().splitlines()), 1, out)  # one line saying why, and no row


class _Recorder(BaseHTTPRequestHandler):
    root = None
    seen = []

    def do_GET(self):
        _Recorder.seen.append((self.path, self.headers.get("User-Agent")))
        if self.path == "/services":
            self.send_response(301)
            self.send_header("Location", "/services/")
            self.end_headers()
            return
        if self.path.endswith("/"):
            self.path += "index.html"
        target = Path(_Recorder.root) / self.path.split("?", 1)[0].lstrip("/")
        if target.is_file():
            data = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass


class SiteCheckUrlTests(unittest.TestCase):
    def serve(self, pages):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        _Recorder.root = str(write_site(Path(tmp.name), pages))
        _Recorder.seen = []
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Recorder)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return "http://127.0.0.1:%d" % server.server_address[1]

    def test_url_fetches_send_an_ordinary_chrome_agent(self):
        base = self.serve({"/index.html": page_html(CLEAN_DECK, body_extra='<a href="/missing.html">Gone</a>')})
        url = base + "/index.html"
        code, out = run("--url", url, "--deck", CLEAN_DECK, "--map", "%s=p" % url)
        self.assertTrue(_Recorder.seen)
        self.assertTrue(all(agent == page_facts.CHROME_UA for _, agent in _Recorder.seen), _Recorder.seen)
        self.assertRegex(out, r"(?m)^FAIL \S+/index\.html LINK: .*missing\.html")  # the same-origin link was fetched too
        self.assertRegex(out, r"(?m)^SKIPPED \S+ SITEMAP: ")
        self.assertRegex(out, r"(?m)^SKIPPED \S+ ROBOTS: ")
        self.assertIn("--dist", out)

    def test_live_links_are_read_against_the_address_the_page_ended_on(self):
        good = page_html(CLEAN_DECK, body_extra='<a href="team.html">Team</a>')
        bad = page_html(CLEAN_DECK, body_extra='<a href="nowhere.html">Gone</a>')
        base = self.serve({"/services/index.html": good, "/services/team.html": page_html(CLEAN_DECK)})
        out = run("--url", base + "/services")[1]
        self.assertNotRegex(out, r"(?m)^FAIL \S+ LINK: ", out)  # team.html exists under /services/, the address the fetch ended on
        base = self.serve({"/services/index.html": bad})
        out = run("--url", base + "/services")[1]
        self.assertRegex(out, r"(?m)^FAIL %s/services LINK: nowhere\.html" % re.escape(base), out)  # rows name the asked address

    def test_a_link_to_the_host_the_page_ended_on_is_internal(self):
        fetched = []
        page = site_check.Page("http://example.com/", page_html(CLEAN_DECK))
        page.base = "http://www.example.com/"  # what a redirect from example.com to www.example.com leaves
        problem = site_check.make_internal_link(None, fetched.append)(page, "http://www.example.com/about")
        self.assertEqual((problem, fetched), (None, ["http://www.example.com/about"]))
        fetched.clear()
        site_check.make_internal_link(None, fetched.append)(page, "http://example.com/about")
        self.assertEqual(fetched, [])  # the address that was asked for is no longer the page's own host

    def test_an_unreachable_url_exits_2(self):
        code, out = run("--url", "http://127.0.0.1:1/index.html")
        self.assertEqual(code, 2, out)
        self.assertTrue(out.startswith("site_check: "), out)


if __name__ == "__main__":
    unittest.main()
