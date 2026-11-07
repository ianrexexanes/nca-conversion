import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import search_check

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "search_check.py"
FIXTURES = HERE / "fixtures"
HOME_URL = "https://harborlane.example/"
SERVICE_URL = "https://harborlane.example/services/bike-repair/"
KEYWORD = "bike repair"


def run(*args):
    done = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    return done.returncode, done.stdout, done.stderr


def audit(fixture, url, *extra):
    code, out, err = run(str(FIXTURES / fixture), "--url", url, "--json", *extra)
    return code, (json.loads(out) if out.strip() else None), err


def check_html(html, keyword=KEYWORD, variants=(), url=HOME_URL):
    facts = search_check.extract_facts(html, url)
    return search_check.check(facts, html, url, keyword, list(variants))


class SearchCheckTests(unittest.TestCase):
    def test_flags_missing_meta_description_and_first_sentence(self):
        code, result, err = audit("search-home.html", HOME_URL, "--keyword", KEYWORD)
        self.assertEqual(code, 0, err)
        places = result["placements"]
        self.assertEqual(places["title"]["status"], "found")
        self.assertEqual(places["h1"]["status"], "found")
        self.assertEqual(places["meta_description"]["status"], "missing")
        self.assertEqual(places["first_sentence"]["status"], "missing")
        self.assertEqual(result["misses"], ["meta_description", "first_sentence"])
        self.assertTrue(result["keyword_confirmed"])

    def test_root_url_slug_not_applicable(self):
        for url in (HOME_URL, "https://harborlane.example"):
            code, result, err = audit("search-home.html", url, "--keyword", KEYWORD)
            self.assertEqual(code, 0, err)
            self.assertEqual(result["placements"]["url_slug"]["status"], "not_applicable", url)
            self.assertNotIn("url_slug", result["misses"], url)

    def test_language_home_slug_not_applicable(self):
        for url in ("https://harborlane.example/en/", "https://harborlane.example/de-ch/"):
            code, result, err = audit("search-home.html", url, "--keyword", KEYWORD)
            self.assertEqual(code, 0, err)
            self.assertEqual(result["placements"]["url_slug"]["status"], "not_applicable", url)

    def test_service_page_slug_found(self):
        code, result, err = audit("search-service.html", SERVICE_URL, "--keyword", KEYWORD)
        self.assertEqual(code, 0, err)
        for name, place in result["placements"].items():
            self.assertEqual(place["status"], "found", name)
        self.assertEqual(result["placements"]["url_slug"]["text"], "/services/bike-repair/")
        self.assertEqual(result["misses"], [])
        code, other, err = audit("search-service.html", "https://harborlane.example/services/", "--keyword", KEYWORD)
        self.assertEqual(other["placements"]["url_slug"]["status"], "missing")
        self.assertEqual(other["misses"], ["url_slug"])

    def test_hyphen_compound_counts_as_keyword(self):
        self.assertEqual(search_check.normalise("Same-Day Bike–Repair"), "same day bike repair")
        self.assertEqual(search_check.normalise("a/b_c «d»"), "a b c d")
        self.assertEqual(search_check.normalise("Straße"), "strasse")
        self.assertFalse(search_check.matches("Bike repairs", [KEYWORD]))
        self.assertTrue(search_check.matches("Standard-Bike-Repair prices", [KEYWORD]))
        self.assertFalse(search_check.matches("Bikerepair prices", [KEYWORD]))
        code, result, err = audit("search-home.html", HOME_URL, "--keyword", KEYWORD)
        h2 = result["placements"]["h2"]
        self.assertEqual(h2["status"], "found")
        self.assertIn("Bike-Repair", h2["text"])

    def test_named_variant_counts_as_keyword(self):
        html = "<html><head><title>Bicycle Repair Shop</title></head><body><h1>Fixes</h1></body></html>"
        self.assertEqual(check_html(html)["placements"]["title"]["status"], "missing")
        with_variant = check_html(html, variants=["bicycle repair"])
        self.assertEqual(with_variant["placements"]["title"]["status"], "found")
        self.assertEqual(with_variant["variants"], ["bicycle repair"])

    def test_heading_counts_reported_never_fail(self):
        code, result, err = audit("search-service.html", SERVICE_URL, "--keyword", KEYWORD, "--variant", "bicycle repair")
        self.assertEqual(code, 0, err)
        self.assertEqual(result["headings"]["h2"], {"total": 3, "exact": 2, "variant": 0})
        self.assertEqual(result["headings"]["h3"], {"total": 3, "exact": 1, "variant": 1})
        self.assertEqual(result["headings"]["h4"], {"total": 1, "exact": 0, "variant": 0})
        self.assertEqual(result["misses"], [])
        stuffed = ("<html><head><title>Bike repair</title></head><body><h1>Bike repair</h1>"
                   + "".join("<h2>Bike repair %d</h2>" % n for n in range(12)) + "</body></html>")
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "stuffed.html"
            page.write_text(stuffed, encoding="utf-8")
            code, out, err = run(str(page), "--url", SERVICE_URL, "--keyword", KEYWORD, "--json")
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["headings"]["h2"], {"total": 12, "exact": 12, "variant": 0})
        body = check_html("<html><body><h1>x</h1><p>Bike repair, bike repair and bicycle repair.</p></body></html>",
                          variants=["bicycle repair"])
        self.assertEqual(body["body_uses"], {"exact": 2, "variant": 1})

    def test_no_keyword_reports_apparent_target(self):
        code, result, err = audit("search-home.html", HOME_URL)
        self.assertEqual(code, 0, err)
        self.assertIsNone(result["keyword"])
        self.assertFalse(result["keyword_confirmed"])
        self.assertEqual(result["apparent_target"], "bike repair")
        for name, place in result["placements"].items():
            self.assertEqual(place["status"], "not_checked", name)
        self.assertEqual(result["placements"]["title"]["text"], "Bike Repair in Harbor Lane | Quick Fixes")
        self.assertEqual(result["misses"], [])
        self.assertEqual(result["headings"]["h2"], {"total": 2, "exact": 0, "variant": 0})
        self.assertEqual(result["body_uses"], {"exact": 0, "variant": 0})
        self.assertTrue(any("not confirmed" in note for note in result["notes"]))
        html = "<html><head><title>Alpha Beta</title></head><body><h1>Gamma Delta</h1></body></html>"
        bare = check_html(html, keyword=None, url=SERVICE_URL)
        self.assertIsNone(bare["apparent_target"])
        self.assertTrue(any("share no topic" in note for note in bare["notes"]))
        self.assertEqual({p["status"] for p in bare["placements"].values()}, {"not_checked"})
        self.assertEqual(bare["misses"], [])

    def test_exit_2_on_bad_arguments(self):
        page = str(FIXTURES / "search-home.html")
        self.assertEqual(run()[0], 2)
        self.assertEqual(run(page, "--no-such-flag")[0], 2)
        self.assertEqual(run(page, "--keyword")[0], 2)

    def test_exit_3_when_the_page_cannot_be_read(self):
        code, out, err = run(str(FIXTURES / "does-not-exist.html"), "--keyword", KEYWORD)
        self.assertEqual(code, 3)
        self.assertIn("could not read", err)

    def test_first_sentence_after_h1_skips_script_and_style(self):
        html = ("<body><p>Before the heading.</p><h1>Bike Repair</h1>"
                "<style>p { color: red; }</style><script>var note = 'Not this one.';</script>"
                "<noscript>Enable scripts.</noscript><svg><text>Icon label.</text></svg>"
                "<p>  Harbor Lane Cycles fixes   bikes\n every day. Second sentence.</p></body>")
        self.assertEqual(search_check.first_sentence_after_h1(html), "Harbor Lane Cycles fixes bikes every day.")
        self.assertIsNone(search_check.first_sentence_after_h1("<body><p>No heading here.</p></body>"))
        self.assertNotIn("Not this one", search_check.visible_text(html))
        self.assertEqual(search_check.visible_text("<nav>Menu</nav><p>Body text.</p><footer>Legal</footer>"), "Body text.")

    def test_text_output_has_one_line_per_placement_and_a_summary(self):
        code, out, err = run(str(FIXTURES / "search-home.html"), "--url", HOME_URL, "--keyword", KEYWORD)
        self.assertEqual(code, 0, err)
        lines = out.strip().splitlines()
        self.assertEqual(len(lines), 7)
        self.assertTrue(lines[0].startswith("FOUND title:"), lines[0])
        self.assertTrue(lines[1].startswith("MISSING meta_description:"), lines[1])
        self.assertTrue(lines[2].startswith("N/A url_slug:"), lines[2])
        self.assertTrue(lines[-1].startswith("search_check: 2 misses of 6 placements"), lines[-1])


class SvgTitleTest(unittest.TestCase):
    def test_title_placement_reads_the_head_title_not_a_logo_svg_title(self):
        page = ('<html><head><title>%s</title></head><body><h1>Welcome</h1>'
                '<a href="/"><svg><title>%s</title></svg></a></body></html>')
        found = check_html(page % ("Bike repair in town", "Harbor Lane logo"))
        self.assertEqual(found["placements"]["title"]["status"], "found")
        missing = check_html(page % ("Harbor Lane", "Bike repair logo"))
        self.assertEqual(missing["placements"]["title"]["status"], "missing")


class RulingsTest(unittest.TestCase):
    def test_normalise_folds_every_dash_and_guillemet_and_drops_invisible_marks(self):
        self.assertEqual(search_check.normalise("Bike—Repair ‹Shop› »Kit«"), "bike repair shop kit")
        self.assertEqual(search_check.normalise("bike\u00a0repair\u2011kit\u2010set\u2012day"), "bike repair kit set day")
        self.assertEqual(search_check.normalise("Fahrrad\u00adreparatur\u200b\ufeff"), "fahrradreparatur")
        self.assertTrue(search_check.matches("Fahrrad\u00adreparatur für Kinder", ["Fahrradreparatur"]))

    def test_matches_takes_terms_literally_and_never_matches_an_empty_term(self):
        self.assertTrue(search_check.matches("Our bike.repair kit", ["bike.repair"]))
        self.assertFalse(search_check.matches("Our bikexrepair kit", ["bike.repair"]))
        self.assertFalse(search_check.matches("Ebike repair", [KEYWORD]))
        self.assertFalse(search_check.matches("Bike repair, today.", ["", " ", "–", "/"]))
        self.assertTrue(search_check.matches("Bike repair", ["", "bike repair"]))

    def test_body_uses_and_headings_count_each_occurrence_once(self):
        html = ("<html><head><title>Bicycle repair</title></head><body><h1>x</h1><h2>Bicycle repair shop</h2>"
                "<p>A bicycle repair, a Bicycle Repair.</p><footer>Bicycle repair</footer></body></html>")
        result = check_html(html, variants=["bicycle repair", "bicycle repair shop", "Bicycle Repair"])
        self.assertEqual(result["body_uses"], {"exact": 0, "variant": 3})
        self.assertEqual(result["headings"]["h2"], {"total": 1, "exact": 0, "variant": 1})
        nested = check_html("<body><h1>x</h1><h2>Bike repair</h2><p>Bike repair and repair.</p></body>", variants=["repair"])
        self.assertEqual(nested["body_uses"], {"exact": 2, "variant": 1})
        self.assertEqual(nested["headings"]["h2"], {"total": 1, "exact": 1, "variant": 0})

    def test_visible_text_survives_void_and_stray_tags_and_skips_the_title(self):
        html = ('<html><head><title>Bike repair</title><meta charset="utf-8"></head><body>'
                '<nav><img src="logo.png" alt=""><br><p>Menu</span> More menu</nav><p>Bike<br>repair today.<p>Open</div> daily.'
                '<footer><input type="email">Legal</footer><p>Call us.</p></body></html>')
        self.assertEqual(search_check.visible_text(html), "Bike repair today. Open daily. Call us.")

    def test_first_sentence_stops_at_a_heading_and_keeps_its_mark(self):
        first = search_check.first_sentence_after_h1
        self.assertIsNone(first("<h1>Bike repair</h1><h2>Prices</h2><p>From today.</p>"))
        self.assertEqual(first("<h1>Bike repair</h1><p>Book a slot</p><h2>Prices</h2>"), "Book a slot")
        self.assertEqual(first("<div><h1>Bike <em>repair</em></div><p>Ready in 2.5 hours! Or less.</p>"), "Ready in 2.5 hours!")

    def test_placement_texts_are_one_line_and_the_slug_is_read_decoded(self):
        html = ("<html><head><title>\n  Bike   Repair\n  Shop </title><meta name=\"description\" content=\" \"></head>"
                "<body><h1>Bike repair</h1><p>We fix bikes.</p></body></html>")
        places = check_html(html, url="https://harborlane.example/services/bike%2Drepair/")["placements"]
        self.assertEqual(places["title"], {"status": "found", "text": "Bike Repair Shop"})
        self.assertEqual(places["meta_description"], {"status": "missing", "text": None})
        self.assertEqual(places["url_slug"], {"status": "found", "text": "/services/bike%2Drepair/"})
        self.assertEqual(places["h2"], {"status": "missing", "text": None})

    def test_command_line_edges(self):
        page = str(FIXTURES / "search-home.html")
        for args in (("--variant", "bicycle repair"), ("--keyword", " "), ("--keyword", KEYWORD, "--variant", "/"),
                     ("--keyword", KEYWORD, "--url", "harborlane.example/")):
            code, out, err = run(page, *args)
            self.assertEqual((code, out), (2, ""), args)
        code, out, err = run(page, "--keyword", KEYWORD, "--json")
        self.assertEqual(code, 0, err)
        result = json.loads(out)
        self.assertEqual(result["url"], "")
        self.assertEqual(result["placements"]["url_slug"], {"status": "not_checked", "text": None})
        self.assertEqual(result["misses"], ["meta_description", "first_sentence"])
        self.assertTrue(any("No address was given" in note for note in result["notes"]))
        with tempfile.TemporaryDirectory() as tmp:
            out_file = Path(tmp) / "audit" / "data" / "search.json"
            code, out, err = run(page, "--url", HOME_URL, "--keyword", KEYWORD, "--out", str(out_file), "--json")
            self.assertEqual(code, 0, err)
            self.assertEqual(out_file.read_text(encoding="utf-8"), out)
            latin = Path(tmp) / "latin.html"
            latin.write_bytes("<title>Fahrräder</title>".encode("latin-1"))
            code, out, err = run(str(latin), "--keyword", KEYWORD)
        self.assertEqual((code, out), (3, ""))
        self.assertTrue(err.startswith("search_check: could not read "), err)
        self.assertNotIn("Traceback", err)

    def test_apparent_target_in_both_modes_and_german_stop_words(self):
        home = (FIXTURES / "search-home.html").read_text(encoding="utf-8")
        self.assertEqual(check_html(home)["apparent_target"], "bike repair")
        german = ("<html><head><title>Fahrrad Reparatur für Kinder | Harbor Lane Cycles</title></head>"
                  "<body><h1>Reparatur für Kinder und Eltern</h1></body></html>")
        self.assertEqual(check_html(german, keyword=None)["apparent_target"], "reparatur kinder")


    def test_heading_counts_skip_footer_headings(self):
        html = ('<title>Bike repair</title><h1>Bike repair today</h1><h2>Bike repair plans</h2><h2>How it works</h2>'
                '<footer><h2>Bike repair company</h2></footer>')
        result = check_html(html)
        self.assertEqual(result["headings"]["h2"]["total"], 2)
        self.assertEqual(result["headings"]["h2"]["exact"], 1)
        self.assertEqual(result["headings_scope"], "above the footer")

    def test_no_footer_element_counts_whole_page_and_says_so(self):
        html = (FIXTURES / "search-divfooter.html").read_text(encoding="utf-8")
        result = check_html(html)
        self.assertEqual(result["headings_scope"], "whole page (no footer element found)")
        self.assertEqual(result["headings"]["h2"]["total"], 3)

    def test_article_footer_page_counts_whole_page_and_says_so(self):
        html = ('<title>Payroll</title><article><h1>Payroll</h1><footer>by me</footer></article><h2>Plans</h2>'
                '<div class="footer"><h2>Contact</h2></div>')
        result = check_html(html)
        self.assertEqual(result["headings_scope"], "whole page (no footer element found)")
        self.assertEqual(result["headings"]["h2"]["total"], 2)

    def test_footer_h2_never_satisfies_the_h2_placement(self):
        html = ('<title>Payroll software</title><h1>Payroll software for restaurants</h1><h2>Plans</h2>'
                '<footer><h2>Payroll software</h2></footer>')
        self.assertEqual(check_html(html, keyword="payroll software")["placements"]["h2"]["status"], "missing")

    def test_footer_h1_is_never_the_h1(self):
        html = '<title>Payroll software</title><h2>Plans</h2><footer><h1>Payroll software</h1></footer>'
        self.assertEqual(check_html(html, keyword="payroll software")["placements"]["h1"], {"status": "missing", "text": None})
        self.assertIsNone(check_html(html, keyword=None)["apparent_target"])

    def test_headings_scope_follows_headings_in_the_result(self):
        keys = list(check_html("<h1>A</h1>"))
        self.assertEqual(keys[keys.index("headings") + 1], "headings_scope")


if __name__ == "__main__":
    unittest.main()
