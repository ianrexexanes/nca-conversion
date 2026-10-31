import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import score

HERE = Path(__file__).resolve().parent


def sheet(scores):
    factors = []
    for i, s in enumerate(scores, start=1):
        if s is None:
            factors.append({"id": i, "score": None, "not_checked": "no speed data"})
        else:
            factors.append({"id": i, "score": s, "evidence": "saw it on the page"})
    return {"page": "https://example.com/", "mode": "direct", "page_role": "landing", "traffic": "unknown", "register": "conservative B2B", "factors": factors}


NINE = sheet([8, 7, 6, 9, 5, 6, 7, 8, 8, None])  # 8+7+6+9+5+6+7+8+8 = 64


class ScoreTest(unittest.TestCase):
    def test_total_is_sum_of_scored_factors(self):
        result = score.score_sheet(NINE)
        self.assertEqual(result["total"], 64)
        self.assertEqual((result["scored"], result["possible"]), (9, 90))
        self.assertEqual(len(result["factors"]), 10)

    def test_line_for_nine_checked(self):
        self.assertEqual(score.score_sheet(NINE)["line"], "64/100, based on the 9 factors that could be checked.")

    def test_line_for_all_ten(self):
        full = sheet([7, 7, 7, 7, 7, 7, 7, 7, 8, 8])
        self.assertEqual(score.score_sheet(full)["line"], "72/100, based on all 10 factors.")

    def test_line_for_one_checked(self):
        one = sheet([6] + [None] * 9)
        self.assertEqual(score.score_sheet(one)["line"], "6/100, based on the 1 factor that could be checked.")

    def test_all_unchecked_gives_no_score(self):
        none = sheet([None] * 10)
        result = score.score_sheet(none)
        self.assertEqual(result["line"], "No score: none of the 10 factors could be checked.")
        self.assertEqual(result["total"], 0)

    def test_rejects_missing_factor(self):
        bad = json.loads(json.dumps(NINE))
        bad["factors"] = [f for f in bad["factors"] if f["id"] != 4]
        problems = score.validate(bad)
        self.assertTrue(any("factor 4" in p and "missing" in p for p in problems), problems)

    def test_rejects_duplicate_factor(self):
        bad = json.loads(json.dumps(NINE))
        bad["factors"][3]["id"] = 3
        problems = score.validate(bad)
        self.assertTrue(any("factor 3" in p and "duplicate" in p for p in problems), problems)

    def test_rejects_score_out_of_range(self):
        for value in (11, -1, 7.5):
            bad = json.loads(json.dumps(NINE))
            bad["factors"][0]["score"] = value
            problems = score.validate(bad)
            self.assertTrue(any("factor 1" in p for p in problems), (value, problems))

    def test_rejects_scored_factor_without_evidence(self):
        bad = json.loads(json.dumps(NINE))
        bad["factors"][1]["evidence"] = "  "
        self.assertTrue(any("factor 2" in p and "evidence" in p for p in score.validate(bad)))

    def test_rejects_unchecked_factor_without_reason(self):
        bad = json.loads(json.dumps(NINE))
        bad["factors"][9]["not_checked"] = ""
        self.assertTrue(any("factor 10" in p and "not_checked" in p for p in score.validate(bad)))

    def test_rejects_missing_or_bad_mode(self):
        missing = json.loads(json.dumps(NINE))
        del missing["mode"]
        self.assertIn("mode: missing", score.validate(missing))
        bad = json.loads(json.dumps(NINE))
        bad["mode"] = "organic"
        self.assertIn('mode: "organic" is not search or direct', score.validate(bad))

    def test_rejects_missing_or_bad_page_role(self):
        missing = json.loads(json.dumps(NINE))
        del missing["page_role"]
        self.assertIn("page_role: missing", score.validate(missing))
        bad = json.loads(json.dumps(NINE))
        bad["page_role"] = "blog"
        self.assertIn('page_role: "blog" is not homepage, service or landing', score.validate(bad))

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "good.json"
            good.write_text(json.dumps(NINE))
            bad_sheet = json.loads(json.dumps(NINE))
            bad_sheet["factors"] = [f for f in bad_sheet["factors"] if f["id"] != 4]
            bad = Path(tmp) / "bad.json"
            bad.write_text(json.dumps(bad_sheet))
            ok = subprocess.run([sys.executable, str(HERE / "score.py"), str(good)], capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertEqual(ok.stdout.strip(), "64/100, based on the 9 factors that could be checked.")
            no = subprocess.run([sys.executable, str(HERE / "score.py"), str(bad)], capture_output=True, text=True)
            self.assertEqual(no.returncode, 2)
            self.assertIn("factor 4", no.stderr)


class RulingsTest(unittest.TestCase):
    def test_result_lists_factors_by_id_with_names(self):
        fresh = sheet([8, 7, 6, 9, 5, 6, 7, 8, 8, None])
        before = json.dumps(fresh)
        result = score.score_sheet(fresh)
        self.assertEqual(json.dumps(fresh), before)
        self.assertEqual([f["id"] for f in result["factors"]], list(range(1, 11)))
        self.assertEqual([f["name"] for f in result["factors"]], list(score.FACTORS))
        self.assertEqual(result["factors"][0], {"id": 1, "name": "What's in it for me?", "score": 8, "evidence": "saw it on the page"})
        self.assertEqual(result["factors"][9], {"id": 10, "name": "Mobile and speed, measured", "score": None, "not_checked": "no speed data"})

    def test_factor_order_in_the_sheet_does_not_matter(self):
        shuffled = json.loads(json.dumps(NINE))
        shuffled["factors"].reverse()
        self.assertEqual(score.score_sheet(shuffled), score.score_sheet(NINE))

    def test_booleans_are_neither_scores_nor_ids(self):
        bad = json.loads(json.dumps(NINE))
        bad["factors"][0]["score"] = True
        self.assertEqual(score.validate(bad), ["factor 1: score true is not a whole number"])
        bad = json.loads(json.dumps(NINE))
        bad["factors"][0]["id"] = True
        self.assertEqual(score.validate(bad), ["sheet: factor id true is not a whole number from 1 to 10", "factor 1: missing"])

    def test_problems_come_in_order_with_fixed_wording(self):
        bad = json.loads(json.dumps(NINE))
        del bad["page_role"]
        bad["traffic"] = "organic"
        bad["factors"][0]["score"] = 11
        bad["factors"][1]["evidence"] = ""
        bad["factors"][2]["score"] = 7.5
        bad["factors"][3]["id"] = 3
        bad["factors"][4]["score"] = "7"
        del bad["factors"][5]["score"]
        bad["factors"][9]["not_checked"] = " "
        self.assertEqual(score.validate(bad), [
            "page_role: missing",
            'sheet: traffic "organic" is not cold-outreach, ads, search, mixed or unknown',
            "factor 1: score 11 is outside 0 to 10",
            "factor 2: scored but no evidence",
            "factor 3: score 7.5 is not a whole number",
            "factor 3: duplicate",
            "factor 4: missing",
            'factor 5: score "7" is not a whole number',
            "factor 6: score missing",
            "factor 10: not scored but no not_checked reason",
        ])

    def test_malformed_sheets_give_problems_not_exceptions(self):
        self.assertEqual(score.validate([]), ["sheet: not a JSON object"])
        no_factors = json.loads(json.dumps(NINE))
        del no_factors["factors"]
        not_a_list = json.loads(json.dumps(NINE))
        not_a_list["factors"] = {"1": 8}
        short = json.loads(json.dumps(NINE))
        short["factors"] = short["factors"][:9]
        odd = json.loads(json.dumps(NINE))
        odd["factors"][4] = "five"
        del odd["factors"][6]["id"]
        odd["factors"][7]["id"] = "8"
        odd["factors"][8]["id"] = 11
        cases = [
            (no_factors, ["sheet: factors missing"]),
            (not_a_list, ["sheet: factors is not a list"]),
            (short, ["sheet: 9 factor entries, not 10", "factor 10: missing"]),
            (odd, [
                "sheet: factor entry 5 is not an object",
                "sheet: factor entry 7 has no id",
                'sheet: factor id "8" is not a whole number from 1 to 10',
                "sheet: factor id 11 is not a whole number from 1 to 10",
                "factor 5: missing",
                "factor 7: missing",
                "factor 8: missing",
                "factor 9: missing",
            ]),
        ]
        for case, expected in cases:
            self.assertEqual(score.validate(case), expected)
        with self.assertRaises(ValueError) as caught:
            score.score_sheet(short)
        self.assertEqual(str(caught.exception), "sheet: 9 factor entries, not 10; factor 10: missing")

    def test_cli_json_output_and_sheets_it_cannot_use(self):
        script = str(HERE / "score.py")
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "good.json"
            good.write_text(json.dumps(NINE))
            out = subprocess.run([sys.executable, script, str(good), "--json"], capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(json.loads(out.stdout), score.score_sheet(NINE))
            bad_sheet = json.loads(json.dumps(NINE))
            bad_sheet["mode"] = "a; b"
            bad_sheet["factors"][0]["score"] = 11
            bad = Path(tmp) / "bad.json"
            bad.write_text(json.dumps(bad_sheet))
            broken = Path(tmp) / "broken.json"
            broken.write_text("{not json")
            listed = Path(tmp) / "listed.json"
            listed.write_text("[]")
            gone = Path(tmp) / "gone.json"
            for path, lines in (
                (bad, ['mode: "a; b" is not search or direct', "factor 1: score 11 is outside 0 to 10"]),
                (broken, ["sheet: not valid JSON"]),
                (listed, ["sheet: not a JSON object"]),
                (gone, [f"sheet: cannot read {gone}"]),
            ):
                no = subprocess.run([sys.executable, script, str(path), "--json"], capture_output=True, text=True)
                self.assertEqual((no.returncode, no.stdout, no.stderr.splitlines()), (2, "", lines), path.name)


if __name__ == "__main__":
    unittest.main()
