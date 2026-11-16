import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "wire_check.py"
FIXTURES = HERE / "fixtures"
DECK = str(FIXTURES / "deck-variants.md")
WIRE_A = str(FIXTURES / "wire-clean-a.html")
WIRE_B = str(FIXTURES / "wire-clean-b.html")
WIRE_PLANTED = str(FIXTURES / "wire-planted.html")
SUMMARY_0 = "wire_check: 0 FAIL, 0 WARN"

TINY_DECK = """## p: Tiny page

```copy
p.page.mode: direct
p.cta.button: Book my pump check
p.cta.fud: Free for plants with ten pumps or more.
p.hero.h1: Know which pump fails next
p.hero.cta: Book my pump check
p.hero.visual: A technician beside a pump
```

## Register notes

- None: the register changed no rule.
"""
TINY_FRAME = """<main data-deck="tiny.md" data-ns="p" data-variant="">
<section data-section="p.hero" data-layout="split-media">
<h1 data-key="p.hero.h1">Know which pump fails next</h1>
<a href="#form" data-key="p.hero.cta">Book my pump check</a>
<p data-key="p.cta.fud">Free for plants with ten pumps or more.</p>
<figure data-visual="p.hero.visual">A technician beside a pump</figure>
</section>
</main>
<!--
- hero: split-media, because the hero must name the visitor and the offer at once.
-->
"""


def run(*args):
    done = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    return done.returncode, done.stdout + done.stderr


def read(path):
    return Path(path).read_text(encoding="utf-8")


def element(key, tag="[a-z0-9]+"):
    # the whole line holding the element that carries `key`
    return r'(?m)^[ \t]*<(?P<tag>%s) [^>]*data-key="%s"[^>]*>.*</(?P=tag)>\n' % (tag, re.escape(key))


def replace_once(text, pattern, repl):
    out, n = re.subn(pattern, repl, text, count=1)
    assert n == 1, pattern
    return out


class WireCheckTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.count = 0

    def write(self, text, name="frame.html"):
        self.count += 1
        path = Path(self._tmp.name) / ("%d-%s" % (self.count, name))
        path.write_text(text, encoding="utf-8")
        return str(path)

    def edited(self, path, key, old, new):
        # the frame at `path` with `old` swapped for `new` inside the element carrying `key`
        text = read(path)
        line = re.search(element(key), text).group(0)
        assert old in line, (key, old)
        return self.write(text.replace(line, line.replace(old, new, 1), 1))

    def dropped(self, path, pattern):
        return self.write(replace_once(read(path), pattern, ""))

    def bad(self, *args):
        # bad input: exit 2 and one "wire_check: ..." line saying why, which a missing script cannot print
        code, out = run(*args)
        self.assertEqual(code, 2, out)
        self.assertTrue(out.startswith("wire_check: "), out)
        return out

    def test_clean_wireframe_passes(self):
        self.assertEqual(run(WIRE_A, "--deck", DECK, "--variant", "a"), (0, SUMMARY_0 + "\n"))

    def test_clean_wireframe_for_variant_b_passes(self):
        self.assertEqual(run(WIRE_B, "--deck", DECK, "--variant", "b"), (0, SUMMARY_0 + "\n"))

    def test_changed_text_fails_parity(self):
        edited = self.edited(WIRE_A, "p.hero.a.h1", "downtime", "stoppages")
        code, out = run(edited, "--deck", DECK, "--variant", "a")
        self.assertEqual(code, 1)
        self.assertIn("FAIL p.hero.a.h1 PARITY", out)

    def test_whitespace_alone_is_not_a_change(self):
        edited = self.edited(WIRE_A, "p.hero.a.h1", "pump downtime by half", "pump  downtime\n   by half")
        self.assertEqual(run(edited, "--deck", DECK, "--variant", "a"), (0, SUMMARY_0 + "\n"))

    def test_dropped_key_fails(self):
        dropped = self.dropped(WIRE_A, element("p.pain.h2"))
        code, out = run(dropped, "--deck", DECK, "--variant", "a")
        self.assertEqual(code, 1)
        self.assertIn("FAIL p.pain.h2 MISSING_KEY", out)

    def test_variant_frame_ignores_other_variants_keys(self):
        code, out = run(WIRE_A, "--deck", DECK, "--variant", "a")
        self.assertEqual(code, 0)
        for key in ("p.hero.b.h1", "p.hero.c.h1", "p.cta.hook.b"):
            self.assertNotIn(key, out)

    def test_buttons_carry_the_frames_label(self):
        # frame b: a button showing cta.button's text instead of cta.hook.b's
        edited = self.edited(WIRE_B, "p.proof.cta", "Get my pump service plan", "Book my pump check")
        code, out = run(edited, "--deck", DECK, "--variant", "b")
        self.assertEqual(code, 1)
        self.assertIn("FAIL p.proof.cta PARITY", out)

    def test_the_label_elements_are_optional_but_checked_when_rendered(self):
        extra = '<p data-key="p.cta.hook.a">Book my pump check now</p>\n'
        framed = self.write(read(WIRE_A).replace("</main>", extra + "</main>", 1))
        code, out = run(framed, "--deck", DECK, "--variant", "a")
        self.assertEqual(code, 1)
        self.assertIn("FAIL p.cta.hook.a BUTTON", out)
        framed = self.write(read(WIRE_A).replace("</main>", '<a href="#form" data-key="p.cta.hook.a">Book my pump check</a>\n</main>', 1))
        self.assertIn("FAIL p.cta.hook.a PARITY", run(framed, "--deck", DECK, "--variant", "a")[1])

    def test_section_without_visual_fails(self):
        dropped = self.dropped(WIRE_A, element("p.pain.visual", "figure").replace('data-key', 'data-visual'))
        code, out = run(dropped, "--deck", DECK, "--variant", "a")
        self.assertEqual(code, 1)
        self.assertIn("FAIL p.pain VISUAL", out)

    def test_none_visual_needs_no_figure(self):
        deck = TINY_DECK.replace("```\n\n## Register", "p.pain.h2: Pumps fail without a warning\np.pain.visual: none, the section reads better as plain text\n```\n\n## Register", 1)
        section = '<section data-section="p.pain" data-layout="stacked">\n<h2 data-key="p.pain.h2">Pumps fail without a warning</h2>\n</section>\n'
        frame = TINY_FRAME.replace("</main>", section + "</main>", 1).replace("-->", "- pain: stacked, because the problem reads best as a short line.\n-->", 1)
        self.assertEqual(run(self.write(frame), "--deck", self.write(deck, "deck.md")), (0, SUMMARY_0 + "\n"))
        kept = self.write(deck.replace("none, the section reads better as plain text", "A pump with a cracked seal"), "deck.md")
        self.assertIn("FAIL p.pain VISUAL", run(self.write(frame), "--deck", kept)[1])

    def test_header_and_faq_need_no_visual(self):
        self.assertNotIn("data-visual", "".join(re.findall(r'<section data-section="p\.(?:header|faq)".*?</section>', read(WIRE_A), re.S)))
        self.assertEqual(run(WIRE_A, "--deck", DECK, "--variant", "a")[0], 0)

    def test_visual_box_text_is_checked_against_its_key(self):
        framed = self.write(read(WIRE_A).replace("An idle packing line", "An empty packing line", 1))
        code, out = run(framed, "--deck", DECK, "--variant", "a")
        self.assertEqual(code, 1)
        self.assertIn("FAIL p.pain.visual PARITY", out)

    def test_a_real_image_needs_no_description_text(self):
        text = read(WIRE_A)
        framed = self.write(re.sub(r'(<figure data-visual="p\.pain\.visual">)[^<]*(</figure>)', r'\1<img src="pain.jpg" alt="">\2', text, count=1))
        self.assertEqual(run(framed, "--deck", DECK, "--variant", "a"), (0, SUMMARY_0 + "\n"))

    def test_an_image_can_carry_the_visual_key_itself(self):
        framed = self.write(re.sub(r'<figure data-visual="p\.pain\.visual">[^<]*</figure>', '<img data-visual="p.pain.visual" src="pain.jpg" alt="">',
                                   read(WIRE_A), count=1))
        self.assertEqual(run(framed, "--deck", DECK, "--variant", "a"), (0, SUMMARY_0 + "\n"))

    def test_the_hero_visual_key_is_the_frames_variant_key(self):
        text = read(WIRE_A).replace('data-visual="p.hero.visual"', 'data-visual="p.pain.visual"', 1)
        code, out = run(self.write(text), "--deck", DECK, "--variant", "a")
        self.assertEqual(code, 1)
        self.assertIn("FAIL p.hero VISUAL", out)

    def test_unknown_layout_fails(self):
        framed = self.write(replace_once(read(WIRE_A), r'(data-section="p\.pain" data-layout=")[^"]*"', r'\1carousel"'))
        code, out = run(framed, "--deck", DECK, "--variant", "a")
        self.assertEqual(code, 1)
        self.assertIn("FAIL p.pain LAYOUT", out)

    def test_layout_not_allowed_for_its_section_fails(self):
        framed = self.write(replace_once(read(WIRE_A), r'(data-section="p\.hero" data-layout=")[^"]*"', r'\1logo-strip"'))
        code, out = run(framed, "--deck", DECK, "--variant", "a")
        self.assertEqual(code, 1)
        self.assertIn("FAIL p.hero LAYOUT", out)

    def test_a_section_without_layout_fails(self):
        framed = self.write(replace_once(read(WIRE_A), r'(data-section="p\.pain") data-layout="[^"]*"', r"\1"))
        self.assertIn("FAIL p.pain LAYOUT", run(framed, "--deck", DECK, "--variant", "a")[1])

    def test_cta_as_plain_text_fails(self):
        framed = self.write(replace_once(read(WIRE_A), r'<a href="#form" data-key="p\.proof\.cta">([^<]*)</a>',
                                         r'<span data-key="p.proof.cta">\1</span>'))
        code, out = run(framed, "--deck", DECK, "--variant", "a")
        self.assertEqual(code, 1)
        self.assertIn("FAIL p.proof.cta BUTTON", out)

    def test_a_button_element_counts(self):
        framed = self.write(replace_once(read(WIRE_A), r'<a href="#form" data-key="p\.proof\.cta">([^<]*)</a>',
                                         r'<button data-key="p.proof.cta">\1</button>'))
        self.assertEqual(run(framed, "--deck", DECK, "--variant", "a"), (0, SUMMARY_0 + "\n"))

    def test_text_outside_keys_warns(self):
        h2 = '<h2 data-key="p.pain.h2">'
        framed = self.write(read(WIRE_A).replace(h2, "<p>Loose words with no key</p>\n  " + h2, 1))
        code, out = run(framed, "--deck", DECK, "--variant", "a")
        self.assertEqual(code, 0)
        self.assertIn("WARN p.pain EXTRA_TEXT", out)
        self.assertTrue(out.endswith("wire_check: 0 FAIL, 1 WARN\n"), out)

    def test_variant_must_match_main(self):
        out = self.bad(WIRE_A, "--deck", DECK, "--variant", "b")
        self.assertIn("data-variant", out)
        self.assertNotIn("PARITY", out)

    def test_a_variant_the_deck_lacks_is_bad_input(self):
        self.assertIn("not a variant", self.bad(WIRE_A, "--deck", DECK, "--variant", "z"))

    def test_a_deck_with_variants_needs_the_flag(self):
        self.assertIn("--variant", self.bad(WIRE_A, "--deck", DECK))

    def test_a_deck_with_one_variant_needs_no_flag(self):
        deck, frame = self.write(TINY_DECK, "deck.md"), self.write(TINY_FRAME)
        self.assertEqual(run(frame, "--deck", deck), (0, SUMMARY_0 + "\n"))

    def test_notes_family_differs_from_layout_fails(self):
        framed = self.write(replace_once(read(WIRE_A), r'(data-section="p\.faq" data-layout=")accordion"', r'\1stacked"'))
        code, out = run(framed, "--deck", DECK, "--variant", "a")
        self.assertEqual(code, 1)
        self.assertIn("FAIL p.faq NOTES: notes say accordion, the frame says stacked", out)
        self.assertTrue(out.endswith("wire_check: 1 FAIL, 0 WARN\n"), out)

    def test_section_without_notes_line_warns(self):
        framed = self.write(replace_once(read(WIRE_A), r"(?m)^- faq: .*\n", ""))
        code, out = run(framed, "--deck", DECK, "--variant", "a")
        self.assertEqual(code, 0, out)
        self.assertIn("WARN p.faq NOTES", out)
        self.assertTrue(out.endswith("wire_check: 0 FAIL, 1 WARN\n"), out)
        bare = self.write(replace_once(read(WIRE_A), r"(?s)<!--\n- header.*?-->\n", ""))
        code, out = run(bare, "--deck", DECK, "--variant", "a")
        self.assertEqual(code, 0, out)
        self.assertRegex(out, r"(?m)^WARN \S+ NOTES: no comment after </main>")
        self.assertTrue(out.endswith("wire_check: 0 FAIL, 1 WARN\n"), out)

    def test_ruling_lines_are_not_section_notes(self):
        ruling = ("- Impeccable eyebrow ban: the line above the H1 stays, because the visitor asks who the page is for; mode search.\n"
                  "- Hallmark Floor rule on eyebrows: stacked, because the answer comes first; mode direct.\n")
        text = replace_once(read(WIRE_A), r"(?m)^- faq: .*\n", ruling)
        code, out = run(self.write(text), "--deck", DECK, "--variant", "a")
        self.assertEqual(code, 0, out)
        self.assertEqual(out.count("NOTES"), 1, out)  # the faq line is gone; the ruling lines add no row of their own
        self.assertIn("WARN p.faq NOTES", out)

    def test_matching_notes_pass(self):
        for wire, variant in ((WIRE_A, "a"), (WIRE_B, "b")):
            self.assertEqual(run(wire, "--deck", DECK, "--variant", variant), (0, SUMMARY_0 + "\n"))
        full = replace_once(read(WIRE_A), r"(?m)^- hero: ", "- p.hero: ")  # the full data-section value names a section too
        self.assertEqual(run(self.write(full), "--deck", DECK, "--variant", "a"), (0, SUMMARY_0 + "\n"))
        inside = read(WIRE_A).replace("</main>\n", "", 1).replace("</body>", "</main>\n</body>", 1)  # notes before </main> are no notes
        code, out = run(self.write(inside), "--deck", DECK, "--variant", "a")
        self.assertIn("NOTES: no comment after </main>", out)

    def test_unreadable_input_is_bad_input(self):
        self.bad(str(FIXTURES / "no-such-file.html"), "--deck", DECK, "--variant", "a")
        self.bad(WIRE_A, "--deck", str(FIXTURES / "no-such-deck.md"), "--variant", "a")
        self.bad(self.write("<p>no main here</p>"), "--deck", DECK, "--variant", "a")

    def test_the_planted_fixture_trips_every_rule(self):
        code, out = run(WIRE_PLANTED, "--deck", DECK, "--variant", "a")
        self.assertEqual(code, 1)
        for line in ("FAIL p.hero.a.h1 PARITY", "FAIL p.pain.h2 MISSING_KEY", "FAIL p.pain VISUAL", "FAIL p.proof LAYOUT",
                     "FAIL p.guarantee LAYOUT", "FAIL p.proof.cta BUTTON", "FAIL p.value.cta PARITY", "WARN p.how EXTRA_TEXT"):
            self.assertIn(line, out)

    def test_json_output(self):
        code, out = run(WIRE_PLANTED, "--deck", DECK, "--variant", "a", "--json")
        data = json.loads(out)
        self.assertEqual(code, 1)
        self.assertEqual({r["rule"] for r in data["findings"]}, {"PARITY", "MISSING_KEY", "VISUAL", "LAYOUT", "BUTTON", "EXTRA_TEXT"})
        self.assertEqual(data["warn"], 1)
        self.assertEqual(data["fail"], len([r for r in data["findings"] if r["level"] == "FAIL"]))


if __name__ == "__main__":
    unittest.main()
