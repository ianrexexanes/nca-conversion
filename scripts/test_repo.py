import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_frontmatter  # noqa: E402

VERSION = "0.2.0"


def skill_version(path: Path) -> str:
    match = re.search(r"^metadata:\s*\n(?:[ \t]+.*\n)*?[ \t]+version:\s*(\S+)", path.read_text(encoding="utf-8"), re.M)
    return match.group(1).strip("\"'") if match else "<none>"


class RepoStructureTest(unittest.TestCase):
    def test_every_version_is_0_2_0(self):
        plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(plugin["version"], VERSION)
        self.assertEqual(market["metadata"]["version"], VERSION)
        skills = sorted((ROOT / "skills").glob("*/SKILL.md"))
        self.assertGreaterEqual(len(skills), 7)
        for path in skills:
            self.assertEqual(skill_version(path), VERSION, str(path.relative_to(ROOT)))

    def test_frontmatter_guard_passes(self):
        self.assertEqual(check_frontmatter.main(str(ROOT)), 0)


class SetupReferenceTest(unittest.TestCase):
    def test_setup_reference_names_both_commands_and_the_key_file(self):
        text = (ROOT / "skills" / "cro" / "references" / "setup.md").read_text(encoding="utf-8")
        for command in (
            'python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/setup.py --data-dir ${CLAUDE_PLUGIN_DATA}',
            'python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/doctor.py --data-dir ${CLAUDE_PLUGIN_DATA}',
            "~/.config/nca-conversion/pagespeed.key",
        ):
            self.assertIn(command, text)


class ScoreAnchorsTest(unittest.TestCase):
    def test_score_anchors_cover_every_factor_at_3_6_9(self):
        sys.path.insert(0, str(ROOT / "skills" / "cro" / "scripts"))
        import score
        text = (ROOT / "skills" / "cro" / "references" / "score-anchors.md").read_text(encoding="utf-8")
        headings = re.findall(r"^## (\d+)\. (.+)$", text, re.M)
        self.assertEqual([f"{n}. {name}" for n, name in headings], [f"{i}. {name}" for i, name in enumerate(score.FACTORS, start=1)])
        sections = re.split(r"^## \d+\. .+$", text, flags=re.M)[1:]
        self.assertEqual(len(sections), 10)
        for i, body in enumerate(sections, start=1):
            for level in ("3", "6", "9"):
                self.assertRegex(body, rf"(?m)^- \*\*{level}:\*\* \S", f"factor {i} has no anchor for {level}")

    def test_factors_1_and_2_have_a_line_per_mode(self):
        text = (ROOT / "skills" / "cro" / "references" / "score-anchors.md").read_text(encoding="utf-8")
        sections = re.split(r"^## \d+\. .+$", text, flags=re.M)[1:]
        for i in (1, 2):
            for label in ("Search page", "Direct page"):
                self.assertRegex(sections[i - 1], rf"(?m)^- \*\*{label}:\*\* \S", f"factor {i} has no {label} line")


class ScoreAnchorsRulingsTest(unittest.TestCase):
    LABELS = ("3", "6", "9", "Homepage", "Service page", "Landing page", "Search page", "Direct page")

    def test_each_factor_section_holds_only_labelled_bullets_in_order(self):
        text = (ROOT / "skills" / "cro" / "references" / "score-anchors.md").read_text(encoding="utf-8")
        sections = re.split(r"^## \d+\. .+$", text, flags=re.M)[1:]
        self.assertEqual(len(sections), 10)
        for i, body in enumerate(sections, start=1):
            labels = []
            for line in body.splitlines():
                if not line.strip():
                    continue
                found = re.fullmatch(r"- \*\*(.+?):\*\* \S.*", line)
                self.assertIsNotNone(found, f"factor {i}: {line!r} is not a labelled bullet")
                labels.append(found.group(1))
            self.assertEqual(labels, [label for label in self.LABELS if label in labels], f"factor {i}: {labels}")
            self.assertEqual(labels[:3], ["3", "6", "9"], f"factor {i}")
            modes = [label for label in labels if label in ("Search page", "Direct page")]
            self.assertEqual(modes, ["Search page", "Direct page"] if i in (1, 2) else [], f"factor {i}")

    def test_how_to_score_comes_first_and_stays_under_40_lines(self):
        lines = (ROOT / "skills" / "cro" / "references" / "score-anchors.md").read_text(encoding="utf-8").splitlines()
        self.assertIn("## How to score", lines)
        start = lines.index("## How to score")
        first = next((n for n, line in enumerate(lines) if line.startswith("## 1. ")), len(lines))
        self.assertLess(start, first)
        section = lines[start:first]
        while section and not section[-1].strip():
            section.pop()
        self.assertLess(len(section), 40)
        if len(lines) > 100:
            self.assertIn("## Contents", lines[:start], "a file over 100 lines opens with ## Contents")


class ClientVersionTests(unittest.TestCase):
    def test_client_version_names_every_label_and_the_check(self):
        text = (ROOT / "skills/cro/references/client-version.md").read_text(encoding="utf-8")
        for required in (
            "**Site:**",
            "**Checked:**",
            "**Pages read:**",
            "**Method:**",
            "**Written by:**",
            "**What I saw**",
            "**Why it costs leads**",
            "**The fix**",
            "**Effort**",
            "The three leaks that cost the most, in the order I would fix them",
            "No score",
            "python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/client_check.py <client file>",
        ):
            self.assertIn(required, text)


class ClientVersionRulingsTest(unittest.TestCase):
    PARTS = ["## Format", "## Rules", "## Language", "## Voice", "## The check"]

    def read_parts(self):
        lines = (ROOT / "skills/cro/references/client-version.md").read_text(encoding="utf-8").splitlines()
        parts, fenced = [["", []]], False
        for line in lines:
            if line.startswith("```"):
                fenced = not fenced
            if line.startswith("## ") and not fenced:
                parts.append([line, []])
            else:
                parts[-1][1].append(line)
        return lines, parts

    def test_parts_come_in_step_6_order(self):
        lines, parts = self.read_parts()
        self.assertTrue(lines[0].startswith("# "), lines[0])
        self.assertEqual([head for head, _ in parts[1:]], self.PARTS)
        self.assertTrue([line for line in parts[0][1][1:] if line.strip()], "a paragraph comes between the title and ## Format")

    def test_format_block_holds_the_shape_and_passes_client_check(self):
        body = dict(self.read_parts()[1][1:])["## Format"]
        fences = [n for n, line in enumerate(body) if line.startswith("```")]
        self.assertEqual(len(fences), 2, "## Format holds one fenced block")
        block = "\n".join(body[fences[0] + 1:fences[1]]) + "\n"
        shape = ["**Site:**", "**Checked:**", "**Pages read:**", "**Method:**", "**Written by:**", "### ", "**What I saw**",
                 "**Why it costs leads**", "**The fix**", "**Effort**", "## Summary",
                 "The three leaks that cost the most, in the order I would fix them."]
        found = [block.find(part) for part in shape]
        self.assertTrue(-1 not in found and found == sorted(found), list(zip(shape, found)))
        self.assertEqual(re.findall(r"(?m)^([1-9])\. \S", block[found[-1]:]), ["1", "2", "3"])
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "client.md"
            file.write_text(block, encoding="utf-8")
            done = subprocess.run([sys.executable, str(ROOT / "skills/cro/scripts/client_check.py"), str(file)],
                                  capture_output=True, encoding="utf-8")
        self.assertEqual((done.returncode, done.stdout), (0, "client_check: 0 FAIL, 0 WARN\n"))

    def test_rules_flag_the_one_example_and_the_check_gives_its_rule(self):
        parts = dict(self.read_parts()[1][1:])
        self.assertTrue(any("Example:" in line and "PageSpeed Insights" in line for line in parts["## Rules"]))
        check = "\n".join(parts["## The check"])
        self.assertIn("```bash\npython3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/client_check.py <client file>\n```", check)
        self.assertIn("fix every FAIL, read every WARN, and keep only measured facts about the client's own page", check)


class ModesReferenceTests(unittest.TestCase):
    def test_modes_reference_has_required_parts(self):
        text = (ROOT / "skills" / "cro" / "references" / "modes.md").read_text(encoding="utf-8")
        required = ("Search page", "Direct page", "GA4", "never picks a keyword",
                    "title", "meta description", "URL", "H1", "first sentence", "H2",
                    "home page", "not applicable")
        for part in required:
            self.assertIn(part, text, part)


class ModesRulingsTest(unittest.TestCase):
    PARTS = ["## The two modes", "## Keyword research comes first", "## The six placements", "## How the audit judges the hero"]

    def test_modes_parts_come_in_step_7_order(self):
        lines = (ROOT / "skills" / "cro" / "references" / "modes.md").read_text(encoding="utf-8").splitlines()
        self.assertTrue(lines[0].startswith("# "), lines[0])
        self.assertLess(len(lines), 100)
        self.assertEqual([line for line in lines if line.startswith("## ")], self.PARTS)
        opening = [line for line in lines[1:lines.index(self.PARTS[0])] if line.strip()]
        self.assertTrue(opening, "a paragraph comes between the title and the first part")

    def test_modes_carries_the_archetype_examples_and_no_figure(self):
        text = (ROOT / "skills" / "cro" / "references" / "modes.md").read_text(encoding="utf-8")
        for example in ("Harbor Lane Cycles is a family workshop that offers bike repair for commuters and weekend riders.",
                        "Bike-Repair", "bicycle repair", "Bikerepair", "/en/"):
            self.assertIn(example, text)
        self.assertEqual(re.findall(r"\d", re.sub(r"\bH[1-6]s?\b|\bGA4\b", "", text)), [])


if __name__ == "__main__":
    unittest.main()
