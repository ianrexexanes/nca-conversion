import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "design_check.py"
FIXTURES = HERE / "fixtures"
CLEAN = FIXTURES / "tokens-clean.json"
PLANTED = FIXTURES / "tokens-planted.json"
BLACK = FIXTURES / "tokens-black.json"


def run(path, *args):
    done = subprocess.run([sys.executable, str(SCRIPT), str(path), *args], capture_output=True, text=True)
    return done.returncode, done.stdout, done.stderr


def findings(path):
    code, out, _err = run(path, "--json")
    return code, json.loads(out)


def rule_levels(path):
    _code, data = findings(path)
    return {f["rule"]: f["level"] for f in data["findings"]}


class ContrastTest(unittest.TestCase):
    def test_contrast_matches_known_pairs(self):
        sys.path.insert(0, str(HERE))
        self.addCleanup(sys.path.remove, str(HERE))
        import design_check
        self.assertEqual(design_check.contrast("#000000", "#ffffff"), 21.0)
        self.assertEqual(design_check.contrast("#ffffff", "#000000"), 21.0)
        self.assertEqual(round(design_check.contrast("#777777", "#ffffff"), 2), 4.48)
        self.assertLess(design_check.contrast("#777777", "#ffffff"), 4.5)
        self.assertEqual(round(design_check.contrast("#333333", "#ffffff"), 2), 12.63)


class RuleTest(unittest.TestCase):
    def test_clean_tokens_pass(self):
        code, out, err = run(CLEAN)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out.strip(), "design_check: 0 FAIL, 0 WARN")

    def test_contrast_text_fails_text_under_4_5(self):
        self.assertEqual(rule_levels(PLANTED)["CONTRAST_TEXT"], "FAIL")

    def test_contrast_action_fails_action_text_under_4_5(self):
        self.assertEqual(rule_levels(PLANTED)["CONTRAST_ACTION"], "FAIL")

    def test_action_visible_fails_action_under_3_on_the_background(self):
        self.assertEqual(rule_levels(PLANTED)["ACTION_VISIBLE"], "FAIL")

    def test_action_visible_edge_sits_at_three_to_one(self):
        def levels(action):
            text = ('{"colors": {"text": "#333333", "background": "#ffffff", "action": "%s", "action_text": "#000000"},'
                    ' "type": {"h1_px": 52, "body_px": 16}}' % action)
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "t.json"
                path.write_text(text, encoding="utf-8")
                return rule_levels(path)
        self.assertEqual(levels("#959595").get("ACTION_VISIBLE"), "FAIL")
        self.assertNotIn("ACTION_VISIBLE", levels("#949494"))

    def test_action_isolated_warns_when_another_token_equals_the_action(self):
        self.assertEqual(rule_levels(PLANTED)["ACTION_ISOLATED"], "WARN")
        self.assertNotIn("ACTION_ISOLATED", rule_levels(CLEAN))

    def test_headline_ratio_warns_outside_three_to_four(self):
        self.assertEqual(rule_levels(PLANTED)["HEADLINE_RATIO"], "WARN")
        self.assertNotIn("HEADLINE_RATIO", rule_levels(CLEAN))

    def test_a_type_size_of_nan_or_infinity_is_a_fail_row(self):
        for token in ("NaN", "Infinity"):
            for name in ("h1_px", "body_px"):
                sizes = {"h1_px": 52, "body_px": 16, name: token}
                text = '{"colors": {"text": "#333333", "background": "#ffffff", "action": "#0047b3", "action_text": "#ffffff"},' \
                       ' "type": {"h1_px": %s, "body_px": %s}}' % (sizes["h1_px"], sizes["body_px"])
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "t.json"
                    path.write_text(text, encoding="utf-8")
                    code, data = findings(path)
                self.assertEqual(code, 1, (token, name))
                self.assertIn(("FAIL", "type." + name, "TYPE_SIZE"),
                              [(f["level"], f["key"], f["rule"]) for f in data["findings"]], (token, name))

    def test_body_black_warns_on_pure_black_text_and_only_that(self):
        code, data = findings(BLACK)
        self.assertEqual(code, 0)
        self.assertEqual([(f["level"], f["rule"], f["key"]) for f in data["findings"]], [("WARN", "BODY_BLACK", "colors.text")])

    def test_planted_output_and_exit(self):
        code, out, _err = run(PLANTED)
        self.assertEqual(code, 1)
        self.assertEqual(out.strip().splitlines()[-1], "design_check: 3 FAIL, 2 WARN")
        self.assertRegex(out, r"(?m)^FAIL colors\.text CONTRAST_TEXT: ")

    def test_thresholds_use_the_unrounded_ratio_and_ratio_bounds_are_inside(self):
        tokens = json.loads(CLEAN.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            def levels(**over):
                t = json.loads(json.dumps(tokens))
                for key, value in over.items():
                    (t["type"] if key.endswith("_px") else t["colors"])[key] = value
                path = Path(tmp) / "t.json"
                path.write_text(json.dumps(t), encoding="utf-8")
                return rule_levels(path)
            self.assertNotIn("CONTRAST_TEXT", levels(text="#767676"))   # 4.54:1
            self.assertIn("CONTRAST_TEXT", levels(text="#777777"))      # 4.48:1
            self.assertNotIn("HEADLINE_RATIO", levels(h1_px=48))
            self.assertNotIn("HEADLINE_RATIO", levels(h1_px=64))
            self.assertIn("HEADLINE_RATIO", levels(h1_px=47))
            self.assertIn("HEADLINE_RATIO", levels(h1_px=65))
            self.assertNotIn("ACTION_ISOLATED", levels(background="#FFF"))
            self.assertIn("ACTION_ISOLATED", levels(accent="#0047B3"))
            self.assertIn("BODY_BLACK", levels(text="#000"))


class BadInputTest(unittest.TestCase):
    def bad(self, content):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.json"
            path.write_text(content, encoding="utf-8")
            code, out, err = run(path)
        self.assertEqual((code, out), (2, ""))
        self.assertTrue(err.startswith("design_check: "), err)

    def test_bad_input_exits_2(self):
        tokens = json.loads(CLEAN.read_text())
        self.bad("{not json")
        self.bad("[]")
        no_action = json.loads(json.dumps(tokens))
        del no_action["colors"]["action"]
        self.bad(json.dumps(no_action))
        for patch in ({"colors": {"text": "blue"}}, {"type": {"h1_px": 0}}, {"type": {"body_px": "16"}}):
            t = json.loads(json.dumps(tokens))
            for group, values in patch.items():
                t[group].update(values)
            self.bad(json.dumps(t))
        no_size = json.loads(json.dumps(tokens))
        del no_size["type"]["body_px"]
        self.bad(json.dumps(no_size))

    def test_missing_file_exits_2(self):
        code, _out, err = run(HERE / "nonexistent.json")
        self.assertEqual(code, 2)
        self.assertTrue(err.startswith("design_check: "), err)


if __name__ == "__main__":
    unittest.main()
