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


AUDIT = ROOT / "skills/cro/references/audit.md"
V1 = ROOT / "skills/conversion-page-audit/SKILL.md"
TEMPLATE = ROOT / "skills/conversion-page-audit/references/report-template.md"
EVAL = ROOT / "evals/manual/audit-could-not-check.md"
INVOCATIONS = (
    "python3 ${CLAUDE_PLUGIN_ROOT}/skills/conversion-page-audit/scripts/page_facts.py <url>",
    "${CLAUDE_PLUGIN_DATA}/venv/bin/python ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/render_check.py <url> --out <dir>",
    "python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/speed_check.py <url> --out <file>",
    "python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/score.py <sheet> --json",
    'python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/search_check.py <url> --keyword "<keyword>" --out <dir>/search.json --json',
    "python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/client_check.py <client file>",
)


class AuditTextTests(unittest.TestCase):
    def test_audit_text_names_no_browser_mcp(self):
        for p in (AUDIT, V1, TEMPLATE, EVAL):
            t = p.read_text(encoding="utf-8")
            self.assertNotIn("mcp__", t, p.name)
            self.assertNotIn("Playwright MCP", t, p.name)

    def test_audit_text_uses_the_exact_script_invocations(self):
        t = AUDIT.read_text(encoding="utf-8")
        for s in INVOCATIONS:   # the six strings from the skeleton, verbatim
            self.assertIn(s, t)

    def test_audit_text_asks_the_four_questions_in_order(self):
        t = AUDIT.read_text(encoding="utf-8")
        pos = [t.index(q) for q in ("What's in it for me?", "Is it for me?", "Does it work?", "What do I do next?")]
        self.assertEqual(pos, sorted(pos))

    def test_audit_text_asks_where_the_traffic_comes_from(self):
        t = AUDIT.read_text(encoding="utf-8").lower()
        for s in ("where the traffic comes from", "cold outreach", "ads", "search"):
            self.assertIn(s, t)

    def test_audit_text_asks_the_mode_first(self):
        t = AUDIT.read_text(encoding="utf-8")
        self.assertNotIn("Page type is landing or homepage", t)
        self.assertLess(t.index("Search or Direct"), t.index("where the traffic comes from"))
        for s in ("GA4", "keyword", "variants", "never picks a keyword"):
            self.assertIn(s, t)

    def test_audit_runs_the_search_check_on_search_pages(self):
        t = AUDIT.read_text(encoding="utf-8")
        for s in ("search_check.py", "search.json", "## Search check", "Search pages only", "outside the score"):
            self.assertIn(s, t)
        self.assertLess(t.index("search_check.py"), t.index("score.py"))
        tpl = TEMPLATE.read_text(encoding="utf-8")
        self.assertLess(tpl.index("## Conversion Score"), tpl.index("## Search check"))
        self.assertLess(tpl.index("## Search check"), tpl.index("## Fix now"))

    def test_report_template_has_the_score_block(self):
        t = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("## Conversion Score", t); self.assertIn("not checked", t)
        self.assertLess(t.index("## Conversion Score"), t.index("## Fix now"))

    def test_v1_audit_step_3_uses_render_check(self):
        t = V1.read_text(encoding="utf-8")
        self.assertIn('${CLAUDE_PLUGIN_DATA}/venv/bin/python', t)
        self.assertIn("render_check.py", t); self.assertIn("/cro setup", t)

    def test_v1_audit_description_is_the_engine_role(self):
        d = re.search(r"^description:\s*(.+)$", V1.read_text(encoding="utf-8"), re.M).group(1)
        self.assertIn("Use when /cro audit runs it, or when an unscored audit is asked for by name", d)
        self.assertNotIn("audit this page", d); self.assertLessEqual(len(d), 250)


class AuditRulingsTest(unittest.TestCase):
    HEADER = ("**Mode:** [Search (keyword: <keyword>) / Direct] · **Page role:** [homepage / service / landing] · "
              "**Traffic:** [cold outreach / ads / search / mixed / unknown] · **Register:** [archetype]")
    NO_KEYWORD = "python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/search_check.py <url> --out <dir>/search.json --json"
    RENDER = "${CLAUDE_PLUGIN_DATA}/venv/bin/python ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/render_check.py <url> --out <dir>"

    def lines(self):
        return AUDIT.read_text(encoding="utf-8").splitlines()

    def steps(self):
        lines = self.lines()
        starts = [i for i, line in enumerate(lines) if re.match(r"\d+\. ", line)]
        return {int(lines[i].split(".")[0]): "\n".join(lines[i:j]) for i, j in zip(starts, starts[1:] + [len(lines)])}

    def test_audit_is_a_title_an_opening_and_fifteen_steps(self):
        lines = self.lines()
        self.assertTrue(lines[0].startswith("# ") and not lines[0].startswith("## "), lines[0])
        self.assertLess(len(lines), 100)
        self.assertEqual([int(line.split(".")[0]) for line in lines if re.match(r"\d+\. ", line)], list(range(1, 16)))
        self.assertEqual([line for line in lines[1:] if line.startswith("#")], [])
        opening = "\n".join(lines[1:lines.index(next(line for line in lines if line.startswith("1. ")))])
        for part in ("/cro audit <url> [mode] [keyword] [traffic] [page role] [register]",
                     "${CLAUDE_PLUGIN_ROOT}", "${CLAUDE_PLUGIN_DATA}", "full paths", "double quotes"):
            self.assertIn(part, opening)

    def test_step_11_carries_a_sample_sheet_that_score_accepts(self):
        sys.path.insert(0, str(ROOT / "skills" / "cro" / "scripts"))
        import score
        blocks = re.findall(r"```json\n(.*?)```", AUDIT.read_text(encoding="utf-8"), re.S)
        self.assertEqual(len(blocks), 1)
        step = self.steps()[11]
        self.assertIn("```json", step)
        self.assertIn("Never add the total by hand.", step)
        self.assertIn("Exit 2", step)
        sheet = json.loads(blocks[0])
        self.assertEqual(score.validate(sheet), [])
        self.assertEqual(list(sheet), ["page", "mode", "page_role", "traffic", "register", "factors"])
        self.assertEqual([f["id"] for f in sheet["factors"]], list(range(1, 11)))
        self.assertTrue(any("not_checked" in f for f in sheet["factors"]))

    def test_step_4_and_step_5_cover_no_keyword_and_failure_exits(self):
        steps = self.steps()
        self.assertIn(self.NO_KEYWORD, steps[4])
        for part in ("apparent target", "not confirmed", '--variant "<variant>"'):
            self.assertIn(part, steps[4])
        for n in (4, 5):
            self.assertRegex(steps[n], r"\bexits? 3\b")
            self.assertIn("Could not check", steps[n])

    def test_step_5_renders_through_render_check_only(self):
        step = self.steps()[5]
        for part in (self.RENDER, "Rendered evidence comes only from `render_check.py`, the one route that blocks analytics.",
                     "No form is sent and nothing is clicked.", "run `/cro setup`", "layout evidence only",
                     "render.json", "first-screen"):
            self.assertIn(part, step)

    def test_factor_10_and_factor_2_read_what_was_measured_or_given(self):
        steps = self.steps()
        for part in ("speed.json", "horizontal_scroll", "could not check", "not checked"):
            self.assertIn(part, steps[9])
        self.assertNotIn("tap target", AUDIT.read_text(encoding="utf-8").lower())
        self.assertIn("the ad, email or message", steps[1])
        self.assertIn("audience naming alone", steps[7])

    def test_header_line_and_output_paths(self):
        steps = self.steps()
        self.assertIn(self.HEADER, steps[12])
        for part in ("<project folder>/[C] Conversion Audit — <Page> — <YYYY-MM-DD>.md", "— client.md",
                     "<project folder>/_audit-data/<page-slug>-<YYYY-MM-DD>/", "score.json", "speed.json", "render/",
                     "search.json", "wherever your project keeps audit output", "outputs/"):
            self.assertIn(part, steps[14])

    def test_files_are_named_by_their_full_paths(self):
        steps = self.steps()
        for n, name in ((1, "cro/references/modes.md"), (2, "conversion-page-audit/references/evidence-rules.md"),
                        (8, "conversion-page-audit/references/audit-framework.md"), (10, "cro/references/score-anchors.md"),
                        (12, "conversion-page-audit/references/report-template.md"), (13, "cro/references/client-version.md")):
            self.assertIn("${CLAUDE_PLUGIN_ROOT}/skills/" + name, steps[n])

    def test_v1_rule_and_step_3(self):
        text = V1.read_text(encoding="utf-8")
        self.assertIn("\nallowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/conversion-page-audit/scripts/page_facts.py *) "
                      "Bash(${CLAUDE_PLUGIN_DATA}/venv/bin/python ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/render_check.py *)\n", text)
        self.assertIn("`" + self.RENDER + "`", text)
        step = " ".join(text[text.index("\n3. "):text.index("\n4. ")].split())
        for part in ("**Get a rendered capture with `" + self.RENDER + "`.**",
                     "Rendered evidence comes only from `render_check.py`, the one route that blocks analytics.",
                     '**if the venv is missing, every rendered-only check goes to Could not check, with the reason and "run `/cro setup`", never to Not a problem.**',
                     "exits 3", "Static markup cannot see layout, scroll-gated content, consent-gated tags, or anything CSS hides."):
            self.assertIn(part, step)

    def test_template_lists_the_ten_factors_and_keeps_lines_apart(self):
        sys.path.insert(0, str(ROOT / "skills" / "cro" / "scripts"))
        import score
        text = TEMPLATE.read_text(encoding="utf-8")
        rows = [line for line in text.splitlines() if re.match(r"\| \d+\. ", line)]
        self.assertEqual(rows, [f"| {n}. {name} | [0 to 10, or not checked] | [evidence, or what blocked the check] |"
                                for n, name in enumerate(score.FACTORS, start=1)])
        self.assertIn("An unscored audit leaves out this block", text[text.index("## Conversion Score"):text.index("## Search check")])
        block = text[text.index("## Search check"):text.index("## Fix now")]
        for label in ("**Keyword:**", "| Placement |", "[one row per placement", "**Headings:**", "**Body:**"):
            self.assertIn("\n\n" + label, block)


if __name__ == "__main__":
    unittest.main()
