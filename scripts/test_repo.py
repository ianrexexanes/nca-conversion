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

VERSION = "0.2.1"


def skill_version(path: Path) -> str:
    match = re.search(r"^metadata:\s*\n(?:[ \t]+.*\n)*?[ \t]+version:\s*(\S+)", path.read_text(encoding="utf-8"), re.M)
    return match.group(1).strip("\"'") if match else "<none>"


class RepoStructureTest(unittest.TestCase):
    def test_every_version_matches(self):
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
        for label in ("**Keyword:**", "| Placement |", "[one row per placement", "**Headings (whole page, footer included):**", "**Body:**"):
            self.assertIn("\n\n" + label, block)


CRO = ROOT / "skills/cro/SKILL.md"
KICKOFF = ROOT / "skills/cro/references/kickoff.md"
README = ROOT / "README.md"


def frontmatter_and_body(path):
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    marks = [i for i, line in enumerate(lines) if line.rstrip("\n") == "---"][:2]
    return "".join(lines[marks[0] + 1:marks[1]]), "".join(lines[marks[1] + 1:])


def cro_parts():
    text = CRO.read_text(encoding="utf-8")
    fm, body = frontmatter_and_body(CRO)
    name = re.search(r"^name:\s*(.+)$", fm, re.M).group(1)
    desc = re.search(r'^description:\s*"(.+)"$', fm, re.M).group(1)
    return text, fm, body, name, desc


def table_words(text):
    # first cell of each table row, backticks and <...> removed, first word kept
    rows = [line for line in text.splitlines() if line.startswith("|")][2:]
    return [re.sub(r"<[^>]*>", "", row.split("|")[1].replace("`", "")).split()[0] for row in rows]


class CroSkillTests(unittest.TestCase):
    def test_cro_skill_frontmatter(self):
        text, fm, body, name, desc = cro_parts()
        self.assertEqual(check_frontmatter.check_frontmatter(text), [])
        self.assertIn("name: cro", fm); self.assertIn("license: MIT", fm); self.assertIn("version: " + VERSION, fm)

    def test_cro_description_rules(self):
        text, fm, body, name, desc = cro_parts()
        self.assertTrue(desc.startswith("Use when")); self.assertLessEqual(len(desc), 500)
        for s in ("audit this page", "CRO audit"): self.assertIn(s, desc)

    def test_cro_body_under_500_words(self):
        text, fm, body, name, desc = cro_parts()
        self.assertLess(len(body.split()), 500)

    def test_cro_command_table_matches_slice_1(self):
        text, fm, body, name, desc = cro_parts()
        words = table_words(body)
        self.assertEqual(words, ["(none)", "audit", "setup", "doctor", "offer", "sweep", "research",
                                 "page", "hero", "wireframe", "vsl", "design", "check", "form",
                                 "data", "compare", "diagnose"])

    def test_every_routed_file_and_skill_exists(self):
        text, fm, body, name, desc = cro_parts()
        # each references/<x>.md and skills/cro/scripts/<x>.py named in the body exists
        named = re.findall(r"(?:skills/([a-z-]+)/)?(references|scripts)/([A-Za-z0-9_-]+\.(?:md|py))", body)
        self.assertTrue(named)
        for folder, kind, file in named:
            self.assertTrue((ROOT / "skills" / (folder or "cro") / kind / file).is_file(), f"{folder or 'cro'}/{kind}/{file}")
        # each of offer-architect, copy-sweeps, audience-research, conversion-page-build,
        # hook-lab, design-handoff named in the body has a SKILL.md
        for skill in ("offer-architect", "copy-sweeps", "audience-research", "conversion-page-build", "hook-lab", "design-handoff"):
            self.assertIn(skill, body)
            self.assertTrue((ROOT / "skills" / skill / "SKILL.md").is_file(), skill)

    def test_allowed_tools_name_existing_scripts(self):
        text, fm, body, name, desc = cro_parts()
        allowed = re.search(r"^allowed-tools:\s*(.+)$", fm, re.M).group(1)
        rules = re.findall(r"Bash\((.*?) \*\)", allowed)
        # the path after ${CLAUDE_PLUGIN_ROOT}/ exists
        for rule in rules:
            self.assertTrue((ROOT / rule.split("${CLAUDE_PLUGIN_ROOT}/", 1)[1]).is_file(), rule)
        # the scripts named are exactly setup, doctor, page_facts, render_check, speed_check, score, search_check, client_check
        self.assertEqual(sorted(Path(rule).stem for rule in rules),
                         sorted(["setup", "doctor", "page_facts", "render_check", "speed_check", "score", "search_check", "client_check"]))

    def test_listing_estimate_within_ceiling(self):
        # sum of len(name)+len(description) over every skills/*/SKILL.md, times 1140/3047, is <= 1350:
        # v1's 3,047 characters measured 1,140 tokens with `claude plugin details` (v1 plan, Task 8.4),
        # so characters/4 would under-count by about a third; the ceiling is about 3,608 characters
        paths = sorted((ROOT / "skills").glob("*/SKILL.md"))
        self.assertEqual(len(paths), 8)
        total = 0
        for path in paths:
            fm, body = frontmatter_and_body(path)
            total += len(re.search(r"^name:\s*(.+)$", fm, re.M).group(1))
            total += len(re.search(r'^description:\s*"(.+)"$', fm, re.M).group(1))
        self.assertLessEqual(total * 1140 / 3047, 1350)

    def test_kickoff_names_every_phase_and_the_questions(self):
        text = KICKOFF.read_text(encoding="utf-8").lower()
        for s in ("decide", "research", "brief and offer", "copy", "wireframe", "style guide", "design", "build",
                  "pre-launch", "launch", "after launch", "mode pending",
                  "own site or client", "page type", "mode", "keyword research", "offer state", "traffic source",
                  "language", "deadline", "material on hand"):
            self.assertIn(s, text)

    def test_manifests_name_the_front_door(self):
        plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        for description in (plugin["description"], market["plugins"][0]["description"]):
            self.assertIn("/nca-conversion:cro", description)


class CroRulingsTest(unittest.TestCase):
    ROOT_RULE = "Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/"
    FRONTMATTER = (
        "name: cro\n"
        "description: \"Use when the user types /nca-conversion:cro, asks to audit or score a landing page or homepage, "
        "says 'audit this page', 'CRO audit' or 'conversion audit', or starts a landing page or site project and wants "
        "the conversion process.\"\n"
        "license: MIT\n"
        "allowed-tools: " + " ".join([
            ROOT_RULE + "cro/scripts/setup.py *)", ROOT_RULE + "cro/scripts/doctor.py *)",
            ROOT_RULE + "conversion-page-audit/scripts/page_facts.py *)",
            "Bash(${CLAUDE_PLUGIN_DATA}/venv/bin/python ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/render_check.py *)",
            ROOT_RULE + "cro/scripts/speed_check.py *)", ROOT_RULE + "cro/scripts/score.py *)",
            ROOT_RULE + "cro/scripts/search_check.py *)", ROOT_RULE + "cro/scripts/client_check.py *)"]) + "\n"
        "metadata:\n"
        "  version: " + VERSION + "\n")
    ROWS = [("(none)", "`references/kickoff.md`", "ready"), ("`audit <url>`", "`references/audit.md`", "ready"),
            ("`setup`", "`references/setup.md`", "ready"), ("`doctor`", "`references/setup.md`", "ready"),
            ("`offer`", "the `offer-architect` skill", "ready (v1 skill)"), ("`sweep`", "the `copy-sweeps` skill", "ready (v1 skill)"),
            ("`research`", "the `audience-research` skill", "v1 engine until slice 2"),
            ("`page <brief>`", "the `conversion-page-build` skill", "v1 engine until slice 2"),
            ("`hero`", "the `hook-lab` skill", "v1 engine until slice 2"),
            ("`wireframe`", "the `design-handoff` skill", "v1 engine until slice 3"),
            ("`vsl`", "nothing yet", "not built yet, slice 2"), ("`design`", "nothing yet", "not built yet, slice 3"),
            ("`check`", "nothing yet", "not built yet, slice 3"), ("`form`", "nothing yet", "on the Later list"),
            ("`data`", "nothing yet", "on the Later list"), ("`compare`", "nothing yet", "on the Later list"),
            ("`diagnose`", "nothing yet", "on the Later list")]
    TABLE = "\n".join(["| Command | Goes to | Status |", "| --- | --- | --- |"] + [f"| {a} | {b} | {c} |" for a, b, c in ROWS]) + "\n"
    PHASES = "\n".join([
        "| Phase | Command | Slice 1 status |", "| --- | --- | --- |",
        "| 0. Decide | `/cro` with no command (this kickoff) | ready |",
        "| 1. Research | `/cro research` | v1 engine until slice 2; a Search project opens it with keyword research |",
        "| 2. Brief and offer | `/cro offer` | ready (v1 skill) |",
        "| 3. Copy | `/cro page`, `/cro hero` | v1 engines until slice 2 |",
        "| 4. Wireframe | `/cro wireframe` | v1 engine until slice 3 |",
        "| 5. Style guide | `/cro design` | not built yet, slice 3 |",
        "| 6. Design | `/cro design` | not built yet, slice 3 |",
        "| 7. Build | none | outside the plugin |",
        "| 8. Pre-launch | `/cro check` | not built yet, slice 3 |",
        "| 9. Launch | none | outside the plugin |",
        "| 10. After launch | `/cro audit` again | ready: quote both score lines for before and after |"]) + "\n"
    PATHS = ("Reference files write this plugin's folder as CLAUDE_PLUGIN_ROOT and its data folder as CLAUDE_PLUGIN_DATA, "
             "each inside a dollar sign and braces. The shell does not know those names: in every command you run and every "
             "file you read, put `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_DATA}` in their place.")

    def test_frontmatter_is_the_ruled_block(self):
        fm, body = frontmatter_and_body(CRO)
        self.assertEqual(fm, self.FRONTMATTER)

    def test_body_routes_and_states_its_rules(self):
        fm, body = frontmatter_and_body(CRO)
        self.assertIn(self.TABLE, body)
        self.assertEqual(len([line for line in body.splitlines() if line.startswith("|")]), 19)
        for part in ("`$0`", "`$ARGUMENTS`", self.PATHS, "Rendered evidence comes only from `render_check.py`",
                     "`python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/setup.py --data-dir ${CLAUDE_PLUGIN_DATA}`",
                     "`python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/doctor.py --data-dir ${CLAUDE_PLUGIN_DATA}`",
                     "`references/client-version.md`"):
            self.assertIn(part, " ".join(body.split()))
        self.assertRegex(body, r"(?i)no subagents")
        self.assertRegex(body, r"(?i)show (the|this) table")
        self.assertEqual(re.findall(r"\$[1-9]", body), [])
        self.assertNotIn(chr(0x2014), body); self.assertNotIn(chr(0x2013), body)

    def test_kickoff_parts(self):
        text = KICKOFF.read_text(encoding="utf-8")
        lines = text.splitlines()
        self.assertTrue(lines[0].startswith("# ") and not lines[0].startswith("## "), lines[0])
        self.assertLess(len(lines), 100)
        self.assertEqual([line for line in lines if line.startswith("## ")], ["## The first questions", "## The build phases"])
        self.assertIn(self.PHASES, text)
        self.assertLess(text.index(self.PHASES), len(text))
        self.assertGreater(text.index(self.PHASES), text.index("## The build phases"))
        for part in ("${CLAUDE_PLUGIN_ROOT}/skills/cro/references/modes.md", "mode pending: keyword research",
                     "never picks a keyword", "If your project has its own build SOP, follow its phases.",
                     "starts no subagents", "claude-seo", "seo-dataforseo", "GA4"):
            self.assertIn(part, " ".join(text.split()))
        self.assertNotIn(chr(0x2014), text); self.assertNotIn(chr(0x2013), text)
        self.assertNotIn("```", text)

    def test_readme_v2_section(self):
        text = README.read_text(encoding="utf-8")
        self.assertIn("\n## Version 2: the front door\n", text)
        start = text.index("\n## Version 2: the front door\n")
        self.assertLess(text.index("\n## Install\n"), start)
        self.assertLess(start, text.index("\n## The toggle, and why it exists\n"))
        section = text[start:text.index("\n## ", start + 1)]
        self.assertIn(self.TABLE, section)
        flat = " ".join(section.split())
        for part in ("/nca-conversion:cro", "/cro setup", "/cro doctor", "PageSpeed", "~/.config/nca-conversion/pagespeed.key",
                     "GET, HEAD and OPTIONS", "Chrome user agent", "blocked request", "Search page", "Direct page",
                     "outside the score", "never picks a keyword"):
            self.assertIn(part, flat)
        self.assertRegex(flat, r"(?i)no form")
        self.assertNotIn(chr(0x2014), section); self.assertNotIn(chr(0x2013), section)

    def test_readme_listing_sentence(self):
        flat = " ".join(README.read_text(encoding="utf-8").split())
        self.assertNotIn("about 1,140 tokens", flat)
        self.assertIn("For this plugin the listing stays under about 1,350 tokens, and `claude plugin details nca-conversion` "
                      "reports the live figure.", flat)

    def test_manifests_carry_the_ruled_descriptions(self):
        plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(plugin["description"], "Conversion-centred landing page work: audience research, offer design, page copy, "
                         "conversion audit, copy editing, hooks, and design handoff. Framework-driven, register-aware. "
                         "Start with /nca-conversion:cro.")
        entry = market["plugins"][0]["description"]
        self.assertTrue(entry.startswith("Eight skills for conversion-centred landing page work: "), entry[:40])
        self.assertTrue(entry.endswith(" Start with /nca-conversion:cro."), entry[-40:])
        self.assertEqual(market["metadata"]["description"], "The No-Code Alchemist's conversion and landing page toolkit")
        self.assertEqual((plugin["version"], market["metadata"]["version"]), (VERSION, VERSION))


class RoundFixesTest(unittest.TestCase):
    """Task 12: the approved round fixes, one check each."""

    @staticmethod
    def read(*parts):
        return ROOT.joinpath(*parts).read_text(encoding="utf-8")

    @staticmethod
    def factor_section(text, number):
        start = text.index("\n## %d. " % number)
        end = text.find("\n## ", start + 1)
        return text[start:end if end != -1 else len(text)]

    def test_heading_counts_say_whole_page(self):
        for parts in (("skills", "cro", "references", "modes.md"), ("skills", "cro", "references", "audit.md")):
            self.assertIn("whole page, footer included", " ".join(self.read(*parts).split()), "/".join(parts))

    def test_report_template_starts_with_its_own_frontmatter(self):
        text = self.read("skills", "conversion-page-audit", "references", "report-template.md")
        block = "---\ntype: audit\npage: <the audited URL>\ndate: <YYYY-MM-DD>\n---\n"
        self.assertIn(block, text)
        self.assertNotIn("author:", text)

    def test_factor_10_without_a_phone_scroll_scores_five_at_most(self):
        audit = " ".join(self.read("skills", "cro", "references", "audit.md").split())
        step = audit[audit.index("9. Factor 10"):audit.index("10. Missing")]
        self.assertIn("scores 5 at most", step)
        anchors = self.read("skills", "cro", "references", "score-anchors.md")
        self.assertIn("scores 5 at most", " ".join(self.factor_section(anchors, 10).split()))

    def test_readme_says_script_permissions_last_one_turn(self):
        text = " ".join(self.read("README.md").split())
        for part in ("turn that invokes", "https://code.claude.com/docs/en/skills", "Pre-approve tools for a skill",
                     "/nca-conversion:cro audit https://example.com/ mode: Direct; traffic: ads; page role: landing page"):
            self.assertIn(part, text)

    def test_two_anchor_gaps_are_closed(self):
        anchors = self.read("skills", "cro", "references", "score-anchors.md")
        self.assertIn("adds one point at most", " ".join(self.factor_section(anchors, 2).split()))
        low = [line for line in self.factor_section(anchors, 10).split("\n") if line.startswith("- **3:**")]
        self.assertEqual(len(low), 1)
        self.assertIn("over 600 ms (Source: Google, Total Blocking Time, 2019)", low[0])


def read(*parts):
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def flat(text):
    return " ".join(text.split())


def audit_step(number):
    audit = flat(read("skills", "cro", "references", "audit.md"))
    start = audit.index(" %d. " % number)
    end = audit.find(" %d. " % (number + 1), start)
    return audit[start:end if end != -1 else len(audit)]


def factor_bands(number):
    """The 3, 6 and 9 bullet lines of factor `number`'s section in score-anchors.md, in that order."""
    section = RoundFixesTest.factor_section(read("skills", "cro", "references", "score-anchors.md"), number)
    lines = section.split("\n")
    return [next(line for line in lines if line.startswith("- **%d:**" % band)) for band in (3, 6, 9)]


class FinalReviewFixesTest(unittest.TestCase):
    read = staticmethod(read)
    flat = staticmethod(flat)
    audit_step = staticmethod(audit_step)

    def test_step_5_reads_a_partial_render_by_viewport(self):
        step = self.audit_step(5)
        self.assertNotIn("When the script exits 3 the page did not load", step)
        for part in ("every viewport present under `viewports` is usable", "`could_not_check` holds the reason",
                     "Only what is missing goes to Could not check", "exit code alone decides nothing"):
            self.assertIn(part, step)


    def test_step_7_sends_a_blank_element_to_could_not_check(self):
        step = self.audit_step(7)
        for part in ("looks blank or unfinished (a map, a video, a 3D viewer)", "Could not check", "not scored low",
                     "in the other view first"):
            self.assertIn(part, step)

    def test_readme_says_a_blank_element_may_be_the_capture(self):
        text = self.flat(self.read("README.md"))
        section = text[text.index("### Rendered checks and your client's analytics"):]
        section = section[:section.index("### Script permissions")]
        self.assertIn("web workers are off", section.lower())
        self.assertIn("map, video or 3D viewer", section)

    def test_readme_does_not_promise_a_clean_analytics_record(self):
        text = self.flat(self.read("README.md"))
        self.assertNotIn("so a test visit never lands in the client's reports", text)
        self.assertIn("common analytics and tag hosts are blocked", text)
        self.assertIn("every request is logged in `network-log.json`", text)
        self.assertIn("a finite list is not a guarantee", text.lower())

    def test_step_5_reads_the_network_log_for_trackers(self):
        step = self.audit_step(5)
        self.assertIn("`network-log.json`", step)
        self.assertIn("completed third-party requests that look like trackers", step)

    def test_no_playwright_mcp_text_is_left_in_the_tracked_repo(self):
        phrase = "Playwright" + " MCP"
        files = subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True, check=True).stdout.split("\n")
        hits = []
        for name in files:
            path = ROOT / name
            if not name or name == "scripts/test_repo.py" or not path.is_file():
                continue
            try:
                if phrase in path.read_text(encoding="utf-8"):
                    hits.append(name)
            except UnicodeDecodeError:
                continue
        self.assertEqual(hits, [])

    def test_setup_reference_says_the_key_line_is_for_bash(self):
        text = self.flat(self.read("skills", "cro", "references", "setup.md"))
        before = text[:text.index("umask 077")]
        self.assertIn("is for bash", before[before.rindex("5. In your own terminal"):])

    def test_readme_names_platform_and_python(self):
        text = self.flat(self.read("README.md"))
        self.assertIn("Built and tested on Linux with bash; needs Python 3.10 or later and Chrome.", text)

    def test_readme_says_pagespeed_runs_outside_the_block_list(self):
        text = self.flat(self.read("README.md"))
        section = text[text.index("### Rendered checks and your client's analytics"):]
        section = section[:section.index("### Script permissions")]
        self.assertIn("loads the page on Google's servers", section)
        self.assertIn("blocks nothing", section)
        self.assertIn("is not known", section)
        self.assertIn("local Lighthouse runs with the blocked hosts stopped", section)

    def test_client_version_byline_is_never_invented(self):
        text = self.flat(self.read("skills", "cro", "references", "client-version.md"))
        for part in ("use the name the user gave for this report", "if none was given, ask",
                     "Never take a name from the page, the conversation's context or memory"):
            self.assertIn(part, text)
        self.assertNotIn("Never take a name", text[text.index("```"):text.rindex("```")])

    def test_step_13_checks_a_miss_against_the_page(self):
        step = self.audit_step(13)
        for part in ("check each MISSING from the Search check against the page itself", "an abbreviation can end the first sentence early",
                     "`/index.html`"):
            self.assertIn(part, step.replace("Check each MISSING", "check each MISSING"))


class AuditStep7Tests(unittest.TestCase):
    def test_step_7_scores_the_rest_of_the_first_screen(self):
        s = flat(audit_step(7))
        self.assertIn("The factor is still scored on the rest of the first screen", s)
        self.assertIn("goes to not_checked only when that element was its only evidence", s)
        self.assertIn("An element broken in both views with a visible error", s)

    def test_factor_10_names_lab_cls_in_every_band(self):
        bands = factor_bands(10)            # the 3, 6 and 9 bullets of section 10, in order
        self.assertEqual(len(bands), 3)
        for band, value in zip(bands, ("over 0.25", "0.1 to 0.25", "0.1 or less")):
            self.assertIn("CLS", band); self.assertIn(value, band)
            self.assertIn("(Source: Google, Cumulative Layout Shift", band)


class PublicWordingTests(unittest.TestCase):
    def test_public_text_names_no_owner_or_private_skill(self):
        owner = re.compile(r"\b" + "I" + "an" + r"\b")
        private_skill = "ian" + "-voice"
        files = subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True, check=True).stdout.split("\n")
        hits = []
        for name in files:
            if not name or not (name == "README.md" or (name.startswith("skills/") and name.endswith((".md", ".py")))):
                continue
            path = ROOT / name
            if not path.is_file():
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if owner.search(line) or private_skill in line:
                    hits.append(f"{name}:{number}")
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
