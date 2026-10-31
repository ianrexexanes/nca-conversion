import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = str(Path(__file__).resolve().parent / "find_figures.py")
HEADER = "| path | line text | figure | verdict | source |\n| --- | --- | --- | --- | --- |\n"
ROW_FOR_OTHER_TEXT = HEADER + "| skills/demo/references/x.md | A 4x lift. | 4x | example | labelled in the file |\n"
LINES = ["Pages gain 23% more leads.", "A 3x lift.", "It is 2.5 times faster.",
         "7 out of 10 buyers agree.", "Loads in 2.5 seconds, under 300 ms."]
EXTENDED = ["An LCP of 2.5 s or less.", "Half of the sessions bounce.", "A loss stings roughly double.",
            "Forty percent agree.", "At the 75th percentile.", "Twenty times the traffic.",
            "A tenfold rise.", "An order of magnitude more.", "Two in three people.",
            "A quarter of completions.", "Readers decide in one second.", "Signed inside eight weeks.",
            "Ten thousand sessions.", "Used by 2,400 companies.", "Costs $3 a day.",
            "A third party checks it."]


def run(lines, ledger=None, files=None):
    """Run find_figures.py on a temporary root and return (exit code, stdout).

    The root holds skills/demo/references/x.md with the given lines and skills/demo/SKILL.md
    with "A 9x claim."; files maps further paths under the root to their text.
    """
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        refs = root / "skills" / "demo" / "references"
        refs.mkdir(parents=True)
        (refs / "x.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        (root / "skills" / "demo" / "SKILL.md").write_text("A 9x claim.\n", encoding="utf-8")
        for rel, text in (files or {}).items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(text, encoding="utf-8")
        extra = []
        if ledger is not None:
            (root / "ledger.md").write_text(ledger, encoding="utf-8")
            extra = ["--ledger", "ledger.md"]
        done = subprocess.run([sys.executable, SCRIPT, "skills"] + extra, cwd=root,
                              capture_output=True, text=True)
        return done.returncode, done.stdout


class FindFiguresTest(unittest.TestCase):
    def test_finds_percent_multiplier_and_time_figures(self):
        out = run(LINES)[1]
        for want in ("x.md:1: 23% | Pages gain 23% more leads.", "x.md:2: 3x | A 3x lift.",
                     "x.md:3: 2.5 times | It is 2.5 times faster.",
                     "x.md:4: 7 out of 10 | 7 out of 10 buyers agree.",
                     "x.md:5: 2.5 seconds | Loads in 2.5 seconds, under 300 ms.",
                     "x.md:5: 300 ms | Loads in 2.5 seconds, under 300 ms."):
            self.assertIn(want, out)
        self.assertNotIn("9x", out)      # SKILL.md is not scanned

    def test_ledger_accounts_for_a_figure(self):
        code, out = run(["A 3x lift."], ledger="| path | line text | figure | verdict | source |\n| --- | --- | --- | --- | --- |\n"
                        "| skills/demo/references/x.md | A 3x lift. | 3x | example | labelled in the file |\n")
        self.assertEqual(code, 0)

    def test_unaccounted_figure_fails(self):
        code, out = run(["A 3x lift."], ledger=ROW_FOR_OTHER_TEXT)   # a row keyed by different line text
        self.assertEqual(code, 1); self.assertIn("A 3x lift.", out)


class FindFiguresRulingsTest(unittest.TestCase):
    def test_figures_in_words_and_other_forms_are_found(self):   # R117
        out = run(EXTENDED)[1]
        for want in ("x.md:1: 2.5 s | ", "x.md:2: Half | ", "x.md:3: double | ", "x.md:4: Forty percent | ",
                     "x.md:5: 75th percentile | ", "x.md:6: Twenty times | ", "x.md:7: tenfold | ",
                     "x.md:8: order of magnitude | ", "x.md:9: Two in three | ", "x.md:10: A quarter | ",
                     "x.md:11: one second | ", "x.md:12: eight weeks | ", "x.md:13: thousand | ",
                     "x.md:14: 2,400 companies | ", "x.md:15: $3 | "):
            self.assertIn(want, out)
        self.assertNotIn("x.md:14: 2,400 | ", out)   # the longest match at one start wins
        self.assertNotIn("x.md:16:", out)            # "a third party" is not a fraction

    def test_rows_on_one_line_follow_the_line(self):   # R118
        out = run(LINES)[1].splitlines()
        self.assertLess(out.index("skills/demo/references/x.md:5: 2.5 seconds | Loads in 2.5 seconds, under 300 ms."),
                        out.index("skills/demo/references/x.md:5: 300 ms | Loads in 2.5 seconds, under 300 ms."))

    def test_overlapping_matches_print_once(self):   # R118
        self.assertEqual(run(LINES)[1].count("x.md:4: "), 1)

    def test_listing_prints_rows_only(self):   # R118
        code, out = run(LINES)
        self.assertEqual(code, 0)
        self.assertEqual(len(out.splitlines()), 6)
        for line in out.splitlines():
            self.assertRegex(line, r"^skills/demo/references/x\.md:\d+: .+ \| .+$")

    def test_ledger_names_each_unaccounted_figure_then_sums_up(self):   # R118
        out = run(["A 3x lift."], ledger=ROW_FOR_OTHER_TEXT)[1].splitlines()
        self.assertIn("unaccounted: skills/demo/references/x.md:1: 3x | A 3x lift.", out)
        self.assertEqual(out[-1], "find_figures: 1 figures, 1 unaccounted")

    def test_ledger_reads_an_escaped_pipe(self):   # R118
        ledger = HEADER + "| skills/demo/references/x.md | A 3x \\| 4x lift. | 3x | example | labelled in the file |\n"
        code, out = run(["A 3x | 4x lift."], ledger=ledger)
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[-1], "find_figures: 2 figures, 0 unaccounted")

    def test_ledger_row_needs_the_same_path(self):   # R118
        ledger = HEADER + "| skills/other/references/x.md | A 3x lift. | 3x | example | labelled in the file |\n"
        self.assertEqual(run(["A 3x lift."], ledger=ledger)[0], 1)

    def test_rows_for_removed_figures_are_ignored(self):   # R118
        ledger = HEADER + ("| skills/demo/references/x.md | A 3x lift. | 3x | example | labelled in the file |\n"
                           "| skills/demo/references/x.md | Gone 9x. | 9x | removed | no original found |\n")
        self.assertEqual(run(["A 3x lift."], ledger=ledger)[0], 0)

    def test_only_markdown_directly_under_references(self):   # R118
        code, out = run(["No figure here."], files={"skills/demo/references/deep/y.md": "A 5x lift.\n",
                                                    "skills/demo/references/z.txt": "A 6x lift.\n",
                                                    "skills/demo/notes/w.md": "A 7x lift.\n"})
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_files_in_sorted_order(self):   # R118
        out = run(["A 3x lift."], files={"skills/alpha/references/z.md": "A 5x lift.\n"})[1].splitlines()
        self.assertEqual([line.split(":")[0] for line in out],
                         ["skills/alpha/references/z.md", "skills/demo/references/x.md"])

    def test_bad_input_exits_2_without_a_traceback(self):   # R128
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            refs = root / "skills" / "demo" / "references"
            refs.mkdir(parents=True)
            (root / "ledger.md").write_bytes(b"| skills/demo/references/x.md | A 3x lift \xff. |\n")
            for text, args in ((b"A 3x lift \xff.\n", ["skills"]), (b"A 3x lift.\n", ["skills", "--ledger", "ledger.md"]),
                               (b"A 3x lift.\n", []), (b"A 3x lift.\n", ["skills", "--ledger"]),
                               (b"A 3x lift.\n", ["missing"])):
                (refs / "x.md").write_bytes(text)
                done = subprocess.run([sys.executable, SCRIPT] + args, cwd=root, capture_output=True, text=True)
                self.assertEqual(done.returncode, 2, args)
                self.assertNotIn("Traceback", done.stderr)
                self.assertNotIn("can't open file", done.stderr)


if __name__ == "__main__":
    unittest.main()
