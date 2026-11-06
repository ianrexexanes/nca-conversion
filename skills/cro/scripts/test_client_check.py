import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "client_check.py"


def run(text):
    with tempfile.TemporaryDirectory() as folder:
        file = Path(folder) / "client.md"
        file.write_text(text, encoding="utf-8")
        done = subprocess.run([sys.executable, str(SCRIPT), str(file)], capture_output=True, encoding="utf-8")
    return done.returncode, done.stdout


class ClientCheckTests(unittest.TestCase):
    def test_fails_on_score_terms(self):
        code, out = run("Your Conversion Score is 64/100.\n")
        self.assertEqual(code, 1); self.assertIn("FAIL score", out)
    def test_fails_on_ai_names(self):
        code, out = run("I read it with Claude and ChatGPT.\n")
        self.assertEqual(code, 1); self.assertIn("FAIL ai-name", out)
    def test_fails_on_tool_names(self):
        code, out = run("A Playwright run in a headless browser.\n")
        self.assertEqual(code, 1); self.assertIn("FAIL tool-name", out)
    def test_headless_cms_warns_headless_browser_fails(self):
        code, out = run("We recommend a headless CMS.\n")
        self.assertEqual(code, 0); self.assertIn("WARN tool-word: line 1", out); self.assertIn("client_check: 0 FAIL, 1 WARN", out)
        code, out = run("We checked it in a headless browser.\n")
        self.assertEqual(code, 1); self.assertIn("FAIL tool-name: line 1", out)
        code, out = run("We checked it in headless browsers.\n")
        self.assertEqual(code, 1); self.assertIn("FAIL tool-name: line 1", out)
    def test_sprachmodellen_fails_like_its_other_forms(self):
        code, out = run("Mit Sprachmodellen geschrieben.\n")
        self.assertEqual(code, 1); self.assertIn("FAIL ai-name: line 1", out)
    def test_fails_on_hormozi(self):
        code, out = run("This follows Hormozi's value equation.\n")
        self.assertEqual(code, 1); self.assertIn("FAIL person", out)
    def test_passes_measured_pagespeed_fact(self):
        code, out = run("Google's PageSpeed Insights, run on October 13, 2026, "
                        "scores the home page 55 out of 100 on a phone.\n")
        self.assertEqual(code, 0); self.assertIn("client_check: 0 FAIL", out)
    def test_warns_on_citation_and_statistic_cues(self):
        code, out = run("According to a survey, 71 percent of visitors leave.\n")
        self.assertEqual(code, 0)
        self.assertIn("WARN citation", out); self.assertIn("WARN statistic", out)
    def test_german_cues_are_caught(self):
        code, out = run("Laut einer Studie steigen die Anfragen.\n")
        self.assertEqual(code, 0); self.assertIn("WARN citation", out)
        code, out = run("Mit künstlicher Intelligenz erstellt.\n")
        self.assertEqual(code, 1); self.assertIn("FAIL ai-name", out)
        code, out = run("Ein Sprachmodell schrieb das.\n")
        self.assertEqual(code, 1); self.assertIn("FAIL ai-name", out)
        code, out = run("Eine KI-gestützte Analyse.\n")
        self.assertEqual(code, 0); self.assertIn("WARN ai-word", out)
        code, out = run("Das bringt dreimal mehr Anfragen.\n")
        self.assertEqual(code, 0); self.assertIn("WARN statistic", out)
        code, out = run("Im Durchschnitt kommen zehn Anfragen.\n")
        self.assertIn("WARN statistic", out)
    def test_plain_german_text_gives_no_row(self):
        code, out = run("Die Startseite zeigt sofort, was das Produkt kann, und der Button fällt auf.\n")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "client_check: 0 FAIL, 0 WARN")
    def test_reports_line_numbers(self):
        code, out = run("A fine line.\n\nWe used Playwright here.\n")
        self.assertIn("FAIL tool-name: line 3", out)
    def test_exit_codes(self):
        self.assertEqual(run("A plain sentence about the page.\n")[0], 0)
        self.assertEqual(run("It was built with Puppeteer.\n")[0], 1)
        code, out = run("Looks like a study.\n")
        self.assertEqual(code, 0); self.assertIn("client_check: 0 FAIL, 1 WARN", out)


class RulingsTest(unittest.TestCase):
    def test_one_row_per_rule_per_line_in_line_then_table_order(self):
        code, out = run("A study by OpenAI and Gemini.\nPlaywright, Selenium and AI.\n")
        self.assertEqual(code, 1)
        self.assertEqual(out, "FAIL ai-name: line 1: A study by OpenAI and Gemini.\n"
                              "WARN citation: line 1: A study by OpenAI and Gemini.\n"
                              "FAIL tool-name: line 2: Playwright, Selenium and AI.\n"
                              "WARN ai-word: line 2: Playwright, Selenium and AI.\n"
                              "client_check: 2 FAIL, 2 WARN\n")

    def test_whole_words_in_any_case_and_plurals(self):
        code, out = run("Claudette keeps chatgpt-style notes on headlessness.\nWe used LLMs and two plugins.\n")
        self.assertEqual(code, 1)
        self.assertEqual(out, "FAIL ai-name: line 1: Claudette keeps chatgpt-style notes on headlessness.\n"
                              "FAIL ai-name: line 2: We used LLMs and two plugins.\n"
                              "WARN plugin-word: line 2: We used LLMs and two plugins.\n"
                              "client_check: 2 FAIL, 1 WARN\n")

    def test_excerpt_is_the_trimmed_line_cut_to_100_characters(self):
        line = "Claude " + "word " * 40
        code, out = run("   " + line + "  \n")
        self.assertEqual(out.splitlines()[0], "FAIL ai-name: line 1: " + line.strip()[:100])

    def test_utf8_text_and_crlf_line_ends(self):
        code, out = run("Für Käufer.\r\n\r\nKäufer lasen es mit ChatGPT.\r\n")
        self.assertEqual((code, out), (1, "FAIL ai-name: line 3: Käufer lasen es mit ChatGPT.\nclient_check: 1 FAIL, 0 WARN\n"))

    def test_unreadable_file_exits_2_without_a_summary(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder) / "missing.md"
            latin = Path(folder) / "latin.md"
            latin.write_bytes("Käufer lasen es.\n".encode("latin-1"))
            for path, message in ((missing, f"client_check: cannot read {missing}\n"),
                                  (latin, f"client_check: {latin} is not UTF-8 text\n")):
                done = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, encoding="utf-8")
                self.assertEqual((done.returncode, done.stdout, done.stderr), (2, "", message))


if __name__ == "__main__":
    unittest.main()
