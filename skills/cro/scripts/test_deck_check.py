import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

import deck_check

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "deck_check.py"
FIXTURES = HERE / "fixtures"
FOLLOW = ("BUTTON_GAP", "CLOSER_PARTS", "VISUAL_MISSING", "PAIN_ORDER", "HEADER_EXITS", "VALUE_BLOCKS", "FAQ_PAIRS")


def read(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def findings(text, part="page", final=False):
    return deck_check.check(deck_check.parse_deck(text), part, final)


def fails(text, part="page", final=False):
    return {f[2] for f in findings(text, part, final) if f[0] == "FAIL"}


def warns(text, part="page", final=False):
    return {f[2] for f in findings(text, part, final) if f[0] == "WARN"}


def rules(text, part="page", final=False):
    return {f[2] for f in findings(text, part, final)}


def level_of(rule, text, part="page", final=False):
    for f in findings(text, part, final):
        if f[2] == rule:
            return f[0]
    return None


def details(rule, text, part="page", final=False):
    return [f[3] for f in findings(text, part, final) if f[2] == rule]


def value_of(text, key):
    m = re.search(r"(?m)^%s: (.*)$" % re.escape(key), text)
    assert m, key
    return m.group(1)


def with_line(text, key, value):
    out, n = re.subn(r"(?m)^%s: .*$" % re.escape(key), lambda m: "%s: %s" % (key, value), text)
    assert n == 1, (key, n)
    return out


def drop_line(text, key):
    return re.sub(r"(?m)^%s: .*\n" % re.escape(key), "", text)


def add_line(text, line):
    start = text.index("```copy\n")
    end = text.index("\n```\n", start + 8)
    return text[:end] + "\n" + line + text[end:]


def with_button(label, mode="direct"):
    name = "deck-clean-search.md" if mode == "search" else "deck-clean-direct.md"
    text = read(name)
    return with_line(text, "p.cta.button", label)


def with_hook(v, label):
    return with_line(read("deck-variants.md"), "p.cta.hook." + v, label)


def with_h1(text, mode):
    name = "deck-clean-search.md" if mode == "search" else "deck-clean-direct.md"
    return with_line(read(name), "p.hero.h1", text)


def with_blocks(text, n):
    text = re.sub(r"(?m)^p\.value\.block\d+: .*\n", "", text)
    for i in range(1, n + 1):
        text = add_line(text, "p.value.block%d: Block %d of the pump service" % (i, i))
    return text


def hero_only(text, keep_visual=True):
    out, fence = [], False
    for line in text.split("\n"):
        if line.strip() == "```copy":
            fence = True
        elif line.strip() == "```":
            fence = False
        elif fence:
            m = deck_check.KEY_LINE.match(line)
            if m:
                parts = m.group("key").split(".")
                if parts[1] not in ("page", "meta", "cta", "hero"):
                    continue
                if not keep_visual and parts[-1] == "visual":
                    continue
        out.append(line)
    return "\n".join(out)


def run(*args):
    done = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    return done.returncode, done.stdout, done.stderr


class DeckCheckTest(unittest.TestCase):
    def test_parse_keys_namespace_and_duplicates(self):
        d = deck_check.parse_deck("## p: Page\n```copy\np.page.mode: direct\nq.page.role: landing\np.page.mode: search\n```\n")
        self.assertEqual(d.values["p.page.mode"], "direct")
        self.assertEqual({e[1] for e in d.errors}, {"KEY_NAMESPACE", "DUPLICATE_KEY"})

    def test_every_slot_name_parses_as_a_key(self):
        d = deck_check.parse_deck("## p: Page\n```copy\np.hero.prooftop: x\np.hero.a.strip: y\np.cta.hook.a: Book my pump check\np.faq.q1: z\n```\n")
        self.assertEqual(d.errors, [])
        self.assertEqual(d.values["p.hero.prooftop"], "x")
        self.assertEqual(d.order, ["p.hero.prooftop", "p.hero.a.strip", "p.cta.hook.a", "p.faq.q1"])
        self.assertEqual(d.headings, ["## p: Page"])

    def test_two_copy_fences_in_one_section_is_a_syntax_error(self):
        self.assertIn("DECK_SYNTAX", fails("## p: Page\n```copy\np.page.mode: direct\n```\n\n```copy\np.page.role: landing\n```\n"))

    def test_clean_decks_have_no_fail(self):
        for name in ("deck-clean-direct.md", "deck-clean-search.md", "deck-variants.md"):
            self.assertEqual(fails(read(name)), set(), name)
            self.assertEqual(findings(read(name), final=True), [], name)

    def test_each_planted_rule_fires(self):
        self.assertTrue({"DECK_SYNTAX", "META", "ONE_ACTION", "BUTTON_GAP", "BUTTON_WORDS", "BUTTON_GENERIC", "FUD_MISSING",
                         "PROOF_SLOTS", "VISUAL_MISSING", "HEADLINE_LENGTH", "BENEFIT_LINES", "CLOSER_PARTS", "PAIN_ORDER",
                         "HEADER_EXITS", "FAQ_PAIRS", "SEARCH_PLACEMENT", "REGISTER_NOTES"} <= fails(read("deck-planted.md"), final=True))

    def test_planted_deck_also_fires_the_other_rules(self):
        deck = read("deck-planted.md")
        self.assertTrue({"KEY_NAMESPACE", "DUPLICATE_KEY", "PLACEHOLDER"} <= fails(deck, final=True))
        self.assertTrue({"VISUAL_STOCK", "VALUE_BLOCKS"} <= warns(deck, final=True))
        self.assertNotIn("VISUAL_STOCK", fails(deck, final=True))
        self.assertNotIn("VALUE_BLOCKS", fails(deck, final=True))

    def test_generic_labels_fail_in_four_languages(self):
        for label in ("Submit", "Contact us", "Contact us today", "Learn more", "Get started", "Let’s talk", "Buy now",
                      "Absenden", "Jetzt kaufen", "Mehr erfahren", "Envoyer", "En savoir plus", "Invia", "Scopri di più",
                      "Learn more.", "Heute anmelden", "Contattaci subito", "Ora acquista", "Contactez-nous maintenant"):
            self.assertIn("BUTTON_GENERIC", fails(with_button(label)), label)
        self.assertNotIn("BUTTON_GENERIC", fails(with_button("Book my pump check")))
        self.assertNotIn("BUTTON_GENERIC", fails(with_button("Book my free pump check today")))

    def test_button_word_count_bands(self):
        for label, level in (("Start", "FAIL"), ("Book inspection", None), ("Book my free pump check", None),
                             ("See which of my pumps fail", "WARN"), ("See which of my pumps need service", "WARN"),
                             ("See which of my pumps need a service", "FAIL")):
            self.assertEqual(level_of("BUTTON_WORDS", with_button(label)), level, label)

    def test_variant_labels_one_per_variant(self):
        deck = read("deck-variants.md")
        self.assertEqual(fails(deck), set())
        self.assertIn("ONE_ACTION", fails(with_line(deck, "p.hero.b.cta", value_of(deck, "p.cta.hook.a"))))
        self.assertIn("ONE_ACTION", fails(add_line(deck, "p.cta.hook.d: Book my pump audit")))
        self.assertEqual(level_of("BUTTON_WORDS", with_hook("b", "See which of my pumps need a service")), "FAIL")
        self.assertIn("BUTTON_GENERIC", fails(with_hook("a", "Learn more")))
        self.assertEqual(deck_check.parse_deck(deck).variants("p"), ["a", "b", "c"])
        d = deck_check.parse_deck(deck)
        self.assertEqual(d.label("p", "a"), value_of(deck, "p.cta.hook.a"))
        self.assertEqual(d.label("p", "c"), value_of(deck, "p.cta.button"))

    def test_shared_slot_satisfies_every_variant(self):
        deck = read("deck-variants.md")
        self.assertNotIn("PROOF_SLOTS", fails(deck))
        d = deck_check.parse_deck(deck)
        self.assertEqual(d.slot("p", "b", "strip"), value_of(deck, "p.hero.strip"))
        self.assertEqual(d.slot("p", "b", "h1"), value_of(deck, "p.hero.b.h1"))
        self.assertIsNone(d.slot("p", "b", "nothing"))
        self.assertIn("PROOF_SLOTS", fails(drop_line(deck, "p.hero.strip")))

    def test_button_gap_two_sections_in_a_row(self):
        deck = read("deck-clean-direct.md")
        self.assertNotIn("BUTTON_GAP", fails(drop_line(deck, "p.value.cta")))
        both = drop_line(drop_line(deck, "p.value.cta"), "p.compare.cta")
        self.assertEqual([f[1] for f in findings(both) if f[2] == "BUTTON_GAP"], ["p.compare"])
        self.assertIn("p.hero", [f[1] for f in findings(drop_line(deck, "p.hero.cta")) if f[2] == "BUTTON_GAP"])
        self.assertEqual([f[1] for f in findings(drop_line(deck, "p.closer.cta")) if f[2] == "BUTTON_GAP"], ["p.closer"])

    def test_headline_ladder_bands(self):
        for n, search, direct in ((50, None, None), (51, "WARN", None), (90, "WARN", None), (91, "FAIL", "WARN")):
            self.assertEqual(level_of("HEADLINE_LENGTH", with_h1("x" * n, "search")), search, n)
            self.assertEqual(level_of("HEADLINE_LENGTH", with_h1("x" * n, "direct")), direct, n)

    def test_benefit_lines(self):
        direct = read("deck-clean-direct.md")
        five = direct
        for i in range(1, 6):
            five = re.sub(r"(?m)^p\.hero\.benefit%d: .*\n" % i, "", five)
        for i in range(1, 6):
            five = add_line(five, "p.hero.benefit%d: Benefit line %d for the pump service" % (i, i))
        self.assertNotIn("BENEFIT_LINES", rules(five))
        self.assertIn("BENEFIT_LINES", fails(add_line(five, "p.hero.benefit6: One line too many")))
        search = read("deck-clean-search.md")
        self.assertNotIn("BENEFIT_LINES", rules(search))
        self.assertIn("BENEFIT_LINES", fails(add_line(search, "p.hero.benefit1: A benefit line on a search page")))

    def test_pain_order_follows_awareness(self):
        direct, search = read("deck-clean-direct.md"), read("deck-clean-search.md")
        self.assertNotIn("PAIN_ORDER", rules(direct))
        self.assertNotIn("PAIN_ORDER", rules(search))
        self.assertIn("PAIN_ORDER", fails(with_line(direct, "p.page.awareness", "warm")))
        self.assertIn("PAIN_ORDER", fails(with_line(search, "p.page.awareness", "cold")))

    def test_header_exits_on_a_landing_page_only(self):
        self.assertIn("HEADER_EXITS", fails(add_line(read("deck-clean-direct.md"), "p.header.nav: Home; Services; Contact")))
        search = read("deck-clean-search.md")
        self.assertIn("p.header.nav", search)
        self.assertNotIn("HEADER_EXITS", rules(search))

    def test_value_blocks_warn_outside_four_to_eight(self):
        deck = read("deck-clean-direct.md")
        for n, level in ((3, "WARN"), (4, None), (8, None), (9, "WARN")):
            self.assertEqual(level_of("VALUE_BLOCKS", with_blocks(deck, n)), level, n)
        self.assertNotIn("VALUE_BLOCKS", fails(with_blocks(deck, 3)))

    def test_faq_pairs(self):
        deck = read("deck-clean-direct.md")
        self.assertNotIn("FAQ_PAIRS", rules(deck))
        self.assertIn("FAQ_PAIRS", fails(drop_line(deck, "p.faq.a2")))
        self.assertIn("FAQ_PAIRS", fails(drop_line(deck, "p.faq.q2")))
        self.assertIn("FAQ_PAIRS", fails(drop_line(drop_line(deck, "p.faq.q2"), "p.faq.a2")))

    def test_search_placements_on_a_deck(self):
        deck = read("deck-clean-search.md")
        self.assertNotIn("SEARCH_PLACEMENT", rules(deck))
        bad = with_line(deck, "p.meta.title", "Payroll that runs itself")
        self.assertTrue(any("title" in d for d in details("SEARCH_PLACEMENT", bad)))
        slug = with_line(deck, "p.meta.slug", "pay")
        self.assertTrue(any("slug" in d for d in details("SEARCH_PLACEMENT", slug)))
        home = with_line(with_line(deck, "p.page.role", "homepage"), "p.meta.slug", "/")
        self.assertFalse(any("slug" in d for d in details("SEARCH_PLACEMENT", home)))
        by_variant = with_line(deck, "p.meta.title", "Payroll for restaurants, done in a day")
        self.assertNotIn("SEARCH_PLACEMENT", rules(by_variant))
        self.assertTrue(any("answer" in d for d in details("SEARCH_PLACEMENT", with_line(deck, "p.hero.answer", "We do it for you."))))
        no_h2 = re.sub(r"(?m)^p\.[a-z0-9]+\.h2: .*\n", "", deck)
        self.assertTrue(any("H2" in d for d in details("SEARCH_PLACEMENT", no_h2)))
        direct = read("deck-clean-direct.md")
        self.assertNotIn("SEARCH_PLACEMENT", rules(with_line(direct, "p.meta.title", "Anything")))

    def test_shared_answer_serves_every_lettered_h1(self):
        two = drop_line(read("deck-clean-search.md"), "p.hero.h1")
        two = add_line(two, "p.hero.a.h1: Restaurant payroll software that runs itself")
        two = add_line(two, "p.hero.b.h1: Payroll for restaurants, done in minutes")
        self.assertEqual(deck_check.parse_deck(two).variants("p"), ["a", "b"])
        self.assertNotIn("SEARCH_PLACEMENT", rules(two))
        bad = with_line(two, "p.hero.answer", "We read your timesheets and split the tips.")
        self.assertTrue(any("answer" in d for d in details("SEARCH_PLACEMENT", bad)))
        self.assertEqual({f[1] for f in findings(bad) if f[2] == "SEARCH_PLACEMENT" and "answer" in f[3]}, {"p.hero.answer"})
        gone = drop_line(two, "p.hero.answer")
        self.assertEqual({f[1] for f in findings(gone) if f[2] == "SEARCH_PLACEMENT" and "answer" in f[3]},
                         {"p.hero.a.answer", "p.hero.b.answer"})

    def test_hyphen_compound_counts_on_a_deck(self):
        deck = with_h1("Restaurant-Payroll-Software for busy kitchens", "search")
        self.assertFalse(any("H1" in d for d in details("SEARCH_PLACEMENT", deck)))
        self.assertFalse(any("H1" in d for d in details("SEARCH_PLACEMENT", with_h1("Payroll for restaurants soon", "search"))))
        self.assertTrue(any("H1" in d for d in details("SEARCH_PLACEMENT", with_h1("Pay your kitchen team in minutes", "search"))))

    def test_empty_proof_slot_is_flagged_not_filled(self):
        deck = with_line(read("deck-clean-direct.md"), "p.hero.prooftop", "[NEEDED: a client rating]")
        self.assertEqual(level_of("PLACEHOLDER", deck), "WARN")
        self.assertNotIn("PROOF_SLOTS", rules(deck))
        self.assertIn("PROOF_SLOTS", fails(drop_line(read("deck-clean-direct.md"), "p.hero.prooftop")))

    def test_placeholder_fails_with_final(self):
        deck = with_line(read("deck-clean-direct.md"), "p.hero.strip", "[OWNER: reply time]")
        self.assertEqual(level_of("PLACEHOLDER", deck), "WARN")
        self.assertEqual(level_of("PLACEHOLDER", deck, final=True), "FAIL")
        self.assertEqual(level_of("PLACEHOLDER", with_line(read("deck-clean-direct.md"), "p.hero.strip", "[OWNER]"), final=True), "FAIL")
        self.assertIsNone(level_of("PLACEHOLDER", with_line(read("deck-clean-direct.md"), "p.hero.strip", "See [below] for terms")))
        self.assertEqual([f[1] for f in findings(deck) if f[2] == "PLACEHOLDER"], ["p.hero.strip"])

    def test_not_established_counts_as_a_gap(self):
        deck = with_line(read("deck-clean-direct.md"), "p.hero.h1", "NOT ESTABLISHED: a figure from the brief")
        self.assertEqual(level_of("PLACEHOLDER", deck), "WARN")
        self.assertEqual(level_of("PLACEHOLDER", deck, final=True), "FAIL")

    def test_visual_stock_warns(self):
        deck = read("deck-clean-direct.md")
        for text in ("Stock photo of a pump hall", "A real plant, not stock"):
            bad = with_line(deck, "p.hero.visual", text)
            self.assertEqual(level_of("VISUAL_STOCK", bad), "WARN", text)
            self.assertEqual(level_of("VISUAL_STOCK", hero_only(bad), "hero"), "WARN", text)
        self.assertIsNone(level_of("VISUAL_STOCK", with_line(deck, "p.hero.visual", "The stockroom shelf of spare seals")))

    def test_register_notes_line_forms(self):
        deck = read("deck-clean-direct.md")
        head = deck.index("## Register notes")
        body = deck[:head]
        self.assertEqual(level_of("REGISTER_NOTES", body), "FAIL")
        self.assertEqual(level_of("REGISTER_NOTES", body + "## Register notes\n\n- Tone: friendlier\n"), "WARN")
        self.assertIsNone(level_of("REGISTER_NOTES", body + "## Register notes\n\n- Urgency: dropped the date, because the client does not run offers.\n"))
        self.assertIsNone(level_of("REGISTER_NOTES", body + "## Register notes\n\n- None: the register changed no rule.\n"))

    def test_part_hero_skips_the_sequence_rules(self):
        deck = read("deck-clean-direct.md")
        short = hero_only(drop_line(deck, "p.hero.cta"), keep_visual=False)
        self.assertEqual(rules(short, "hero") & set(FOLLOW), set())
        self.assertTrue({"CLOSER_PARTS", "VISUAL_MISSING", "BUTTON_GAP"} <= rules(short, "page"))
        self.assertEqual(findings(hero_only(deck), "hero", final=True), [])
        self.assertEqual(level_of("VALUE_BLOCKS", hero_only(deck), "page"), "WARN")
        self.assertIsNone(level_of("VALUE_BLOCKS", hero_only(deck), "hero"))
        full = with_blocks(deck, 3)
        self.assertIn("VALUE_BLOCKS", rules(full, "page"))
        self.assertNotIn("VALUE_BLOCKS", rules(hero_only(full), "hero"))
        search = re.sub(r"(?m)^p\.[a-z0-9]+\.h2: .*\n", "", hero_only(read("deck-clean-search.md")))
        self.assertFalse(any("H2" in d for d in details("SEARCH_PLACEMENT", search, "hero")))
        self.assertTrue(any("H2" in d for d in details("SEARCH_PLACEMENT", search, "page")))

    def test_cli_exit_codes_and_summary_line(self):
        code, out, err = run(str(FIXTURES / "deck-clean-direct.md"))
        self.assertEqual((code, out.strip().splitlines()[-1]), (0, "deck_check: 0 FAIL, 0 WARN"), err)
        code, out, err = run(str(FIXTURES / "deck-planted.md"), "--final")
        lines = out.strip().splitlines()
        self.assertEqual(code, 1, err)
        self.assertRegex(lines[-1], r"^deck_check: [1-9]\d* FAIL, \d+ WARN$")
        for line in lines[:-1]:
            self.assertRegex(line, r"^(FAIL|WARN) \S+ [A-Z_]+: .+")
        self.assertEqual(run(str(FIXTURES / "missing.md"))[0], 2)
        self.assertEqual(run()[0], 2)
        self.assertEqual(run(str(FIXTURES / "deck-clean-direct.md"), "--part", "bad")[0], 2)
        bad = FIXTURES.parent / "not-utf8.tmp"
        bad.write_bytes(b"\xff\xfe\x00")
        try:
            self.assertEqual(run(str(bad))[0], 2)
        finally:
            bad.unlink()

    def test_cli_json_prints_only_the_object(self):
        code, out, err = run(str(FIXTURES / "deck-planted.md"), "--json")
        data = json.loads(out)
        self.assertEqual(code, 1, err)
        self.assertEqual(set(data), {"findings", "fail", "warn"})
        self.assertEqual(set(data["findings"][0]), {"level", "key", "rule", "detail"})
        self.assertEqual(data["fail"], sum(1 for f in data["findings"] if f["level"] == "FAIL"))
        code, out, _ = run(str(FIXTURES / "deck-clean-search.md"), "--json", "--final")
        self.assertEqual((code, json.loads(out)), (0, {"findings": [], "fail": 0, "warn": 0}))

    def test_runs_from_any_folder_isolated(self):
        done = subprocess.run([sys.executable, "-I", str(SCRIPT), str(FIXTURES / "deck-variants.md")], capture_output=True, text=True, cwd="/")
        self.assertEqual(done.returncode, 0, done.stderr)


if __name__ == "__main__":
    unittest.main()
