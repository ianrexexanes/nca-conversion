import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import compare  # noqa: E402

FIX = HERE / "fixtures"
BEFORE, AFTER, SEARCH = FIX / "audit-before", FIX / "audit-after", FIX / "audit-search"
OLD_A, OLD_B = FIX / "audit-old-a", FIX / "audit-old-b"


def run(before, after, *extra):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = compare.main([str(before), str(after), *extra])
        except SystemExit as exc:
            code = exc.code
        except Exception as exc:  # a traceback is a failed assertion on the exit code, not an error
            code = f"traceback: {type(exc).__name__}"
    return code, out.getvalue().splitlines(), err.getvalue().splitlines()


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

    def variant(self, source, name, **edits):
        """Copy a fixture folder and change files: edits maps file name to a function that edits the loaded JSON."""
        dest = self.tmp / name
        shutil.copytree(source, dest)
        for file_name, fn in edits.items():
            path = dest / file_name
            data = json.loads(path.read_text())
            fn(data)
            path.write_text(json.dumps(data))
        return dest

    def lines(self, before, after):
        code, out, err = run(before, after)
        self.assertEqual(code, 0, err)
        return out


class CompareTests(Base):
    def test_deltas_for_factors_scored_on_both_sides(self):
        lines = self.lines(BEFORE, AFTER)
        self.assertEqual(lines[0], "Before: 37/100, based on the 9 factors that could be checked.")
        self.assertEqual(lines[1], "After: 46/100, based on all 10 factors.")
        self.assertIn("Factor 3 (Does it work?): 3 -> 5, +2", lines)
        self.assertIn("Factor 1 (What's in it for me?): 4 -> 5, +1", lines)
        self.assertIn("Factor 2 (Is it for me?): 5 -> 5, +0", lines)
        self.assertEqual([l for l in lines if l.startswith("Factor ")].__len__(), 10)
        self.assertFalse([l for l in lines if "total" in l.lower()])

    def test_factor_scored_on_one_side_is_not_compared(self):
        lines = self.lines(BEFORE, AFTER)
        self.assertIn("Factor 8 (The form and what happens after it): not compared: scored on one side", lines)
        self.assertFalse([l for l in lines if l.startswith("Factor 8") and "->" in l])
        both_off = self.variant(AFTER, "after-off", **{"score.json": lambda d: d["factors"][7].update(score=None, not_checked="No form here.")})
        del_ev = json.loads((both_off / "score.json").read_text())
        del_ev["factors"][7].pop("evidence", None)
        (both_off / "score.json").write_text(json.dumps(del_ev))
        self.assertIn("Factor 8 (The form and what happens after it): not scored on either side", self.lines(BEFORE, both_off))

    def test_mode_change_is_a_new_baseline(self):
        after = self.variant(AFTER, "after-search", **{"score.json": lambda d: d.update(mode="search", page_role="homepage")})
        lines = self.lines(BEFORE, after)
        self.assertEqual(lines[:2], [
            "New baseline: mode changed from direct to search; no before and after.",
            "New baseline: page_role changed from landing to homepage; no before and after.",
        ])
        self.assertFalse([l for l in lines if l.startswith(("Factor ", "Before:", "After:", "Anchors"))])
        only_role = self.variant(AFTER, "after-role", **{"score.json": lambda d: d.update(page_role="service")})
        lines = self.lines(BEFORE, only_role)
        self.assertEqual(lines[0], "New baseline: page_role changed from landing to service; no before and after.")
        self.assertFalse([l for l in lines if l.startswith("New baseline: mode")])

    def test_speed_compared_only_for_the_same_source(self):
        lines = self.lines(BEFORE, AFTER)
        self.assertIn("Speed mobile performance: 54 -> 68, +14", lines)
        self.assertIn("Speed mobile lcp_s: 4.2 -> 3.1, -1.1", lines)
        self.assertIn("Speed mobile cls: 0.1 -> 0.1, +0", lines)
        self.assertIn("Speed desktop performance: 84 -> 98, +14", lines)
        lab = self.variant(AFTER, "after-lab", **{"speed.json": lambda d: d.update(source="lighthouse-lab", label="lab data")})
        lines = self.lines(BEFORE, lab)
        self.assertIn("Speed: not compared: PageSpeed Insights against lab data", lines)
        self.assertFalse([l for l in lines if l.startswith(("Speed mobile", "Speed desktop"))])
        none = self.variant(AFTER, "after-nospeed")
        (none / "speed.json").unlink()
        self.assertIn("Speed: not compared: PageSpeed Insights against no speed.json", self.lines(BEFORE, none))

    def test_factor_10_not_compared_across_speed_sources(self):
        lines = self.lines(BEFORE, AFTER)
        self.assertTrue([l for l in lines if l.startswith("Factor 10") and "->" in l])
        lab = self.variant(AFTER, "after-lab10", **{"speed.json": lambda d: d.update(source="lighthouse-lab", label="lab data")})
        lines = self.lines(BEFORE, lab)
        self.assertIn("Factor 10 (Mobile and speed, measured): not compared: PageSpeed Insights against lab data", lines)
        self.assertFalse([l for l in lines if l.startswith("Factor 10") and "->" in l])
        self.assertEqual(len([l for l in lines if l.startswith("Factor ") and "->" in l]), 8)
        none = self.variant(AFTER, "after-nospeed10")
        (none / "speed.json").unlink()
        self.assertIn("Factor 10 (Mobile and speed, measured): not compared: PageSpeed Insights against no speed.json", self.lines(BEFORE, none))

    def test_anchor_version_change_is_read_not_subtracted(self):
        old = self.variant(BEFORE, "before-old", **{"score.json": lambda d: d.pop("plugin_version")})
        lines = self.lines(old, AFTER)
        self.assertEqual(lines[0], "The before sheet has no plugin_version: read as 0.2.x.")
        self.assertEqual(lines[1], "Anchors changed in 0.3.0: read these scores side by side, not as a change.")
        self.assertEqual(lines[2], "Before: 37/100, based on the 9 factors that could be checked.")
        self.assertFalse([l for l in lines if l.startswith("Factor ")])
        newer = self.variant(AFTER, "after-040", **{"score.json": lambda d: d.update(plugin_version="0.5.1")})
        self.assertIn("Factor 3 (Does it work?): 3 -> 5, +2", self.lines(BEFORE, newer))

    def test_anchor_boundary_is_exactly_0_3_0(self):
        def sheet(name, version):
            return self.variant(BEFORE, name, **{"score.json": lambda d: d.update(plugin_version=version)})
        def after(name, version):
            return self.variant(AFTER, name, **{"score.json": lambda d: d.update(plugin_version=version)})
        for old, new in (("0.2.1", "0.3.0"), ("0.2.9", "0.3.0"), ("0.2.0", "0.4.0")):
            lines = self.lines(sheet("b" + old + new, old), after("a" + old + new, new))
            self.assertIn("Anchors changed in 0.3.0: read these scores side by side, not as a change.", lines, (old, new))
            self.assertFalse([l for l in lines if l.startswith("Factor ")], (old, new))
        for old, new in (("0.3.0", "0.3.1"), ("0.3.0", "0.4.0"), ("0.2.0", "0.2.1")):
            lines = self.lines(sheet("b" + old + new, old), after("a" + old + new, new))
            self.assertFalse([l for l in lines if l.startswith("Anchors changed")], (old, new))
            self.assertIn("Factor 3 (Does it work?): 3 -> 5, +2", lines, (old, new))

    def test_two_sheets_without_plugin_version_are_compared(self):
        lines = self.lines(OLD_A, OLD_B)
        self.assertEqual(lines[0], "Neither sheet has plugin_version: both read as 0.2.x.")
        self.assertEqual(lines[1], "Caution: 0.2.1 changed factor 10's anchors, so a change in factor 10 may come from the version, not the page.")
        self.assertFalse([l for l in lines if l.startswith("Anchors changed")])
        self.assertIn("Factor 2 (Is it for me?): 4 -> 5, +1", lines)
        self.assertIn("Factor 3 (Does it work?): 4 -> 4, +0", lines)

    def test_page_facts_json_is_read_as_facts(self):
        self.assertFalse((OLD_B / "facts.json").exists())
        self.assertTrue((OLD_B / "page_facts.json").is_file())
        lines = self.lines(OLD_A, OLD_B)
        self.assertIn('Title: "Harbor Lantern Co" -> "Handmade boat lanterns | Harbor Lantern Co"', lines)
        self.assertIn('H1: "Lanterns made by hand" -> "Handmade boat lanterns"', lines)
        self.assertIn("Button labels: not compared: facts from before 0.3.0 hold no links", lines)
        self.assertNotIn("Facts: not compared: facts on one side only", lines)
        self.assertNotIn("The result cannot be put down to either change.", lines)
        both = self.variant(OLD_B, "old-b-both")
        (both / "facts.json").write_text(json.dumps({"headings": [{"level": 1, "text": "Wins"}], "forms": []}))
        self.assertIn('H1: "Lanterns made by hand" -> "Wins"', self.lines(OLD_A, both))

    def test_search_placements_compared_for_the_same_keyword(self):
        after = self.variant(SEARCH, "search-after", **{"search.json": lambda d: d["placements"]["meta_description"].update(status="found", text="x")})
        lines = self.lines(SEARCH, after)
        self.assertIn("Search title: FOUND -> FOUND", lines)
        self.assertIn("Search meta_description: MISSING -> FOUND", lines)
        self.assertIn("Search url_slug: N/A -> N/A", lines)
        self.assertEqual(len([l for l in lines if l.startswith("Search ")]), 6)
        other = self.variant(SEARCH, "search-other", **{"search.json": lambda d: d.update(keyword="lantern repair")})
        lines = self.lines(SEARCH, other)
        self.assertIn('Search: not compared: keyword "handmade boat lanterns" against "lantern repair"', lines)
        self.assertFalse([l for l in lines if l.startswith("Search ") and "->" in l])
        unconfirmed = self.variant(SEARCH, "search-unconfirmed", **{"search.json": lambda d: d.update(keyword_confirmed=False)})
        self.assertIn("Search: not compared: the keyword is not confirmed", self.lines(SEARCH, unconfirmed))
        self.assertIn("Search: not compared: search.json on one side only", self.lines(SEARCH, BEFORE))

    def test_search_not_compared_when_variants_differ(self):
        base = self.variant(SEARCH, "search-va", **{"search.json": lambda d: d.update(variants=[])})
        other = self.variant(SEARCH, "search-vb", **{"search.json": lambda d: (d.update(variants=["boat lamps"]), d["placements"]["meta_description"].update(status="found"))})
        lines = self.lines(base, other)
        self.assertIn("Search: not compared: spelling variants differ", lines)
        self.assertFalse([l for l in lines if l.startswith("Search ") and "->" in l])
        same = self.variant(SEARCH, "search-vc", **{"search.json": lambda d: d.update(variants=[" Boat  LAMPS"])})
        again = self.variant(SEARCH, "search-vd", **{"search.json": lambda d: d.update(variants=["boat lamps", "Boat lamps"])})
        self.assertEqual(len([l for l in self.lines(same, again) if l.startswith("Search ") and "->" in l]), 6)

    def test_facts_drift_lists_the_changed_h1(self):
        lines = self.lines(BEFORE, AFTER)
        self.assertIn('H1: "Lanterns made by hand" -> "Handmade lanterns for your boat"', lines)
        self.assertIn('H2 list: added "Care"', lines)
        self.assertFalse([l for l in lines if l.startswith(("Title:", "Meta description:", "Form count:"))])
        same = self.lines(BEFORE, BEFORE_COPY(self))
        self.assertIn("Facts: no change in what was compared", same)

    def test_button_labels_come_from_links(self):
        lines = self.lines(BEFORE, AFTER)
        self.assertIn('Button labels: added "Order a sample"', lines)
        # a label in links but absent from ctas is still read; a footer link is left out
        more = self.variant(BEFORE, "before-links", **{"facts.json": lambda d: d["links"].append({"text": "Browse sizes", "href": "/sizes", "kind": "a", "in_footer": False})})
        lines = self.lines(more, AFTER)
        self.assertIn('Button labels: added "Order a sample"; removed "Browse sizes"', lines)
        footer = self.variant(AFTER, "after-footer", **{"facts.json": lambda d: d["links"].append({"text": "Press kit", "href": "/press", "kind": "a", "in_footer": True})})
        self.assertFalse([l for l in self.lines(BEFORE, footer) if "Press kit" in l])

    def test_headline_and_button_both_changed_is_not_attributed(self):
        lines = self.lines(BEFORE, AFTER)
        self.assertEqual(lines[-1], "The result cannot be put down to either change.")
        h1_only = self.variant(BEFORE, "h1-only", **{"facts.json": lambda d: d["headings"][0].update(text="A new headline")})
        lines = self.lines(BEFORE, h1_only)
        self.assertIn('H1: "Lanterns made by hand" -> "A new headline"', lines)
        self.assertNotIn("The result cannot be put down to either change.", lines)


def BEFORE_COPY(case):
    return case.variant(BEFORE, "before-copy")


class BadInputTests(Base):
    def assert_exit2(self, before, after, *needles):
        code, out, err = run(before, after)
        self.assertEqual(code, 2)
        self.assertEqual(out, [])
        self.assertTrue(err and all(l.startswith("compare: ") for l in err), err)
        for needle in needles:
            self.assertTrue(any(needle in l for l in err), (needle, err))

    def test_not_a_folder_and_same_folder(self):
        self.assert_exit2(self.tmp / "missing", AFTER, "before")
        self.assert_exit2(BEFORE, BEFORE)
        self.assert_exit2(BEFORE, BEFORE / ".." / "audit-before")

    def test_missing_or_broken_files_name_the_side(self):
        empty = self.tmp / "empty"
        empty.mkdir()
        self.assert_exit2(BEFORE, empty, "after", "score.json")
        bad = self.variant(AFTER, "bad")
        (bad / "speed.json").write_text("{not json")
        self.assert_exit2(BEFORE, bad, "after", "speed.json")
        listy = self.variant(AFTER, "listy")
        (listy / "facts.json").write_text("[]")
        self.assert_exit2(BEFORE, listy, "after", "facts.json")

    def test_invalid_sheet_and_version_report_every_problem(self):
        broken = self.variant(BEFORE, "broken", **{"score.json": lambda d: d.update(mode="x", plugin_version="v1")})
        worse = self.variant(AFTER, "worse", **{"score.json": lambda d: d.pop("page_role")})
        code, out, err = run(broken, worse)
        self.assertEqual((code, out), (2, []))
        self.assertTrue(any(l.startswith("compare: before: ") and "mode" in l for l in err))
        self.assertTrue(any(l.startswith("compare: before: ") and "plugin_version" in l for l in err))
        self.assertTrue(any(l.startswith("compare: after: ") and "page_role" in l for l in err))

    def test_bad_speed_search_and_facts_shapes(self):
        speed = self.variant(AFTER, "s", **{"speed.json": lambda d: d.pop("results")})
        self.assert_exit2(BEFORE, speed, "after", "speed.json")
        search = self.variant(SEARCH, "q", **{"search.json": lambda d: d["placements"].pop("h2")})
        self.assert_exit2(SEARCH, search, "after", "search.json")
        nokey = self.variant(SEARCH, "k", **{"search.json": lambda d: d.pop("keyword")})
        self.assert_exit2(SEARCH, nokey, "after", "search.json")
        for bad in (["found"], {"a": 1}, 7):
            odd = self.variant(SEARCH, "st", **{"search.json": lambda d: d["placements"]["title"].update(status=bad)})
            self.assert_exit2(SEARCH, odd, "after", "search.json")
            shutil.rmtree(odd)
        facts = self.variant(AFTER, "f", **{"facts.json": lambda d: d["headings"].append({"level": "1", "text": "x"})})
        self.assert_exit2(BEFORE, facts, "after", "facts.json")
        links = self.variant(AFTER, "l", **{"facts.json": lambda d: d.update(links="no")})
        self.assert_exit2(BEFORE, links, "after", "facts.json")

    def test_a_file_nested_too_deeply_is_exit_2_not_a_traceback(self):
        deep = self.variant(AFTER, "deep")
        (deep / "speed.json").write_text("[" * 200000)
        self.assert_exit2(BEFORE, deep, "after", "speed.json")
        deep_sheet = self.variant(BEFORE, "deep-sheet")
        (deep_sheet / "score.json").write_text("[" * 200000)
        self.assert_exit2(deep_sheet, AFTER, "before", "score.json")

    def test_wrong_argument_count_is_exit_2(self):
        code, out, _ = run(BEFORE, AFTER, "extra")
        self.assertEqual((code, out), (2, []))


class OutputTests(Base):
    def test_json_has_three_keys_and_the_plain_lines(self):
        code, plain, _ = run(BEFORE, AFTER)
        code, out, _ = run(BEFORE, AFTER, "--json")
        self.assertEqual(code, 0)
        data = json.loads("\n".join(out))
        self.assertEqual(sorted(data), ["after", "before", "lines"])
        self.assertEqual(data["lines"], plain)
        self.assertEqual((data["before"], data["after"]), (str(BEFORE), str(AFTER)))

    def test_no_blank_lines_and_blocks_in_order(self):
        lines = self.lines(BEFORE, AFTER)
        self.assertTrue(all(lines))
        order = [next(i for i, l in enumerate(lines) if l.startswith(p)) for p in ("Before:", "Speed ", "H1:")]
        self.assertEqual(order, sorted(order))

    def test_number_format(self):
        self.assertEqual(compare.fmt(12345.678), "12345.678")
        self.assertEqual(compare.fmt(54.0), "54")
        self.assertEqual(compare.fmt(0.1), "0.1")
        self.assertEqual(compare.fmt(2.4567), "2.457")
        self.assertEqual(compare.signed(2.4567, 2.0311), "-0.426")
        self.assertEqual(compare.signed(1.0, 1.0), "+0")
        self.assertEqual(compare.signed(1.0001, 1.0), "+0")

    def test_writes_nothing_in_the_folders(self):
        before = sorted(p.name for p in BEFORE.iterdir())
        run(BEFORE, AFTER)
        self.assertEqual(sorted(p.name for p in BEFORE.iterdir()), before)


if __name__ == "__main__":
    unittest.main()
