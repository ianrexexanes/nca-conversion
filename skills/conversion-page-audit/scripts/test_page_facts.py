import os
import threading
import unittest
import urllib.error
import urllib.request
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import page_facts
from page_facts import extract_facts

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample.html")


def load():
    with open(FIXTURE, encoding="utf-8") as handle:
        return handle.read()


class ExtractFactsTest(unittest.TestCase):
    def setUp(self):
        self.html = load()

    def test_headings_carry_level_and_text_in_document_order(self):
        headings = extract_facts(self.html)["headings"]
        self.assertEqual(headings[0]["level"], 1)
        self.assertEqual([h["level"] for h in headings], [1, 2, 2, 3])

    def test_single_h1_produces_no_heading_note(self):
        notes = extract_facts(self.html)["notes"]
        self.assertFalse(any("h1" in n.lower() for n in notes))

    def test_multiple_h1_is_noted(self):
        html = "<html><body><h1>One</h1><h1>Two</h1></body></html>"
        notes = extract_facts(html)["notes"]
        self.assertTrue(any("h1" in n.lower() for n in notes))

    def test_forms_report_required_fields(self):
        form = extract_facts(self.html)["forms"][0]
        email = [f for f in form["fields"] if f["type"] == "email"][0]
        self.assertTrue(email["required"])

    def test_ctas_extract_exactly_the_cta_like_links(self):
        # Fixture carries two <a> elements written to match CTA_HINTS ("Book a
        # Free Demo" -> "book"/"demo", "Get Started Today" -> "get started")
        # plus one ordinary body link ("Read our full methodology") that
        # matches none of the hints and must not be classified as a CTA.
        ctas = extract_facts(self.html)["ctas"]
        self.assertEqual(len(ctas), 2)
        texts = {c["text"] for c in ctas}
        self.assertEqual(texts, {"Book a Free Demo", "Get Started Today"})
        self.assertNotIn("Read our full methodology", texts)

    def test_jsonld_graph_types_are_flattened(self):
        types = extract_facts(self.html)["schema_types"]
        self.assertIn("Organization", types)
        self.assertIn("FAQPage", types)

    def test_empty_alt_is_distinguished_from_missing_alt(self):
        images = extract_facts(self.html)["images"]
        alts = [img["alt"] for img in images]
        self.assertIn("", alts, "alt='' means decorative and must be preserved as empty string")
        self.assertIn(None, alts, "a missing alt attribute must be None, not ''")

    def test_lcp_candidates_are_document_order_and_flag_early_lazy_image(self):
        # The fixture's first image in document order (the hero image) carries
        # loading="lazy" -- the classic early-LCP-defect pattern, which IS
        # deterministically detectable from static markup even though true LCP
        # identification is not.
        facts = extract_facts(self.html)
        candidates = facts["lcp_candidates"]
        images = facts["images"]
        self.assertEqual(len(candidates), 3, "candidates are capped at 3")
        self.assertEqual(
            [c["src"] for c in candidates],
            [img["src"] for img in images[:3]],
            "lcp_candidates must preserve document order",
        )
        self.assertTrue(any("lazy" in n.lower() for n in facts["notes"]))

    def test_query_string_url_emits_the_schema_caveat(self):
        notes = extract_facts(self.html, url="https://example.com/page?cb=123")["notes"]
        self.assertTrue(any("query string" in n.lower() for n in notes))

    def test_no_schema_found_is_noted_rather_than_silently_empty(self):
        notes = extract_facts("<html><body><p>hi</p></body></html>")["notes"]
        self.assertTrue(any("json-ld" in n.lower() for n in notes))

    def test_svg_title_in_the_body_does_not_replace_the_page_title(self):
        html = ('<html><head><title>Real title</title></head><body>'
                '<a href="/"><svg><title>Logo</title></svg></a></body></html>')
        facts = extract_facts(html)
        self.assertEqual(facts["title"], "Real title")
        self.assertEqual(facts["ctas"], [])

    def test_svg_title_text_goes_nowhere(self):
        html = ('<html><head><title>Real</title></head><body><a href="/"><svg><title>Logo</title></svg></a>'
                '<h2><svg><title>Icon</title></svg>Services</h2></body></html>')
        facts = extract_facts(html)
        self.assertEqual(facts["title"], "Real")
        self.assertEqual([h["text"] for h in facts["headings"]], ["Services"])
        collector = page_facts._Collector()
        collector.feed(html)
        self.assertEqual([link["text"] for link in collector.links], [""])

    def test_a_title_only_inside_an_svg_is_no_page_title(self):
        html = '<html><body><svg><title>Logo</title></svg></body></html>'
        self.assertIsNone(extract_facts(html)["title"])


PAGE = b"<html><head><title>Fixture</title></head><body></body></html>"


class _AgentHandler(BaseHTTPRequestHandler):
    seen = []

    def do_GET(self):
        agent = self.headers.get("User-Agent", "")
        type(self).seen.append(agent)
        if "Python-urllib" in agent:
            self.send_response(403)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(PAGE)))
        self.end_headers()
        self.wfile.write(PAGE)

    def log_message(self, *args):
        pass


class FetchUserAgentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _AgentHandler)
        cls.url = "http://127.0.0.1:%d/" % cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        _AgentHandler.seen.clear()

    def test_server_rejects_python_default_agent(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(self.url)
        self.assertEqual(caught.exception.code, 403)

    def test_fetch_passes_a_server_that_blocks_python_default_agent(self):
        html = page_facts.fetch(self.url)
        self.assertIn("<title>Fixture</title>", html)

    def test_fetch_sends_chrome_ua(self):
        page_facts.fetch(self.url)
        self.assertEqual(_AgentHandler.seen[-1], page_facts.CHROME_UA)


class FetchHelpersTest(unittest.TestCase):
    def test_chrome_major_steps_every_14_days_from_the_anchor(self):
        a = page_facts.ANCHOR_DATE
        self.assertEqual(page_facts.chrome_major(a), page_facts.ANCHOR_MAJOR)
        self.assertEqual(page_facts.chrome_major(a + timedelta(days=13)), page_facts.ANCHOR_MAJOR)
        self.assertEqual(page_facts.chrome_major(a + timedelta(days=14)), page_facts.ANCHOR_MAJOR + 1)
        self.assertEqual(page_facts.chrome_major(a + timedelta(days=56)), page_facts.ANCHOR_MAJOR + 4)
        self.assertEqual(page_facts.chrome_major(a - timedelta(days=100)), page_facts.ANCHOR_MAJOR)

    def test_header_charset_decodes_latin1(self):
        self.assertEqual(page_facts.decode_body("Größe".encode("latin-1"), "iso-8859-1"), "Größe")

    def test_meta_charset_decodes_when_the_header_has_none(self):
        raw = '<meta charset="iso-8859-1"><p>Größe</p>'.encode("latin-1")
        self.assertIn("Größe", page_facts.decode_body(raw, None))

    def test_unknown_charset_falls_back_to_utf8(self):
        self.assertEqual(page_facts.decode_body("Größe".encode("utf-8"), "x-unknown"), "Größe")

    def test_meta_http_equiv_charset_decodes(self):
        raw = '<meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1"><p>Größe</p>'.encode("latin-1")
        self.assertIn("Größe", page_facts.decode_body(raw, None))

    def test_windows_1252_labels_decode_as_windows_1252(self):
        text = "<h1>„Grüße“ – 5 €</h1>"
        raw = text.encode("cp1252")
        for label in ["iso-8859-1", "ISO-8859-1", " latin1 ", "us-ascii", "x-cp1252"]:
            with self.subTest(label=label):
                self.assertEqual(page_facts.decode_body(raw, label), text)
        page = '<meta charset="iso-8859-1">' + text
        self.assertEqual(page_facts.decode_body(page.encode("cp1252"), None), page)

    def test_meta_declared_utf16_or_utf32_reads_as_utf8(self):
        for label in ["utf-16", "utf-32"]:
            with self.subTest(label=label):
                page = '<meta charset="%s"><h1>Grüße</h1>' % label
                self.assertEqual(page_facts.decode_body(page.encode("utf-8"), None), page)

    def test_charset_names_that_cannot_decode_a_page_fall_back(self):
        page = "<h1>Grüße</h1>"
        for name in ["base64", "hex", "rot13", "zlib", "undefined", "idna", "punycode"]:
            with self.subTest(name=name):
                self.assertEqual(page_facts.decode_body(page.encode("utf-8"), name), page)
                tagged = '<meta charset="%s">' % name + page
                self.assertEqual(page_facts.decode_body(tagged.encode("utf-8"), None), tagged)

    def test_unusable_header_charset_falls_through_to_the_meta(self):
        page = '<meta charset="iso-8859-1"><h1>Grüße €</h1>'
        self.assertEqual(page_facts.decode_body(page.encode("cp1252"), "base64"), page)

    def test_file_argument_decodes_its_declared_charset(self):
        import json
        import subprocess
        import sys
        import tempfile
        from pathlib import Path
        html = ('<html><head><meta charset="iso-8859-1"><title>Seite</title></head>'
                '<body><h1>„Grüße“ €</h1></body></html>').encode("cp1252")
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "page.html"
            file.write_bytes(html)
            done = subprocess.run([sys.executable, page_facts.__file__, str(file)], capture_output=True, encoding="utf-8")
        self.assertEqual(done.returncode, 0, done.stderr)
        headings = json.loads(done.stdout)["headings"]
        self.assertIn((1, "„Grüße“ €"), [(h["level"], h["text"]) for h in headings])


    def test_links_list_every_anchor_and_button_unfiltered(self):
        facts = page_facts.extract_facts('<a href="/d"><span>Request my diagnosis</span></a><button>Go on</button>')
        self.assertEqual([(l["text"], l["kind"]) for l in facts["links"]], [("Request my diagnosis", "a"), ("Go on", "button")])
        self.assertEqual(facts["ctas"], [])  # the hint list is unchanged

    def test_headings_and_links_carry_in_footer(self):
        html = '<h2>Top</h2><footer><h2>Company</h2><a href="/i">Imprint</a></footer><div role="contentinfo"><h3>Legal</h3></div>'
        facts = page_facts.extract_facts(html)
        self.assertEqual([h["in_footer"] for h in facts["headings"]], [False, True, True])
        self.assertTrue(facts["links"][0]["in_footer"])
        self.assertTrue(facts["has_footer"])
        self.assertFalse(page_facts.extract_facts("<h2>Top</h2>")["has_footer"])

    def test_unclosed_tag_inside_the_footer_closes_with_it(self):
        html = '<footer><p>Imprint<h2>Company</h2></footer><h2>After</h2>'
        self.assertEqual([h["in_footer"] for h in page_facts.extract_facts(html)["headings"]], [True, False])

    def test_nested_divs_inside_contentinfo(self):
        html = '<div role="contentinfo"><div><h3>Legal</h3></div><h3>More</h3></div><h3>Out</h3>'
        self.assertEqual([h["in_footer"] for h in page_facts.extract_facts(html)["headings"]], [True, True, False])

    def test_unclosed_tag_of_the_scopes_own_name_keeps_the_scope_open(self):
        # A </div> closes the innermost open div, as a browser's parser does, so the contentinfo div stays open.
        html = '<div role="contentinfo"><div><h3>Legal</h3></div><h3>Still inside</h3>'
        self.assertEqual([h["in_footer"] for h in page_facts.extract_facts(html)["headings"]], [True, True])

    def test_result_keys_come_in_the_documented_order(self):
        self.assertEqual(list(page_facts.extract_facts("<h1>A</h1>")), [
            "url", "title", "meta_description", "headings", "links", "has_footer", "ctas", "forms",
            "schema_types", "images", "lcp_candidates", "notes"])

    def test_out_writes_the_printed_json(self):
        import json
        import subprocess
        import sys
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            page = Path(folder) / "page.html"
            page.write_text("<h1>Grüße €</h1><footer><a href='/i'>Imprint</a></footer>", encoding="utf-8")
            out = Path(folder) / "audit-data" / "new" / "facts.json"
            done = subprocess.run([sys.executable, page_facts.__file__, str(page), "--out", str(out)],
                                  capture_output=True, encoding="utf-8")
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(json.loads(out.read_text(encoding="utf-8")), json.loads(done.stdout))
            self.assertEqual(out.read_text(encoding="utf-8").strip(), done.stdout.strip())

    def _decoded(self, head, encoding="cp1252"):
        raw = ("<html><head>%s</head><body><p>Preis: €</p></body></html>" % head).encode(encoding)
        return page_facts.decode_body(raw, None)

    def test_meta_charset_inside_another_attribute_is_not_read(self):
        self.assertIn("€", self._decoded('<meta name="description" content="Our charset=koi8-r guide"><meta charset="windows-1252">'))

    def test_http_equiv_content_type_still_declares_the_charset(self):
        self.assertIn("€", self._decoded('<meta http-equiv="Content-Type" content="text/html; charset=windows-1252">'))

    def test_unusable_meta_charset_passes_to_the_next_meta(self):
        self.assertIn("€", self._decoded('<meta charset="no-such-label"><meta charset="windows-1252">'))

    def test_meta_inside_a_comment_is_not_read(self):
        self.assertIn("€", self._decoded('<!-- <meta charset="windows-1252"> -->', encoding="utf-8"))

    def test_chrome_ua_carries_chrome_major(self):
        self.assertIn("Chrome/%d.0.0.0 " % page_facts.chrome_major(), page_facts.CHROME_UA)


if __name__ == "__main__":
    unittest.main()
