import os
import unittest

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


if __name__ == "__main__":
    unittest.main()
