import fnmatch
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

VERSION = "0.4.0"


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

    def test_frontmatter_guard_docstring_names_what_runs_it(self):
        doc = " ".join(check_frontmatter.__doc__.split())
        self.assertNotIn("at commit time", doc)
        self.assertIn("when the repo test suite runs", doc)


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

    def test_manual_eval_runs_cro_audit_and_names_the_branch_it_can_earn(self):
        t = flat(EVAL.read_text(encoding="utf-8"))
        self.assertIn("Run `/nca-conversion:cro audit` against", t)
        self.assertNotIn("Run `nca-conversion:conversion-page-audit` against", t)
        self.assertIn("`/cro audit` can earn only the Could not check branch of (b)", t)
        self.assertIn("launch_render.py", t)
        self.assertIn("Read the score sheet's `not_checked` reasons", t)

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

    def test_step_one_asks_the_keyword_and_step_ten_applies_the_modes_line(self):
        steps = self.steps()
        self.assertIn("For a Search page also ask the keyword and its spelling variants", steps[1])
        self.assertIn("apply the line of the page's mode", steps[10])

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
        first = sheet["factors"][0]  # a Search H1 with the keyword and no promise stays at the low anchor (score-anchors.md)
        if "no result" in first["evidence"]:
            self.assertLessEqual(first["score"], 3)
        self.assertEqual(list(sheet), ["page", "plugin_version", "mode", "page_role", "traffic", "register", "factors"])
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
        for part in (self.RENDER, "Rendered evidence comes only from the plugin's guarded routes, which share the analytics guard in `cro_runtime.py`.",
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
        for part in ("<project folder>/Conversion Audit — <Page> — <YYYY-MM-DD>.md", "— client.md",
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
                     "Rendered evidence comes only from the plugin's guarded routes, which share the analytics guard in `cro_runtime.py`.",
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
        for label in ("**Keyword:**", "| Placement |", "[one row per placement", "**Headings (<headings_scope>):**", "**Body:**"):
            self.assertIn("\n\n" + label, block)
        self.assertIn("**Headings (<headings_scope>):**", audit_step(12))
        self.assertIn("| Title | [found / missing / not applicable / not checked] |", block)
        self.assertIn("\n\n**Apparent target:** [only when the keyword is not confirmed:", block)


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

    def test_cro_command_table_matches_slice_3(self):
        text, fm, body, name, desc = cro_parts()
        words = table_words(body)
        self.assertEqual(words, ["(none)", "audit", "setup", "doctor", "offer", "sweep", "research",
                                 "page", "hero", "wireframe", "vsl", "design", "check", "form",
                                 "data", "compare", "diagnose"])
        statuses = [line.split("|")[3].strip() for line in body.splitlines()
                    if line.startswith("| ") and not line.startswith(("| Command", "| ---"))]
        self.assertEqual(statuses, [row[2] for row in CroRulingsTest.ROWS])

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
        # the scripts named are exactly slice 2's nine plus slice 3's nine; form_consent.py is in none
        self.assertEqual(sorted(Path(rule).stem for rule in rules),
                         sorted(["setup", "doctor", "page_facts", "render_check", "speed_check", "score", "search_check", "client_check", "deck_check",
                                 "wire_check", "design_check", "site_check", "asset_text_check", "redirect_check", "clarity_export",
                                 "compare", "launch_render", "form_check"]))

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
        "says 'audit this page', 'review my landing page', 'CRO audit', 'conversion audit' or 'why isn't this converting', "
        "or starts a landing page or site project and wants the conversion process: research, page copy, a hero or a "
        "hero video script.\"\n"
        "license: MIT\n"
        "allowed-tools: " + " ".join([
            ROOT_RULE + "cro/scripts/setup.py *)", ROOT_RULE + "cro/scripts/doctor.py *)",
            ROOT_RULE + "conversion-page-audit/scripts/page_facts.py *)",
            "Bash(${CLAUDE_PLUGIN_DATA}/venv/bin/python ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/render_check.py *)",
            ROOT_RULE + "cro/scripts/speed_check.py *)", ROOT_RULE + "cro/scripts/score.py *)",
            ROOT_RULE + "cro/scripts/search_check.py *)", ROOT_RULE + "cro/scripts/client_check.py *)",
            ROOT_RULE + "cro/scripts/deck_check.py *)",
            ROOT_RULE + "cro/scripts/wire_check.py *)", ROOT_RULE + "cro/scripts/design_check.py *)",
            ROOT_RULE + "cro/scripts/site_check.py *)", ROOT_RULE + "cro/scripts/asset_text_check.py *)",
            ROOT_RULE + "cro/scripts/redirect_check.py *)", ROOT_RULE + "cro/scripts/clarity_export.py *)",
            ROOT_RULE + "cro/scripts/compare.py *)",
            "Bash(${CLAUDE_PLUGIN_DATA}/venv/bin/python ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/launch_render.py *)",
            "Bash(${CLAUDE_PLUGIN_DATA}/venv/bin/python ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/form_check.py *)"]) + "\n"
        "metadata:\n"
        "  version: " + VERSION + "\n")
    ROWS = [("(none)", "`references/kickoff.md`", "ready"), ("`audit <url>`", "`references/audit.md`", "ready"),
            ("`setup`", "`references/setup.md`", "ready"), ("`doctor`", "`references/setup.md`", "ready"),
            ("`offer`", "the `offer-architect` skill", "ready (v1 skill)"), ("`sweep`", "the `copy-sweeps` skill", "ready (v1 skill)"),
            ("`research`", "`references/research.md`, with the `audience-research` skill", "ready"),
            ("`page <brief>`", "`references/page.md`, with the `conversion-page-build` skill", "ready"),
            ("`hero`", "`references/hero.md`, with the `hook-lab` skill", "ready"),
            ("`wireframe`", "`references/wireframe.md`, with the `design-handoff` skill", "ready"),
            ("`vsl`", "`references/vsl.md`", "ready"), ("`design`", "`references/design.md`", "ready"),
            ("`check`", "`references/check.md`", "ready"), ("`form`", "`references/form.md`", "ready"),
            ("`data`", "`references/data.md`", "ready"), ("`compare`", "`references/compare.md`", "ready"),
            ("`diagnose`", "`references/diagnose.md`", "ready")]
    TABLE = "\n".join(["| Command | Goes to | Status |", "| --- | --- | --- |"] + [f"| {a} | {b} | {c} |" for a, b, c in ROWS]) + "\n"
    PHASES = "\n".join([
        "| Phase | Command | Status |", "| --- | --- | --- |",
        "| 0. Decide | `/cro` with no command (this kickoff); `/cro diagnose <url>` for a prospect's site | ready |",
        "| 1. Research | `/cro research`; `/cro data` when the site has GA4 or Clarity | ready; a Search project opens it with keyword research |",
        "| 2. Brief and offer | `/cro offer` | ready (v1 skill) |",
        "| 3. Copy | `/cro page`, `/cro hero`, `/cro vsl` | ready |",
        "| 4. Wireframe | `/cro wireframe` | ready |",
        "| 5. Style guide | `/cro design` | ready |",
        "| 6. Design | `/cro design` | ready |",
        "| 7. Build | none | outside the plugin |",
        "| 8. Pre-launch | `/cro check`, `/cro form` | ready |",
        "| 9. Launch | none | outside the plugin |",
        "| 10. After launch | `/cro audit` again, then `/cro compare` | ready |"]) + "\n"
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
        for part in ("`$0`", "`$ARGUMENTS`", self.PATHS, "Rendered evidence comes only from the plugin's guarded routes",
                     "`python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/setup.py --data-dir ${CLAUDE_PLUGIN_DATA}`",
                     "`python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/doctor.py --data-dir ${CLAUDE_PLUGIN_DATA}`",
                     "`references/client-version.md`"):
            self.assertIn(part, " ".join(body.split()))
        self.assertRegex(body, r"(?i)no subagents")
        self.assertRegex(body, r"(?i)show (the|this) table")
        self.assertEqual(re.findall(r"\$[1-9]", body), [])
        self.assertNotIn(chr(0x2014), body); self.assertNotIn(chr(0x2013), body)
        self.assertNotIn("Later list", body)
        self.assertIn("A row that names a reference file and a skill: read and follow the reference file; "
                      "its steps say when to use the skill.", " ".join(body.split()))
        self.assertIn("- Run `setup.py` only when the user typed `setup`. In any other command, report that the runtime is missing, "
                      "say to run `/cro setup`, and stop.", " ".join(body.split()))

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
        for part in ("/nca-conversion:cro", "/nca-conversion:cro setup", "/nca-conversion:cro doctor", "PageSpeed", "~/.config/nca-conversion/pagespeed.key",
                     "GET, HEAD and OPTIONS", "Chrome user agent", "blocked request", "Search page", "Direct page",
                     "outside the score", "never picks a keyword"):
            self.assertIn(part, flat)
        self.assertRegex(flat, r"(?i)no form")
        said = "A bare `/cro` can run the `cro` of another plugin, so every command in this README is written in full."
        self.assertIn(said, flat)
        self.assertNotRegex(" ".join(text.split()).replace(said, ""), r"(?<![:\w])/cro\b")
        self.assertNotIn(chr(0x2014), section); self.assertNotIn(chr(0x2013), section)

    def test_readme_lists_four_commands_ready_and_the_permissions_command(self):
        text = README.read_text(encoding="utf-8")
        start = text.index("\n## Version 2: the front door\n")
        section = text[start:text.index("\n## ", start + 1)]
        for word in ("`research`", "`page <brief>`", "`hero`", "`vsl`"):
            row = next(line for line in section.splitlines() if line.startswith("| " + word + " |"))
            self.assertTrue(row.endswith("| ready |"), row)
        sub = section[section.index("### Script permissions last one turn"):]
        sub = " ".join(sub[:sub.index("\n### ", 5)].split())
        for part in ("/nca-conversion:cro setup --permissions", ".claude/settings.local.json"):
            self.assertIn(part, sub)

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

    def test_heading_counts_say_their_scope(self):
        for parts in (("skills", "cro", "references", "modes.md"), ("skills", "cro", "references", "audit.md")):
            text = " ".join(self.read(*parts).split())
            self.assertIn("above the footer", text, "/".join(parts))
            self.assertIn("no footer element found", text, "/".join(parts))
            self.assertNotIn("whole page, footer " + "included", text, "/".join(parts))  # the old label is split on purpose, so this file never holds it as one string

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


def factor(number):
    return RoundFixesTest.factor_section(read("skills", "cro", "references", "score-anchors.md"), number)


def audit():
    return read("skills", "cro", "references", "audit.md")


def how_to_score():
    text = read("skills", "cro", "references", "score-anchors.md")
    start = text.index("\n## How to score")
    end = text.find("\n## ", start + 1)
    return text[start:end if end != -1 else len(text)]


def cpa_skill():
    return read("skills", "conversion-page-audit", "SKILL.md")


def audit_framework():
    return read("skills", "conversion-page-audit", "references", "audit-framework.md")


def form_audit():
    return read("skills", "conversion-page-audit", "references", "form-and-signup-audit.md")


def factor_bands(number):
    """The 3, 6 and 9 bullet lines of factor `number`'s section in score-anchors.md, in that order."""
    section = RoundFixesTest.factor_section(read("skills", "cro", "references", "score-anchors.md"), number)
    lines = section.split("\n")
    return [next(line for line in lines if line.startswith("- **%d:**" % band)) for band in (3, 6, 9)]


class AuditSlice2Tests(unittest.TestCase):
    def test_audit_reads_the_brief_or_names_its_absence(self):
        s = flat(audit_step(1))
        self.assertIn("If a Conversion Brief exists for the page, read it first", s)
        self.assertIn("If none exists, say so in the report's header as a limitation", s)

    def test_static_and_rendered_differ_is_a_finding(self):
        s = flat(audit_step(5))
        self.assertIn("When page_facts.py and render.json disagree on copy, such as a button or a heading, use the rendered text", s)
        self.assertIn("do not file it under Could not check", s)

    def test_facts_step_counts_buttons_from_links_and_saves_the_facts(self):
        s = flat(audit_step(3))
        self.assertIn("Count buttons from `links`", s)
        self.assertIn("--out <dir>/facts.json", s)
        self.assertIn("After the run, read `<dir>/facts.json`", s)
        self.assertIn("prints one summary line", s)
        v1 = flat((ROOT / "skills/conversion-page-audit/SKILL.md").read_text(encoding="utf-8"))
        self.assertIn("page_facts.py <url> --out <dir>/facts.json", v1)
        self.assertIn("read `<dir>/facts.json`", v1)

    def test_audit_names_the_form_and_test_references(self):
        self.assertIn("form-and-signup-audit.md", flat(audit_step(8)))
        self.assertIn("test-design.md", flat(audit()))

    def test_test_design_states_the_low_traffic_rule(self):
        t = flat((ROOT / "skills/conversion-page-audit/references/test-design.md").read_text(encoding="utf-8"))
        for s in ('Route confirmed defects to "Fix now"', "name the qualitative alternative",
                  "with no traffic context attached"):
            self.assertIn(s, t)

    def test_sheet_carries_plugin_version_and_the_folder_lists_facts(self):
        self.assertIn('"plugin_version": "%s"' % VERSION, audit_step(11))
        self.assertIn(".claude-plugin/plugin.json", flat(audit_step(11)))
        self.assertIn("facts.json", flat(audit_step(14)))

    def test_v1_files_say_links_holds_every_link(self):
        af, fa, sk = flat(audit_framework()), flat(form_audit()), flat(cpa_skill())
        self.assertIn("`page_facts.py`'s `ctas` array is the hint-matched part of its `links` array, which lists every link and "
                      "button in the static markup, in page order.", af)
        self.assertIn("Confirm a genuine absence from `links`, and from the rendered page if `render_check.py` ran, never from "
                      "`ctas` alone coming up short.", af)
        self.assertIn("The script's `links` array lists every `<a>` and `<button>` unfiltered, so confirm a genuine absence from "
                      "`links` or from the rendered page, never by `ctas` alone coming up short of anything social-auth-shaped.", fa)
        self.assertIn("It returns twelve keys parsed from static markup only: `url`, `title`, `meta_description`, `headings`, "
                      "`links`, `has_footer`, `ctas`, `forms`, `schema_types`, `images`, `lcp_candidates`, `notes`.", sk)
        for text in (af, fa):
            self.assertNotIn("does not expose", text)

    def test_anchors_read_the_slots_the_button_and_proof_beside_it(self):
        f3 = factor(3)
        self.assertIn("above the H1", f3)
        self.assertIn("directly under the H1", f3)
        self.assertIn("under the button", f3)
        self.assertIn("after nearly every major section", factor(4))
        self.assertIn("beside each button", factor(6))
        self.assertIn("Changed in 0.3.0: factors 3, 4 and 6", how_to_score())

    def test_step_9_says_what_a_null_measure_means(self):  # minor 111
        s = flat(audit_step(9))
        self.assertIn("A measure that `speed.json` holds as null (the performance score, LCP, TBT or CLS) was not measured", s)
        self.assertIn("When every measure is null, factor 10 is not checked.", s)


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
        self.assertIn("Built and tested on Linux with bash; needs Python 3.10 or later, and uses Chrome, or Playwright's bundled Chromium when Chrome is not installed.", text)

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
        for band, value in zip(bands, ("over 0.25", "over 0.1 and up to 0.25", "0.1 or less")):
            self.assertIn("CLS", band); self.assertIn(value, band)
            self.assertIn("(Source: Google, Cumulative Layout Shift", band)


class PublicWordingTests(unittest.TestCase):
    def test_public_text_names_no_owner_or_private_skill(self):
        owner = re.compile(r"\b" + "I" + "an" + r"\b")
        private_skill = "ian" + "-voice"
        files = subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True, check=True).stdout.split("\n")
        hits = []
        for name in files:
            if not name or not (name in ("README.md", "ATTRIBUTION.md") or (name.startswith("skills/") and name.endswith((".md", ".py")))):
                continue
            path = ROOT / name
            if not path.is_file():
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if owner.search(line) or private_skill in line:
                    hits.append(f"{name}:{number}")
        self.assertEqual(hits, [])

    def test_public_text_names_no_vault_and_no_c_file(self):
        needles = ("va" + "ult", "03 Pro" + "jects", "_Rese" + "arch", "[" + "C]")
        files = subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True, check=True).stdout.split("\n")
        hits = []
        for name in files:
            if not name or not (name in ("README.md", "ATTRIBUTION.md") or (name.startswith("skills/") and name.endswith((".md", ".py")))):
                continue
            path = ROOT / name
            if not path.is_file():
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if any(n in (line.lower() if n == needles[0] else line) for n in needles):
                    hits.append(f"{name}:{number}")
        self.assertEqual(hits, [])


class CarriedFrom021Tests(unittest.TestCase):
    def test_factor_10_middle_band_starts_above_the_good_limit(self):
        line = next(l for l in factor(10).split("\n") if l.startswith("- **6:**"))
        for part in ("over 0.1", "over 2.5 s", "over 200 ms"):
            self.assertIn(part, line)
        for part in ("2.5 to 4 s", "200 to 600 ms", "0.1 to 0.25"):
            self.assertNotIn(part, line)

    def test_two_sentences_keep_the_instruction_without_the_claim(self):
        forms = flat(read("skills", "conversion-page-audit", "references", "form-and-signup-audit.md"))
        self.assertNotIn("usually loses to a multi-step flow", forms)
        self.assertIn("multi-step", forms)
        self.assertIn("progress indicator", forms)
        psychology = flat(read("skills", "conversion-page-build", "references", "conversion-psychology.md"))
        self.assertNotIn("outperforms a long one", psychology)
        self.assertNotIn("clearly beats", psychology)
        self.assertIn("**Value stack**", psychology)
        self.assertIn("tiers", psychology)


class SetupPermissionsTests(unittest.TestCase):
    def test_setup_reference_names_the_permissions_step(self):
        text = (ROOT / "skills" / "cro" / "references" / "setup.md").read_text(encoding="utf-8")
        self.assertIn("merge", text.lower())  # the permissions section opens with "Merge": the printed rules go into the existing allow list
        for needle in ("--permissions", "settings.local.json", "claude plugin update",
                       "python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/setup.py --permissions --plugin-root ${CLAUDE_PLUGIN_ROOT} --data-dir ${CLAUDE_PLUGIN_DATA}"):
            self.assertIn(needle, text)


HERO_BUILD = ROOT / "skills" / "hook-lab" / "references" / "hero-build.md"
HEADLINE_FORMULAS = ROOT / "skills" / "hook-lab" / "references" / "headline-formulas.md"
HOOK_LAB = ROOT / "skills" / "hook-lab" / "SKILL.md"
HERO_HEADS = ["## The headline build", "## The subheadline build", "## The two proof slots", "## The button",
              "## By mode", "## By awareness", "## Register translation", "## Register notes"]


def hero_build():
    return HERO_BUILD.read_text(encoding="utf-8")


def hero_section(n):
    # the n-th "## " section (1 to 8, in HERO_HEADS order), from its heading to the next "## "
    text = hero_build()
    start = text.index(HERO_HEADS[n - 1])
    end = text.find("\n## ", start + 1)
    return text[start:] if end == -1 else text[start:end]


def table_rows(text):
    rows = [l for l in text.splitlines() if l.startswith("|")]
    cells = [[c.strip() for c in l.strip().strip("|").split("|")] for l in rows]
    return [c for c in cells if not all(re.fullmatch(r":?-{3,}:?", x) for x in c)][1:]


def hook_lab_body():
    return frontmatter_and_body(HOOK_LAB)[1]


def headline_formulas():
    return HEADLINE_FORMULAS.read_text(encoding="utf-8")


def group_g(text):
    start = text.index("## G. Imperatives, and what a button may say")
    end = text.find("\n## ", start + 1)
    return text[start:] if end == -1 else text[start:end]


class HeroBuildTests(unittest.TestCase):
    def test_hero_build_has_its_parts_in_order(self):
        lines = hero_build().splitlines()
        self.assertEqual([l for l in lines if l.startswith("## ")], HERO_HEADS)

    def test_headline_build_names_its_parts_and_the_without_option(self):
        for part in ("end result", "how long it takes", "how the buyer feels", "a figure the brief supports",
                     "without", "the objection the brief records"):
            self.assertIn(part, flat(hero_section(1)))

    def test_subheadline_is_pain_to_solution(self):
        for part in ("tired of", "the old way", "two or three ways"):
            self.assertIn(part, flat(hero_section(2)))

    def test_proof_slots_come_from_the_brief(self):
        for part in ("prooftop", "proof strip", "under the button", "above the H1", "directly under the H1",
                     "body face", "sentence case", "never a pill", "[NEEDED:", "never invent", "recorded departure"):
            self.assertIn(part, flat(hero_section(3)))

    def test_call_out_above_the_h1_leaves_the_strip_two_kinds_of_proof(self):
        self.assertIn("`prooftop` holds an audience call-out above the H1, the proof strip under the button carries "
                      "two kinds of proof", flat(hero_section(3)))
        self.assertIn("`prooftop` holds an audience call-out above the H1, the proof strip under the button carries "
                      "two kinds of proof", flat(hero))

    def test_button_rule(self):
        for part in ("what the reader gets", "the concrete next step", "the seller's own name for the offer",
                     "so what", "two to five words", "six or seven", "first person", "what is free",
                     "one label per variant", "the same click", "Submit", "Contact us", "Learn more",
                     "doubt reducers", "the worry that stops the click"):
            self.assertIn(part, flat(hero_section(4)))

    def test_by_mode_gives_both_modes(self):
        for part in ("keyword near the front", "one claim", "two lines on desktop", "never cut to meet a design limit", "one or two sentences",
                     "no stacked benefits", "up to five", "continues the ad or message"):
            self.assertIn(part, flat(hero_section(5)))

    def test_by_awareness_gives_cold_and_warm(self):
        for part in ("cold", "warm", "form hero", "image or video hero", "pain section"):
            self.assertIn(part, flat(hero_section(6)))

    def test_register_translation_covers_five_registers_without_blanks(self):
        rows = table_rows(hero_section(7))  # header: Register | Time and urgency | How the buyer feels | Stacked benefits | Button voice
        self.assertEqual([r[0] for r in rows], ["Conservative B2B (DACH)", "Technical / industrial",
                                                "Consumer / lifestyle", "Mission / nonprofit", "Direct-response"])
        self.assertTrue(all(cell.strip() for r in rows for cell in r))
        self.assertEqual(len(rows[0]), 5)

    def test_register_notes_gives_both_line_forms(self):
        self.assertIn(", because ", hero_section(8))
        self.assertIn("- None: the register changed no rule.", hero_section(8))

    def test_hook_lab_builds_a_page_hero_with_the_build(self):
        self.assertIn("references/hero-build.md", hook_lab_body())
        self.assertNotIn("Not the hero section", hook_lab_body())
        self.assertIn("hero-build.md", headline_formulas())

    def test_group_g_says_the_same_button_rule(self):
        g = flat(group_g(headline_formulas()))
        for part in ("what the reader gets or the concrete next step", "never the seller's own name for the offer",
                     "six or seven only when the outcome needs them"):
            self.assertIn(part, g)
        self.assertNotIn("A button names the transaction, never the feeling.", g)
        self.assertNotIn("seven-word button", g)

    def test_hero_line_row_follows_the_spec(self):
        formulas = headline_formulas()
        row = next(l for l in formulas.splitlines() if l.startswith("| **Hero line**"))
        for part in ("Aim for two lines on desktop", "Three or four lines on a phone is fine", "hero-build.md"):
            self.assertIn(part, row)
        self.assertNotIn("Two lines at a phone width", formulas)

    def test_email_subject_row_states_no_count(self):
        formulas = headline_formulas()
        self.assertNotIn("thirty-five characters", formulas)
        row = next(l for l in formulas.splitlines() if l.startswith("| **Email subject**"))
        self.assertTrue("Front-load" in row or "front-load" in row)


BUILD_REFERENCES = ROOT / "skills" / "conversion-page-build" / "references"
PLAYBOOKS = BUILD_REFERENCES / "section-playbooks.md"
PROOF_LIBRARY = BUILD_REFERENCES / "proof-library.md"
ARCHITECTURE = BUILD_REFERENCES / "page-architecture.md"
PAGE_TYPES = BUILD_REFERENCES / "page-types.md"
SECTION_TO_COMPONENT = ROOT / "skills" / "design-handoff" / "references" / "section-to-component.md"
ORDER_HEADERS = ("Order", "Deck section", "What the section does", "Playbooks that write it")


def md_section(path, heading):
    # heading is a whole heading line ("## Hero", "### 10. CTA"); the text runs from that line to the next
    # heading of the same or a higher level, or to the end of the file; "" when no line equals it
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    level = len(heading) - len(heading.lstrip("#"))
    for start, line in enumerate(lines):
        if line.rstrip() == heading:
            break
    else:
        return ""
    end = len(lines)
    for n in range(start + 1, len(lines)):
        found = re.match(r"(#+) ", lines[n])
        if found and len(found.group(1)) <= level:
            end = n
            break
    return "\n".join(lines[start:end])


def playbook(name):
    return md_section(PLAYBOOKS, "## " + name)


def proof_section(name):
    return md_section(PROOF_LIBRARY, "## " + name)


def architecture(name):
    return md_section(ARCHITECTURE, "## " + name)


def page_types(name):
    return md_section(PAGE_TYPES, "## " + name)


def s2c_section(name):
    return md_section(SECTION_TO_COMPONENT, "### " + name)


def split_cells(line):
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def order_rows(text):
    # the table whose header holds the four ORDER_HEADERS, read by header name:
    # one (deck section, what the section does, playbooks) tuple per body row
    block = []
    for line in text.splitlines() + [""]:
        if line.lstrip().startswith("|"):
            block.append(split_cells(line))
            continue
        if block and all(h in block[0] for h in ORDER_HEADERS):
            at = [block[0].index(h) for h in ORDER_HEADERS]
            body = [r for r in block[1:] if not all(re.fullmatch(r":?-+:?", c) for c in r)]
            return [tuple((r[i] if i < len(r) else "") for i in at[1:]) for r in body]
        block = []
    return []


class PageRulesTests(unittest.TestCase):
    def test_hero_row_points_at_the_build_and_names_its_register_changes(self):
        s = flat(playbook("Hero"))
        self.assertIn("hero-build.md", s)
        self.assertIn("Register notes", s)
        self.assertNotIn("stays understated", s)

    def test_problem_section_carries_pas_and_the_old_way(self):
        s = flat(playbook("Problem"))
        self.assertIn("Problem, Agitate, Solve", s)
        self.assertIn("the old way", s)

    def test_the_repeated_action(self):
        s = flat(playbook("Repeating the action"))
        for part in ("never more than one section away from the button", "the same action", "not a second action",
                     "every repeat goes to the same place", "every button leads to the form"):
            self.assertIn(part, s)

    def test_the_closer_is_a_mini_hero(self):
        s = flat(playbook("Closer"))
        for part in ("mini hero", "three to five bullets", "stacked proof", "real reasons", "Register translation"):
            self.assertIn(part, s)

    def test_header_compare_and_team_playbooks(self):
        for part in ("logo", "the one button", "no menu", "standard navigation"):
            self.assertIn(part, flat(playbook("Header")))
        for part in ("competitors", "the status quo", "checkable"):
            self.assertIn(part, flat(playbook("Compare")))
        for part in ("real names", "photos", "founder"):
            self.assertIn(part, flat(playbook("Team")))

    def test_every_section_names_its_visual(self):
        self.assertIn("names its visual", flat(playbook("A visual for every section")))

    def test_proof_placement(self):
        s = flat(proof_section("Where proof goes"))
        for part in ("prooftop", "proof strip", "beside each button", "wall of testimonials", "full name"):
            self.assertIn(part, s)

    def test_long_form_order_table_lists_the_deck_names_and_their_playbooks(self):
        order = architecture("The long-form order")
        rows = order_rows(order)
        self.assertEqual([r[0] for r in rows],
                         ["header", "hero", "pain", "proof", "value", "compare", "how", "team", "guarantee", "faq",
                          "closer"])
        for name, does, plays in rows:
            self.assertTrue(plays.strip(), name)
            for title in re.findall(r"`([^`]+)`", plays):
                self.assertTrue(playbook(title), (name, title))
        self.assertIn("four to eight value blocks", flat(order))
        self.assertIn("Objections", dict((r[0], r[2]) for r in rows)["faq"])

    def test_skeleton_by_awareness(self):
        s = flat(architecture("Skeleton by awareness"))
        for part in ("form hero", "image or video hero", "pain comes before proof", "proof comes before pain"):
            self.assertIn(part, s)

    def test_four_skeletons_in_words(self):
        s = flat(page_types("The four skeletons"))
        for part in ("image or video hero", "form hero", "e-commerce homepage", "e-commerce product page",
                     "not scored"):
            self.assertIn(part, s)

    def test_design_handoff_says_the_repeat_is_not_an_exit(self):
        s = flat(s2c_section("10. CTA"))
        self.assertIn("Repeating the page's one action after a section is not a second action", s)
        self.assertIn("the same label and the same target", s)

    def test_register_departures_from_one_action_go_in_register_notes(self):
        rows = {}
        for line in playbook("CTA").splitlines():
            if line.startswith("|"):
                cells = split_cells(line)
                rows[cells[0]] = flat(line)
        for register in ("Conservative B2B (DACH)", "Technical / industrial", "Mission / nonprofit"):
            self.assertIn(register, rows)
            self.assertIn("one action", rows[register], register)
            self.assertIn("Register notes", rows[register], register)
        self.assertIn("Register notes", flat(md_section(ARCHITECTURE, "### CTA")))
        self.assertIn("Register notes", flat(page_types("What doesn't fit any of these five")))


class DeckSectionsTest(unittest.TestCase):
    def test_deck_sections_match_page_architecture(self):
        sys.path.insert(0, str(ROOT / "skills" / "cro" / "scripts"))
        import deck_check
        self.assertEqual(list(deck_check.SECTIONS), [r[0] for r in order_rows(architecture("The long-form order"))])


def section(text, name):
    # the first heading line that is exactly `name` starts the section; it ends before the next heading of the
    # same or a higher level, or at the end of the text; "" when no heading matches
    lines = text.splitlines()
    start = level = None
    for n, line in enumerate(lines):
        found = re.match(r"(#{1,6}) (.*?)\s*$", line)
        if found and found.group(2) == name:
            start, level = n, len(found.group(1))
            break
    if start is None:
        return ""
    end = len(lines)
    for n in range(start + 1, len(lines)):
        found = re.match(r"(#{1,6}) ", lines[n])
        if found and len(found.group(1)) <= level:
            end = n
            break
    return "\n".join(lines[start:end])


def read_or_empty(*parts):
    try:
        return read(*parts)
    except FileNotFoundError:
        return ""


template = read_or_empty("skills", "audience-research", "assets", "conversion-brief-template.md")
audience_skill = read_or_empty("skills", "audience-research", "SKILL.md")
research_modes = read_or_empty("skills", "audience-research", "references", "research-modes.md")
research = read_or_empty("skills", "cro", "references", "research.md")
hero = read_or_empty("skills", "cro", "references", "hero.md")
page = read_or_empty("skills", "cro", "references", "page.md")
vsl = read_or_empty("skills", "cro", "references", "vsl.md")


def step_of(text, n):
    # the flattened text of top-level step n: from the line that starts `n. ` at column 0 to the line before the
    # next line that starts with digits and `. ` at column 0, or to the end; "" when the text is empty or step n is absent
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("%d. " % n):
            start = i
            break
    if start is None:
        return ""
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if re.match(r"\d+\. ", lines[i]):
            end = i
            break
    return flat("\n".join(lines[start:end]))


def output_format(text):
    # the content of the first fenced block in text: the lines between the opening and the closing fence, with the opening
    # line's indentation removed; the opening line is spaces, three or more backticks and an optional info string, the closing
    # line the same count of backticks with only spaces around it; "" when the text is empty or holds no fence
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"( *)(`{3,})[^`]*$", line)
        if not m:
            continue
        indent, fence = m.group(1), m.group(2)
        out = []
        for later in lines[i + 1:]:
            if later.strip() == fence:
                return "\n".join(out)
            out.append(later[len(indent):] if later.startswith(indent) else later.lstrip(" "))
        return ""
    return ""


class ResearchTests(unittest.TestCase):
    def test_research_step_3_reads_the_saved_facts(self):
        s = flat(step_of(read("skills", "cro", "references", "research.md"), 3))
        self.assertIn("--out <dir>/facts.json", s)
        self.assertIn("After the run, read `<dir>/facts.json`", s)
        self.assertIn("prints one summary line", s)

    def test_research_names_the_buyers_path_to_the_page_in_step_6_and_the_personas_section(self):
        self.assertIn("the buyer's path to the page", flat(step_of(read("skills", "cro", "references", "research.md"), 6)))
        self.assertIn("the path each one takes to the page", flat(section(template, "Personas")))

    def test_brief_template_has_the_new_parts_and_one_proof_section(self):
        for head in ("## Page modes and keywords", "## Traffic and awareness", "## Proof available", "## Visual inventory"):
            self.assertIn(head, template)
        self.assertNotIn("## Proof inventory", template)
        self.assertIn("| Page | Language | Mode | Keyword | Variants | Volume | Difficulty | Tool | Date checked |",
                      section(template, "Page modes and keywords"))
        self.assertIn("| Item | Source | May be shown | Where it goes |", section(template, "Proof available"))
        self.assertIn("all thirteen sections", flat(template))
        self.assertIn("Thirteen sections:", flat(audience_skill))

    def test_traffic_part_records_temperature_and_its_offer(self):
        for part in ("temperature", "cold", "warm", "hot", "the offer that suits it"):
            self.assertIn(part, section(template, "Traffic and awareness"))

    def test_research_modes_has_the_notebooklm_route(self):
        s = section(research_modes, "NotebookLM route")
        for part in ("optional", "skipped", "rewritten, never pasted", "sources"):
            self.assertIn(part, s)

    def test_research_procedure(self):
        for part in ("keyword research", "seo-dataforseo", "never picks a keyword", "per language", "awareness", "temperature",
                     "render_check.py", "voice of customer", "Proof available", "Visual inventory", "before the design tool opens"):
            self.assertIn(part, research)
        self.assertLess(len(research.splitlines()), 100)

    def test_research_opens_with_the_paths_note(self):
        self.assertIn("full paths", research.split("1. ")[0])


class HeroCommandTests(unittest.TestCase):
    def test_hero_asks_the_page_questions_first(self):
        for part in ("mode", "page role", "traffic", "awareness", "register", "language", "the one action"):
            self.assertIn(part, step_of(hero, 1))

    def test_hero_builds_three_variants_with_transformation_first(self):
        for part in ("hero-build.md", "three variants", "transformation", "a, b and c"):
            self.assertIn(part, hero)

    def test_hero_writes_a_label_per_variant(self):
        for part in ("cta.hook", "completes its own headline", "the same click", "cta.fud", "commitment point", "so what"):
            self.assertIn(part, flat(hero))

    def test_hero_says_never_invent_proof(self):
        self.assertIn("[NEEDED:", hero)
        self.assertIn("never invent", hero)
        self.assertIn("prooftop", hero)

    def test_hero_visual_is_the_real_product(self):
        self.assertIn("the real product or outcome", hero)
        self.assertIn("never stock", hero)

    def test_hero_writes_register_notes_and_checks_the_deck(self):
        self.assertIn("## Register notes", hero)
        self.assertIn('python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/deck_check.py "<deck>" --part hero', hero)

    def test_hero_routes_the_text_through_a_voice_skill(self):
        self.assertIn("humanizer", hero)
        self.assertIn("banned-vocabulary.md", hero)
        self.assertIn("German copy is flagged for the user's own check", flat(hero))


class PageCommandTests(unittest.TestCase):
    def test_page_asks_mode_traffic_and_awareness_first(self):
        for part in ("mode", "traffic", "awareness"):
            self.assertIn(part, step_of(page, 1))
        step = step_of(page, 1)
        asked = step[step.index("Ask once"):]
        self.assertLess(asked.index("the mode"), asked.index("the traffic"))
        self.assertLess(asked.index("the traffic"), asked.index("the awareness"))
        self.assertIn("separate from the mode", page)

    def test_page_picks_the_skeleton_and_order(self):
        for part in ("Skeleton by awareness", "The long-form order", "pain comes before proof", "proof comes before pain"):
            self.assertIn(part, page)

    def test_page_writes_the_hero_through_hero_md(self):
        self.assertIn("references/hero.md", page)

    def test_page_rules(self):
        for part in ("never more than one section away from the button", "every button leads to the same place",
                     "names its visual", "mini hero", "no menu", "FAQPage schema", "faq.q1", "answer-first sentence",
                     "deck_check.py", "/nca-conversion:cro sweep", "German copy is flagged for the user's own check"):
            self.assertIn(part, flat(page))


class PageDeckOrderTests(unittest.TestCase):
    def test_step_9_puts_the_header_keys_before_the_hero_keys(self):
        step = flat(step_of(read("skills", "cro", "references", "page.md"), 9))
        self.assertNotIn("then the header keys between", step)
        self.assertIn("The header keys go after the cta keys and before the hero keys, and every other section follows in the order step 2 chose", step)


class PendingModeTests(unittest.TestCase):
    def test_page_and_hero_step_1_stop_for_a_mode_pending_page_and_the_kickoff_goes_on(self):
        rule = "When the brief records the page as `mode pending: keyword research`, write nothing and name `/cro research`."
        for name in ("page", "hero"):
            self.assertIn(rule, flat(step_of(read("skills", "cro", "references", name + ".md"), 1)), name)
        self.assertIn("the kickoff goes on with the other pages and any phase that needs no copy",
                      flat(read("skills", "cro", "references", "kickoff.md")))


class SecondLanguageFlagTests(unittest.TestCase):
    def test_french_and_italian_copy_is_flagged_where_german_copy_is(self):
        flag = "Copy in French or Italian is flagged for the user's own check"
        for name in ("hero", "page", "vsl"):
            text = flat(read("skills", "cro", "references", name + ".md"))
            self.assertIn("German copy is flagged for the user's own check", text, name)
            self.assertIn(flag, text, name)
        text = flat(read("skills", "cro", "references", "client-version.md"))
        self.assertIn("German text goes to the user for their own check before it is sent", text)
        self.assertIn("French or Italian text goes the same way", text)


class VslTests(unittest.TestCase):
    def test_vsl_output_headings_in_order(self):
        heads = [l for l in output_format(vsl).splitlines() if l.startswith("## ")]
        self.assertEqual(heads, ["## Hook", "## The deliverable on screen", "## Proof", "## The ask", "## Shot list"])

    def test_vsl_rules(self):
        for part in ("plays on a click", "never autoplay with sound", "captions", "the exact deliverable",
                     "only as strong as its script", "a graphic of the deliverable", "the page's one action"):
            self.assertIn(part, flat(vsl))
        self.assertIsNone(re.search(r"\d+\s?%", vsl))

    def test_vsl_opens_with_the_paths_note(self):
        self.assertIn("full paths", vsl.split("1. ")[0])

    def test_vsl_routes_the_text_through_a_voice_skill(self):
        self.assertIn("humanizer", vsl)
        self.assertIn("banned-vocabulary.md", vsl)
        self.assertIn("German copy is flagged for the user's own check", flat(vsl))


class Slice2RoundFixesTests(unittest.TestCase):
    def test_direct_response_service_page_keeps_its_menu(self):
        rows = [l for l in playbook("Header").splitlines() if l.startswith("| Direct-response |")]
        self.assertEqual(len(rows), 1)
        self.assertIn("homepage or service page", rows[0])
        self.assertIn("standard navigation", rows[0])

    def test_hero_step_4_allows_an_audience_call_out(self):
        step = flat(step_of(hero, 4))
        self.assertIn("audience call-out", step)
        self.assertIn("the strip still carries proof", step)

    def test_hero_build_benefit_count_has_no_unsourced_reason(self):
        text = flat(read("skills", "hook-lab", "references", "hero-build.md"))
        self.assertIn("naming two or three ways it does.", text)
        self.assertNotIn("reads as thin", text)
        self.assertNotIn("stops being read", text)

    def test_hero_build_names_no_plan_stage(self):
        text = read("skills", "hook-lab", "references", "hero-build.md")
        self.assertNotIn("slice", text.casefold())
        self.assertIn("the design step writes it down as a ruling line with its reason", flat(text))

    def test_problem_playbook_has_no_length_claim(self):
        text = flat(read("skills", "conversion-page-build", "references", "section-playbooks.md"))
        self.assertIn("Warm visitors take proof before pain", text)
        self.assertNotIn("runs shorter", text)

    def test_design_handoff_names_its_file_cleanly(self):
        text = flat(read("skills", "design-handoff", "SKILL.md"))
        self.assertIn("A single handoff document: `Design Handoff — <Page>.md`, in the page's folder in your project, "
                      "or wherever the project keeps specs.", text)
        self.assertNotIn("; anywhere else, wherever the project", text)


class FixWave1Tests(unittest.TestCase):
    def test_build_points_the_page_at_the_long_form_order(self):
        text = flat(read("skills", "conversion-page-build", "SKILL.md"))
        self.assertIn("The long-form order", text)
        self.assertIn("page-architecture.md", text)
        self.assertNotRegex(text, r"page-architecture\.md` is that order")

    def test_hero_build_by_mode_holds_the_headline_ladder(self):
        text = flat(md_section(ROOT / "skills" / "hook-lab" / "references" / "hero-build.md", "## By mode"))
        for part in ("50 characters", "51 to 90", "over 90"):
            self.assertIn(part, text)

    def test_test_comments_name_no_process_words(self):
        bad = re.compile("the " + "controller|plugin " + r"gate|README\.md " + r"line \d")
        hits = []
        for path in sorted(ROOT.rglob("test_*.py")):
            if ".git" in path.parts:
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if bad.search(line):
                    hits.append("%s:%d" % (path.relative_to(ROOT), number))
        self.assertEqual(hits, [])

    def test_deck_form_says_to_leave_the_variants_key_out_when_empty(self):
        for name in ("hero.md", "page.md"):
            self.assertIn("leave the key out when there are none", flat(read("skills", "cro", "references", name)), name)

    def test_page_reads_the_brief_the_command_names(self):
        self.assertIn("the brief the command names", step_of(page, 1))

    def test_kickoff_offers_the_five_traffic_values(self):
        self.assertIn("6. **Traffic source.** Cold outreach, ads, search, email or mixed?", read("skills", "cro", "references", "kickoff.md"))

    def test_readme_says_what_the_copy_deck_is(self):
        text = flat(read("README.md"))
        self.assertIn("copy deck", text)
        self.assertIn("deck_check.py", text)


class DesignRulesTests(unittest.TestCase):
    HEADS = ["## The six rules", "## Measured thresholds", "## What design never does", "## Design skills, by mode", "## Rulings"]

    def setUp(self):
        self.text = read_or_empty("skills", "design-handoff", "references", "design-rules.md")

    def section(self, n):
        parts = re.split(r"^## .*$", self.text, flags=re.M)
        return flat(parts[n]) if len(parts) > n else ""

    def test_it_says_only_what_the_launch_gate_and_check_really_read(self):
        text = flat(self.text)
        self.assertNotIn("the launch gate reads the same file", text)
        self.assertIn("`/cro check` measures what it can of them on the built page. Those commands point here", text)
        self.assertIn("`/cro design` guards the blur test on the main button", text)
        self.assertNotIn("`/cro design` and `/cro check` guard the blur test", text)

    def test_headings_in_order(self):
        self.assertEqual([l.strip() for l in self.text.splitlines() if l.startswith("## ")], self.HEADS)

    def test_six_rules(self):
        for part in ("three to four times the body size", "dark grey, not black", "a directional cue",
                     "emotional, social and functional", "no carousels", "tight hero padding on a phone"):
            self.assertIn(part, self.section(1))

    def test_thresholds(self):
        for part in ("4.5:1", "3:1", "24 by 24", "44 by 44", "https://www.w3.org/TR/WCAG22/"):
            self.assertIn(part, self.section(2))

    def test_never_list(self):
        for part in ("award-chasing", "scroll-jacking", "preloaders", "sliders", "autoplaying background video"):
            self.assertIn(part, self.section(3))

    def test_never_list_says_what_check_detects(self):
        s = self.section(3)
        self.assertIn("`/cro check` reports sliders and autoplaying video", s)
        self.assertIn("design-time rule", s)
        self.assertNotIn("guard this list", s)

    def test_ladder_in_order(self):
        s = self.section(4)
        rungs = [s.find(w) for w in ("WCAG 2.2", "conversion rules", "Impeccable", "Hallmark", "Taste", "Emil")]
        self.assertNotIn(-1, rungs)
        self.assertEqual(rungs, sorted(rungs))
        for part in ("Direct page", "Search page", "design authority", "never apply to a conversion page", "built code"):
            self.assertIn(part, s)

    def test_rulings(self):
        s = self.section(5)
        self.assertIn("- <skill> <rule>: <what this page does instead>, because <conversion rule>; mode <search or direct>.", s)
        for part in ("prooftop", "audience call-out", "body face", "sentence case", "matched to a ruling line",
                     "/hallmark:hallmark audit"):
            self.assertIn(part, s)

    def test_rung_one_states_the_safety_rule_as_the_spec_does(self):
        row = next(l for l in self.text.splitlines() if l.startswith("| 1. WCAG"))
        self.assertIn("blocked", row)
        self.assertIn("tags", row)
        self.assertNotIn("nothing in the design blocks analytics", row)

    def test_handoff_points_to_the_rules(self):
        self.assertIn("references/design-rules.md", read("skills", "design-handoff", "SKILL.md"))


class WireframeTests(unittest.TestCase):
    DH = ROOT / "skills" / "design-handoff"

    def setUp(self):
        sys.path.insert(0, str(ROOT / "skills" / "cro" / "scripts"))
        self.addCleanup(sys.path.pop, 0)

    def layout_table(self):
        # the rows of the layout table under "## Layout families by section", by header name:
        # one (section, families) pair per body row, in order
        block = [split_cells(l) for l in md_section(SECTION_TO_COMPONENT, "## Layout families by section").splitlines()
                 if l.lstrip().startswith("|")]
        if not block:
            return []
        head = [c.lower() for c in block[0]]
        section_at = head.index("section")
        families_at = next(i for i, c in enumerate(head) if c.startswith("famil"))
        return [(re.sub(r"[`*]", "", r[section_at]), [f.strip() for f in r[families_at].split(",")]) for r in block[2:]]

    def test_layout_table_sections_are_the_deck_sections(self):
        import deck_check
        self.assertEqual([s for s, _ in self.layout_table()], list(deck_check.SECTIONS))

    def test_layout_table_uses_only_the_known_families_and_every_one_of_them(self):
        import wire_check
        used = {f for _, families in self.layout_table() for f in families}
        self.assertTrue(used <= set(wire_check.LAYOUT_FAMILIES), used - set(wire_check.LAYOUT_FAMILIES))
        self.assertEqual(used, set(wire_check.LAYOUT_FAMILIES))

    def test_the_checker_allows_what_the_table_allows(self):
        import wire_check
        self.assertEqual({s: tuple(f) for s, f in self.layout_table()}, dict(wire_check.LAYOUT_RULES))

    def test_the_hero_may_not_be_a_logo_strip(self):
        self.assertNotIn("logo-strip", dict(self.layout_table())["hero"])

    def test_the_table_names_the_v1_section_each_row_replaces(self):
        rows = [r for r in md_section(SECTION_TO_COMPONENT, "## Layout families by section").splitlines() if r.startswith("| `")]
        text = flat(" ".join(rows))
        for new in ("header", "compare", "team"):
            self.assertIn("new in v2", flat(next(r for r in rows if r.startswith("| `%s`" % new))))
        for part in ("1. Hero", "2. Problem", "7. Proof", "3. Outcome", "4. Solution", "6. Value stack", "5. Mechanism",
                     "9. Guarantee", "11. FAQ", "8. Objections", "10. CTA"):
            self.assertIn(part, text)

    def test_icon_cards_are_right_for_three_to_six_parallel_items_the_visual_field_names(self):
        problem = flat(s2c_section("2. Problem"))
        self.assertIn("The over-add", problem)
        self.assertIn("three to six parallel items, and the visual field names them", problem)
        self.assertIn("three to six parallel items, and the visual field names them",
                      flat(md_section(SECTION_TO_COMPONENT, "## Layout families by section")))

    def test_design_handoff_names_paper_and_figma_only_as_older_files(self):
        text = (self.DH / "SKILL.md").read_text(encoding="utf-8")
        front, body = text.split("\n---", 2)[0], text.split("\n---", 2)[-1]
        description = next(l for l in front.splitlines() if l.startswith("description:"))
        self.assertIn("Paper spec", description)
        self.assertIn("Figma spec", description)
        self.assertIn("Paper", body)
        for path in sorted(self.DH.rglob("*.md")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if "Figma" in line and not line.startswith("description:"):
                    self.assertIn("older", line.lower(), "%s: %s" % (path.name, line[:80]))

    def test_the_readme_skill_list_names_paper_for_design_handoff(self):
        lines = read("README.md").splitlines()
        start = next(i for i, l in enumerate(lines) if l.startswith("- **`design-handoff`**"))
        item = [lines[start]]
        for line in lines[start + 1:]:
            if not line.startswith("  ") or not line.strip():
                break
            item.append(line.strip())
        self.assertIn("Paper", " ".join(item))

    def test_the_refinement_spec_is_named_for_paper_and_nothing_links_the_old_name(self):
        self.assertTrue((self.DH / "references" / "paper-refinement-spec.md").is_file())
        self.assertFalse((self.DH / "references" / ("figma-refinement" + "-spec.md")).exists())
        old = "figma-refinement" + "-spec"
        found = [str(p.relative_to(ROOT)) for p in ROOT.rglob("*")
                 if p.is_file() and ".git" not in p.relative_to(ROOT).parts and p.suffix in (".md", ".py", ".json", ".html", ".txt")
                 and old in p.read_text(encoding="utf-8", errors="replace")]
        self.assertEqual(found, [])
        self.assertIn("paper-refinement-spec.md", read("ATTRIBUTION.md"))

    def test_the_worked_hero_example_does_not_call_the_proof_strip_decoration(self):
        t = flat(read("skills", "design-handoff", "references", "paper-refinement-spec.md"))
        example = t[t.index("## Worked example"):]
        self.assertNotIn("proof strip is decoration", example)
        self.assertIn("4 badge row", example)

    def test_wireframe_reference_names_the_method(self):
        text = flat(read("skills", "cro", "references", "wireframe.md"))
        for part in ("wire_check.py", "--variant", "get_guide", "finish_working_on_nodes", "1440", "390", "a visual per section",
                     "one frame per variant", "design-rules.md", "directional cue", "carousel", "deck_check.py", "--final"):
            self.assertIn(part, text)
        self.assertRegex(text, r"When Impeccable or Taste is on, take direction from them as `design-rules\.md` ranks them")
        self.assertIn("name any that were off in the report", text)

    def test_wireframe_reference_runs_wire_check_again_after_the_notes_block(self):
        raw = read("skills", "cro", "references", "wireframe.md")
        step8 = flat(re.search(r"^8\. (.*(?:\n(?!\d+\. |\n).*)*)", raw, re.M).group(1))
        self.assertIn("wire_check.py", step8)
        self.assertRegex(step8, r"again.{0,80}notes|notes.{0,80}again")

    def test_wireframe_reference_says_a_none_visual_carries_no_figure(self):
        text = flat(read("skills", "cro", "references", "wireframe.md"))
        self.assertIn("A section whose visual line in the deck starts with `none` carries no figure.", text)

    def test_wireframe_reference_places_prooftop_by_mode(self):
        text = flat(read("skills", "cro", "references", "wireframe.md"))
        self.assertIn("The `prooftop` element comes before the H1 on a Direct page and after it on a Search page.", text)

    def test_wireframe_reference_names_every_rule_the_checker_prints_and_fixes_the_second_run(self):
        script = read("skills", "cro", "scripts", "wire_check.py")
        rules = set(re.findall(r'add\("(?:FAIL|WARN)",[^,]+,\s*"([A-Z_]+)"', script))
        self.assertGreaterEqual(len(rules), 11, rules)
        raw = read("skills", "cro", "references", "wireframe.md")
        text = flat(raw)
        self.assertEqual([r for r in sorted(rules) if "`%s`" % r not in text], [])
        step5 = flat(re.search(r"^5\. .*$", raw, re.M).group(0))
        self.assertIn("A `NOTES` WARN at this step only means the notes block is not written yet", step5)
        step8 = flat(re.search(r"^8\. .*$", raw, re.M).group(0))
        self.assertIn("Every FAIL of the second run is fixed before the frames are reported", step8)

    def test_wireframe_reference_reads_the_nav_as_a_list(self):
        text = flat(read("skills", "cro", "references", "wireframe.md"))
        self.assertIn("`<ns>.header.nav` is a list split on semicolons, and each label is its own link", text)


class DesignTests(unittest.TestCase):
    def setUp(self):
        self.text = flat(read_or_empty("skills", "cro", "references", "design.md"))

    def test_steps_4_and_11_name_the_skip_when_hallmark_is_not_on(self):
        raw = read_or_empty("skills", "cro", "references", "design.md")
        skip = "Hallmark audit skipped: Hallmark is not on"
        self.assertIn(skip, flat(step_of(raw, 11)))
        self.assertIn("Without Hallmark, write", flat(step_of(raw, 11)))
        self.assertIn("Hallmark's four questions skipped: Hallmark is not on", flat(step_of(raw, 4)))

    def test_it_points_to_the_rules_and_restates_none(self):
        self.assertIn("design-rules.md", self.text)
        rules = flat(read("skills", "design-handoff", "references", "design-rules.md")).lower().split()
        mine = self.text.lower().split()
        shared = {" ".join(mine[i:i + 8]) for i in range(len(mine) - 7)} & {" ".join(rules[i:i + 8]) for i in range(len(rules) - 7)}
        self.assertEqual(sorted(shared), [])

    def test_it_names_the_checks_and_the_hand_offs(self):
        for part in ("design_check.py", "--blur", "## Design rulings", "sloplint.mjs", "matched to a ruling line",
                     "/hallmark:hallmark audit", "get_tokens", "Hallmark lint skipped", "most visible"):
            self.assertIn(part, self.text)

    def test_hallmarks_four_questions_are_answered_from_the_brief(self):
        paragraph = next((p for p in re.split(r"\n\s*\n", read_or_empty("skills", "cro", "references", "design.md"))
                          if "brief" in p.lower() and all(re.search(r"\b%s\b" % w, p, re.I) for w in ("material", "audience", "use", "tone"))), "")
        self.assertTrue(paragraph)

    def test_it_asks_which_token_is_which_colour(self):
        self.assertRegex(self.text, r"which token is the text, background, action and action-text colour")

    def test_it_does_not_name_emil(self):
        self.assertTrue(self.text)
        self.assertNotIn("Emil", self.text)


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.raw = read_or_empty("skills", "cro", "references", "check.md")
        self.text = flat(self.raw)

    def steps(self):
        return [(int(m.group(1)), flat(m.group(2))) for m in re.finditer(r"^(\d+)\. (.*(?:\n(?!\d+\. |\n).*)*)", self.raw, re.M)]

    def test_it_opens_with_the_paths_note(self):
        self.assertRegex(self.text, r"This is the procedure `/cro check` follows\. It writes the plugin's folder as `\$\{CLAUDE_PLUGIN_ROOT\}`")

    def test_it_names_every_gate_in_order_with_its_invocation(self):
        gates = ("deck_check.py", "client_check.py", "site_check.py", "asset_text_check.py", "redirect_check.py", "launch_render.py",
                 "search_check.py", "speed_check.py", "/nca-conversion:cro form")
        first = [next((n for n, body in self.steps() if gate in body), None) for gate in gates]
        self.assertNotIn(None, first, list(zip(gates, first)))
        self.assertEqual(first, sorted(first))
        for part in ("--final", "--visible-text", "--dist", "--url", "--deck", "--map", "--pages", "--forbid", "--dir", "--cases"):
            self.assertIn(part, self.text)

    def test_the_copy_gate_comes_first_and_runs_the_deck_check_before_the_client_check(self):
        steps = self.steps()
        self.assertTrue(steps)
        self.assertIn("deck_check.py", steps[0][1])
        self.assertLess(steps[0][1].index("deck_check.py"), steps[0][1].index("client_check.py"))
        self.assertIn("deck_check.py", self.text.split("client_check.py")[0])
        self.assertIn("--visible-text", steps[0][1] + " " + steps[1][1])

    def test_it_cites_the_pages_the_noindex_rule_rests_on(self):
        for url in ("developers.google.com/search/docs/crawling-indexing/block-indexing",
                    "developers.google.com/search/docs/crawling-indexing/google-special-case-crawlers", "support.google.com/google-ads",
                    "support.google.com/adspolicy"):
            self.assertIn(url, self.text)
        self.assertIn("UNVERIFIED", self.text)

    def test_it_names_emils_skills_as_an_optional_review_of_motion(self):
        paragraphs = re.split(r"\n\s*\n", self.raw)
        self.assertTrue(any("Emil" in p and "optional" in p.lower() and "motion" in p.lower() and "design principle" in p.lower()
                            for p in (flat(q) for q in paragraphs)) or any(
            "Emil" in body and "optional" in body.lower() and "motion" in body.lower() for _, body in self.steps()))

    def test_it_reports_one_row_per_gate_with_pass_fail_or_skipped(self):
        for word in ("PASS", "FAIL", "SKIPPED"):
            self.assertIn(word, self.raw)
        self.assertRegex(self.text, r"one (report )?row (for|per) (each|every) gate")

    def test_the_gates_it_names_exist(self):
        for name in ("site_check.py", "asset_text_check.py", "redirect_check.py", "deck_check.py", "client_check.py", "search_check.py",
                     "speed_check.py", "launch_render.py"):
            self.assertTrue((ROOT / "skills" / "cro" / "scripts" / name).is_file(), name)

    def step(self, n):
        return dict(self.steps())[n]

    def test_step_6_passes_the_url_on_a_built_page_and_sets_the_row_result(self):
        body = self.step(6)
        self.assertIn("--url", body)
        self.assertIn("NOT CHECKED", body)
        self.assertRegex(body, r"MISSING placement.{0,40}FAIL")
        self.assertRegex(body, r"heading counts? never fail")


    def test_step_10_lists_a_noindex_sent_as_a_header_among_what_the_checks_cannot_see(self):
        self.assertIn("a noindex sent as an `X-Robots-Tag` header", self.step(10))


    def test_step_2_says_a_live_run_fetches_every_same_origin_link_in_full(self):
        self.assertIn("`LINK` check on a live run fetches every same-origin link in full", self.step(2))


class FormTests(unittest.TestCase):
    def setUp(self):
        self.raw = read_or_empty("skills", "cro", "references", "form.md")
        self.text = flat(self.raw)

    def steps(self):
        return [(int(m.group(1)), flat(m.group(2))) for m in re.finditer(r"^(\d+)\. (.*(?:\n(?!\d+\. |\n).*)*)", self.raw, re.M)]

    def test_it_opens_with_the_paths_note(self):
        self.assertRegex(self.text, r"This is the procedure `/cro form` follows\. It writes the plugin's folder as `\$\{CLAUDE_PLUGIN_ROOT\}`")

    def test_it_carries_numbered_steps(self):
        self.assertGreaterEqual(len(self.steps()), 4)

    def test_it_runs_the_read_only_test_first_then_the_simulations_and_the_send_last(self):
        text = self.text
        self.assertRegex(text, r"(?i)read-only")
        self.assertIn("form_check.py", text)
        self.assertIn("--simulate", text)
        self.assertRegex(text, r"(?i)simulated success")
        self.assertRegex(text, r"(?i)simulated error")
        self.assertLess(text.index("form_check.py"), text.index("--simulate"))
        self.assertLess(text.index("--simulate"), text.rindex("form_consent.py"))

    def test_it_sends_only_with_the_owners_yes_and_says_claude_code_asks(self):
        self.assertIn("only with the owner's yes, given for this test", self.text)
        self.assertIn("Before the command runs, always print the exact command with every value it will send, ask the user for the "
                      "owner's yes to it in the chat, and run it only on that yes, whatever the permission mode", self.text)
        self.assertIn("No rule of the plugin pre-approves `form_consent.py`, so Claude Code asks as well in its default mode until "
                      "the user answers \"don't ask again\", and does not ask in auto mode, with permission prompts off or under an "
                      "allow rule of the user's own", self.text)
        self.assertNotRegex(self.text, r"(?i)before every (real )?send|always asks")

    def test_it_says_what_to_tell_the_user_when_the_fill_is_refused(self):
        self.assertIn("When the form's own validation refuses the fill, the script prints `not sent: the fill does not satisfy "
                      "<field> (<message>)`; tell the user the field and the message and that nothing was sent.", self.text)

    GUARD_LIMIT = ("So no non-GET request leaves in this run at any time, and after the route is installed no request to the "
                   "form's address leaves; a GET that the page's own script sends somewhere else is not covered, and neither is a GET "
                   "to that address while the page loads or on the phone pass.")
    POPUP_LIMIT = ("A route on the browser context aborts every request to the form's action address first, whatever its method, "
                   "and to every submit control's own `formaction` address. The form's target is set to the same page and "
                   "`window.open` returns null before the press, but a page that saved `window.open` earlier, or that clicks a "
                   "`target=\"_blank\"` link itself, can still open a popup during the press. Such a popup is under the guard's "
                   "context rules (every non-GET request aborted, the blocked hosts stopped) and under the form-address route, "
                   "but not under the address block the guard puts on the page it opens itself, so a GET the popup sends to a path "
                   "on the site's own host is not covered.")

    def test_it_says_when_the_form_address_promise_holds_and_what_a_popup_can_still_do(self):
        self.assertIn(self.POPUP_LIMIT, self.text)
        self.assertIn(self.GUARD_LIMIT, self.text)
        self.assertNotIn("No non-GET request and no request to the form's address leaves the browser", self.text)
        self.assertNotIn("A page route aborts", self.text)
        doc = flat(read("skills/cro/scripts/form_check.py").split('"""')[1])
        self.assertIn("A route on the browser context aborts every request to the form's action address first", doc)
        self.assertIn("after the route is installed no request to the form's action address", doc)
        self.assertIn("is under the guard's context rules and the form-address route, but not under the address block the guard "
                      "puts on the page it opens itself", doc)
        self.assertNotIn("so no popup carries a request past the route", doc)

    def test_it_says_the_send_needs_a_request_that_carries_the_typed_address(self):
        self.assertIn("The one send goes only to a request whose body carries the address given in `--email`. When no request to "
                      "the form's host carries it, such as a form with no email field or one that sends the address in another "
                      "shape, it prints `SKIPPED ... SEND` with exit 3 and sends nothing.", self.text)

    def test_the_consent_script_docstring_does_not_say_always_asks(self):
        doc = flat(read("skills/cro/scripts/form_consent.py").split('"""')[1])
        self.assertIn("The yes in the chat comes first, as `form.md` step 7 says", doc)
        self.assertNotRegex(doc, r"(?i)before every|always asks|nothing asks")

    def test_it_points_at_the_form_audit_and_reads_the_thank_you_step(self):
        self.assertIn("form-and-signup-audit.md", self.text)
        self.assertTrue((ROOT / "skills" / "conversion-page-audit" / "references" / "form-and-signup-audit.md").is_file())
        self.assertIn("what happens next", self.text)
        self.assertIn("thank-you", self.text.lower())
        self.assertIn("reply", self.text.lower())

    def test_it_says_what_the_guard_covers_and_what_it_reports_after_the_fact(self):
        for part in ("formaction", "submits by GET", "redirect that keeps the method", "a GET that the page's own script sends somewhere else is not covered"):
            self.assertIn(part, self.text)
        self.assertNotIn("the press cannot send anything", self.text)

    def test_the_scripts_it_names_exist(self):
        for name in ("form_check.py", "form_consent.py"):
            self.assertTrue((ROOT / "skills" / "cro" / "scripts" / name).is_file(), name)


class DataTests(unittest.TestCase):
    def setUp(self):
        self.raw = read_or_empty("skills", "cro", "references", "data.md")
        self.text = flat(self.raw)

    def test_it_opens_with_the_paths_note(self):
        self.assertRegex(self.text, r"This is the procedure `/cro data` follows\. It writes the plugin's folder as `\$\{CLAUDE_PLUGIN_ROOT\}`")

    def test_it_carries_numbered_steps(self):
        steps = re.findall(r"^\d+\. ", self.raw, re.M)
        self.assertGreaterEqual(len(steps), 4)

    def test_it_names_the_ga4_route_and_its_fallback(self):
        self.assertRegex(self.text, r"(?i)GA4 MCP server")
        self.assertRegex(self.text, r"(?i)last 28 days")
        self.assertRegex(self.text, r"(?i)(ask|asks) the user for a GA4 export")
        for part in ("landing page", "form start", "device", "source and medium"):
            self.assertIn(part, self.text.lower())

    def test_it_runs_clarity_through_the_script_within_its_budget(self):
        self.assertIn("clarity_export.py", self.text)
        self.assertIn("--dimension URL --dimension Device", self.text)
        self.assertIn('--out "<audit data folder>/clarity.json"', self.text)
        self.assertIn("clarity-token", self.text)
        self.assertIn("setup.md", self.text)
        self.assertRegex(self.text, r"(?i)never ask for the token in the chat")
        self.assertRegex(self.text, r"(?i)ten (calls|requests)")
        self.assertNotIn("--endpoint", self.text)

    def test_it_maps_each_clarity_metric_to_an_audit_factor(self):
        text = self.text
        self.assertRegex(text, r"(?i)rage clicks?[^.]*dead clicks?[^.]*factor 9|dead clicks?[^.]*rage clicks?[^.]*factor 9")
        self.assertRegex(text, r"(?i)quick-?backs?[^.]*factor 2")
        self.assertRegex(text, r"(?i)scroll depth[^.]*where the page loses people")
        self.assertRegex(text, r"(?i)form starts[^.]*factor 8")

    def test_it_marks_the_reset_time_unverified_with_a_429_as_the_authority(self):
        self.assertRegex(self.text, r"(?i)reset time is UNVERIFIED")
        self.assertRegex(self.text, r"(?i)429[^.]*(authority|decides)|(authority|decides)[^.]*429")

    def test_it_invents_nothing_and_says_when_a_result_is_cut(self):
        self.assertRegex(self.text, r"(?i)missing, never estimated or invented")
        self.assertIn("truncated", self.text)
        self.assertIn("clarity.json", self.text)

    def test_it_names_no_c_prefixed_file(self):
        self.assertNotIn("[C]", self.raw)

    def test_the_script_it_names_exists(self):
        self.assertTrue((ROOT / "skills" / "cro" / "scripts" / "clarity_export.py").is_file())

    def test_setup_md_has_the_token_section_and_the_two_doctor_rows(self):
        setup = read_or_empty("skills", "cro", "references", "setup.md")
        flat_setup = flat(setup)
        self.assertIn("## The Clarity token", setup)
        self.assertLess(setup.index("## The PageSpeed key"), setup.index("## The Clarity token"))
        self.assertIn("read -rs -p 'Clarity token: '", setup)
        self.assertIn("~/.config/nca-conversion/clarity.token", setup)
        self.assertIn("NCA_CLARITY_TOKEN", setup)
        self.assertIn("--token-file", setup)
        rows = [line.split("|")[1].strip() for line in setup.splitlines() if line.startswith("| `")]
        self.assertEqual(rows, ["`python`", "`venv`", "`playwright`", "`browser`", "`pagespeed-key`", "`clarity-token`", "`lighthouse`", "`companions`", "`hallmark-lint`"])
        self.assertIn("never the token", flat_setup)


class CompareTests(unittest.TestCase):
    def setUp(self):
        self.raw = read_or_empty("skills", "cro", "references", "compare.md")
        self.text = flat(self.raw)

    def test_it_opens_with_the_paths_note(self):
        self.assertRegex(self.text, r"This is the procedure `/cro compare` follows\. It writes the plugin's folder as `\$\{CLAUDE_PLUGIN_ROOT\}`")

    def test_new_baseline_says_the_speed_search_and_facts_lines_still_follow(self):
        self.assertIn("The speed, search and facts lines that follow are changes in the page's parts, not a score comparison, "
                      "and are written up as such.", self.text)

    def test_footer_headings_count_in_the_h2_list_on_every_facts_file(self):
        self.assertIn("A footer heading counts in the H2 list on every facts file, because facts from before 0.3.0 cannot say "
                      "which headings sit in a footer and both sides are read the same way.", self.text)

    def test_the_version_note_warns_that_021_changed_factor_10(self):
        self.assertIn("a sheet without `plugin_version` reads as the oldest anchors, and the line says which sheet it is. "
                      "When both sheets lack it, a caution says 0.2.1 changed factor 10's anchors, so a change in factor 10 may come from the version.", self.text)

    def test_it_carries_numbered_steps(self):
        steps = re.findall(r"^\d+\. ", self.raw, re.M)
        self.assertGreaterEqual(len(steps), 4)

    def test_it_runs_the_script_and_the_script_exists(self):
        self.assertIn("python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/compare.py <before folder> <after folder>", self.text)
        self.assertTrue((ROOT / "skills" / "cro" / "scripts" / "compare.py").is_file())

    def test_it_writes_compare_md_in_the_after_audits_data_folder(self):
        self.assertRegex(self.text, r"(?i)write `compare\.md` in the after audit's data folder")

    def test_it_names_the_client_file_and_checks_it(self):
        self.assertIn("Before and After \u2014 <Page> \u2014 <YYYY-MM-DD> \u2014 client.md", self.text)
        self.assertIn("client_check.py", self.text)

    def test_the_client_version_lists_fixed_and_open_leaks_and_no_score(self):
        self.assertRegex(self.text, r"(?i)lists the fixed leaks and the open leaks and gives no score")

    def test_a_live_test_changes_one_thing_at_a_time(self):
        self.assertRegex(self.text, r"(?i)a live test changes one thing at a time")
        self.assertIn("The result cannot be put down to either change.", self.text)

    def test_it_never_edits_a_sheet_to_make_a_comparison_run(self):
        self.assertRegex(self.text, r"(?i)never edited to make a comparison run")

    def test_it_names_no_c_prefixed_file(self):
        self.assertNotIn("[C]", self.raw)


def section_between(text, start, end):
    # the text from the first line that starts with `start` up to the first later line that starts with `end`; "" when
    # `start` is absent
    lines = text.splitlines()
    begin = next((n for n, line in enumerate(lines) if line.startswith(start)), None)
    if begin is None:
        return ""
    stop = next((n for n in range(begin + 1, len(lines)) if lines[n].startswith(end)), len(lines))
    return "\n".join(lines[begin:stop])


class FounderPlaybookTests(unittest.TestCase):
    REFS = ("skills", "cro", "references")
    COMMIT = "e811e63be42c9b64a208707220b145451ad4b6c8"

    def raw_of(self, name):
        return read_or_empty(*self.REFS, name)

    def headings(self, raw):
        return re.findall(r"^## (.+?)\s*$", raw, re.M)

    def check_sections(self, name, title, headings):
        raw = self.raw_of(name)
        self.assertTrue(raw, name + " is missing")
        self.assertEqual(raw.splitlines()[0], title)
        self.assertEqual(self.headings(raw), headings)
        first = raw.index("\n## ")
        between = raw[len(title):first].strip()
        self.assertTrue(between and "\n\n" not in between, "one paragraph between the title and the first section")

    def no_code(self, raw):
        return re.sub(r"`[^`\n]*`", "", raw)

    def test_positioning_has_its_sections_in_order(self):
        self.check_sections("positioning.md", "# Positioning", [
            "Competitive alternatives", "What is unique", "The value it enables", "Who cares most",
            "The market category", "How each feeds the page"])

    def test_lead_sources_has_its_sections_in_order(self):
        self.check_sections("lead-sources.md", "# Lead sources", [
            "The four ways leads arrive", "Lead magnets", "How the traffic leg reads them"])

    def test_sales_follow_up_has_its_sections_in_order(self):
        self.check_sections("sales-follow-up.md", "# Sales follow-up", [
            "The discovery-call questions", "Response time", "The promised next step", "The confirmation message"])

    def test_a_lead_hears_back_within_minutes_not_days(self):
        s = flat(section(self.raw_of("sales-follow-up.md"), "Response time"))
        self.assertIn("a lead hears back within minutes, not days", s)

    def test_the_confirmation_says_what_happens_next_and_when(self):
        s = flat(section(self.raw_of("sales-follow-up.md"), "The confirmation message"))
        self.assertIn("what happens next and when", s)

    def test_attribution_carries_the_founder_playbook_row(self):
        text = flat(read("ATTRIBUTION.md"))
        self.assertIn("[getagentseal/founder-playbook](https://github.com/getagentseal/founder-playbook)", text)
        self.assertIn(self.COMMIT, text)
        row = next((r for r in read("ATTRIBUTION.md").splitlines() if "getagentseal/founder-playbook](" in r), "")
        self.assertIn("AgentSeal", row)
        self.assertIn("| MIT |", row)
        for path, folder in (("positioning.md", "skills/obviously-awesome"), ("lead-sources.md", "skills/100m-leads"),
                             ("sales-follow-up.md", "skills/spin-selling")):
            self.assertIn("`skills/cro/references/%s`" % path, row)
            self.assertIn("`%s`" % folder, row)
        self.assertRegex(flat(row), r"(?i)response-time and confirmation sections are the plugin's own rules")

    def test_attribution_carries_the_mit_notice(self):
        block = section_between(read("ATTRIBUTION.md"), "**founder-playbook licence.**", "## 2. Statement of changes")
        self.assertIn("```text", block)
        self.assertIn("MIT License", block)
        self.assertIn("Copyright (c) 2026 AgentSeal", block)
        self.assertIn("Permission is hereby granted, free of charge", block)

    def test_attribution_lists_the_fifteen_source_books(self):
        block = section_between(read("ATTRIBUTION.md"), "**founder-playbook's source books**", "## 2. Statement of changes")
        books = re.findall(r"^- (.+?) — (.+?)\s*$", block, re.M)
        self.assertEqual(len(books), 15)
        self.assertTrue(all(title and author for title, author in books))

    def test_the_source_books_block_claims_only_what_this_task_can_know(self):
        block = flat(section_between(read("ATTRIBUTION.md"), "**founder-playbook's source books**", "## 2. Statement of changes"))
        self.assertNotIn("nowhere else", block)
        self.assertRegex(block, r"the three reference files rewritten from founder-playbook .*name none of them")

    def test_attribution_maps_each_new_file_to_its_folder(self):
        rows = [r for r in read("ATTRIBUTION.md").splitlines() if r.startswith("| `skills/cro/references/")]
        for path, folder in (("positioning.md", "skills/obviously-awesome"), ("lead-sources.md", "skills/100m-leads"),
                             ("sales-follow-up.md", "skills/spin-selling")):
            hit = [r for r in rows if r.startswith("| `skills/cro/references/%s`" % path)]
            self.assertGreaterEqual(len(hit), 1, path)
            self.assertIn("`getagentseal/founder-playbook` at `e811e63`", hit[0])
            self.assertIn("`%s`" % folder, hit[0])
        positioning_row = next(r for r in rows if r.startswith("| `skills/cro/references/positioning.md`"))
        for term in ("competitive alternatives", "market category", "unique attribute", "so what?", "Who cares most"):
            self.assertIn('"%s"' % term, positioning_row)
        self.assertNotIn("Nothing else is kept", positioning_row)
        follow = next(r for r in rows if "sales-follow-up.md" in r)
        self.assertRegex(flat(follow), r"(?i)response-time and confirmation sections draw on no source")

    def test_research_sends_positioning_gaps_to_positioning(self):
        raw = read("skills", "cro", "references", "research.md")
        step = step_of(raw, 7)
        self.assertIn("positioning gap", step)
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/skills/cro/references/positioning.md", step)
        self.assertEqual(len(re.findall(r"^\d+\. ", raw, re.M)), 11)

    def test_the_three_references_hold_no_digit(self):
        for name in ("positioning.md", "lead-sources.md", "sales-follow-up.md"):
            raw = self.raw_of(name)
            self.assertTrue(raw, name + " is missing")
            self.assertNotRegex(self.no_code(raw), r"\d", name)

    def test_the_three_references_name_no_source(self):
        for name in ("positioning.md", "lead-sources.md", "sales-follow-up.md"):
            raw = self.raw_of(name)
            self.assertTrue(raw, name + " is missing")
            for word in ("founder-playbook", "obviously-awesome", "100m-leads", "spin-selling"):
                self.assertNotIn(word, raw, name)
            for domain in re.findall(r"\b[\w-]+(?:\.[\w-]+)*\.(?:[a-z]{2,})\b", self.no_code(raw)):
                self.assertTrue(domain.endswith(".example"), "%s: %s" % (name, domain))


class DiagnoseTests(unittest.TestCase):
    STEP_FIRST = re.compile(r"^1\. ", re.M)
    LEGS = (
        (2, "Traffic and search: are the right people arriving?"),
        (3, "The page: do they see it is for them?"),
        (4, "Form and behaviour: do they act?"),
        (5, "Follow-up: what happens after they act?"),
        (6, "The offer: would they buy?"),
        (7, "Demand: do people want it?"),
    )
    REF = "${CLAUDE_PLUGIN_ROOT}/skills/cro/references/"
    NEVER_AUDIT = "Never run claude-seo's `seo-audit`: it audits a whole site and hands its work to subagents."
    NO_SUBAGENTS = ("Start no subagents, and use no browser tool from an MCP server: every leg runs in this conversation, "
                    "one after another, and a page is rendered only by the plugin's own scripts, which block the site's analytics.")
    ORDER = ("The walk keeps the buyer-path order, from the visit to the sale, rather than starting with whether people want the "
             "offer, because a free diagnosis sees the traffic and the page from outside; only the owner's data answers whether "
             "people want it.")

    def setUp(self):
        self.raw = read_or_empty("skills", "cro", "references", "diagnose.md")
        self.text = flat(self.raw)
        first = self.STEP_FIRST.search(self.raw)
        self.before = flat(self.raw[:first.start()]) if first else self.text

    def step(self, n):
        return flat(step_of(self.raw, n))

    def test_it_opens_with_the_paths_note(self):
        self.assertTrue(self.raw, "diagnose.md is missing")
        self.assertEqual(self.raw.splitlines()[0], "# The /cro diagnose procedure")
        self.assertIn("This is the procedure `/cro diagnose` follows. It writes the plugin's folder as `${CLAUDE_PLUGIN_ROOT}` "
                      "and its data folder as `${CLAUDE_PLUGIN_DATA}`. The shell sets neither one, so put the full paths the `cro` "
                      "skill gave you in their place in every command you run and every file you read. Any argument that can hold "
                      "a space, such as a folder name, goes in quotation marks. The output is a buyer-path diagnosis of one site, "
                      "internal first and then a client version.", self.before)

    def test_step_three_says_where_the_audits_internal_report_stays(self):
        self.assertIn("The audit's internal report stays in the audit data folder as the page leg's evidence; the diagnosis "
                      "report cites it and does not copy it.", flat(self.step(3)))

    def test_it_carries_eleven_numbered_steps(self):
        numbers = [int(n) for n in re.findall(r"^(\d+)\. ", self.raw, re.M)]
        self.assertEqual(numbers, list(range(1, 12)))
        self.assertEqual(re.findall(r"^## ", self.raw, re.M), [], "no heading below the title")

    def test_the_legs_follow_the_buyer_path(self):
        for n, label in self.LEGS:
            self.assertTrue(self.step(n).startswith("%d. **%s**" % (n, label)), "step %d" % n)

    def test_the_walk_keeps_the_buyer_path_order_and_says_why(self):
        self.assertIn(self.ORDER, self.before)
        self.assertEqual(self.text.count(self.ORDER), 1)

    def test_each_leg_names_its_command_or_reference(self):
        names = {
            1: ["python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/doctor.py --data-dir ${CLAUDE_PLUGIN_DATA}", "companions",
                "clarity-token", "<project folder>/_audit-data/<page-slug>-<YYYY-MM-DD>/", "Search Console", "**Written by:**"],
            2: [self.REF + "lead-sources.md", "seo-page", "seo-google", "search_check.py"],
            3: ["/cro audit", self.REF + "audit.md", self.REF + "positioning.md", "factor 1", "factor 2", "6 or under"],
            4: ["/cro form", self.REF + "form.md", "/cro data", self.REF + "data.md", "steps 1 to 5"],
            5: [self.REF + "sales-follow-up.md", "form_consent.py", "owner's yes", "steps 6 and 7",
                "a lead hears back within minutes, not days"],
            6: ["${CLAUDE_PLUGIN_ROOT}/skills/offer-architect/references/offer-audit-checklist.md", "no composite score"],
            7: ["/cro research", self.REF + "research.md"],
            11: ["/cro compare", self.REF + "compare.md", "every other leg is read again from its own new evidence"],
        }
        for n, wanted in names.items():
            step = self.step(n)
            self.assertTrue(step, "step %d is missing" % n)
            for name in wanted:
                self.assertIn(name, step, "step %d" % n)

    def test_traffic_leg_names_seo_page_and_seo_google(self):
        step = self.step(2)
        self.assertRegex(step, r"claude-seo's `seo-page` on the page's raw HTML, never with claude-seo's render option")
        self.assertIn("claude-seo's renderer does not block the site's analytics", step)
        self.assertRegex(step, r"`seo-google` for the page's Search Console data when the user has Search Console access")
        self.assertRegex(step, r"Without claude-seo, run `search_check\.py`")
        self.assertRegex(step, r"On a Direct page the search part is skipped")

    def test_diagnose_never_calls_the_site_audit(self):
        self.assertEqual(self.text.count("seo-audit"), 1)
        self.assertEqual(self.text.count(self.NEVER_AUDIT), 1)
        self.assertIn(self.NEVER_AUDIT, self.step(2))

    def test_demand_is_asked_last_and_goes_back_to_research(self):
        step = self.step(7)
        self.assertIn("only when every other leg passes and leads still do not buy", step)
        self.assertRegex(step, r"which goes back to `/cro research`")
        self.assertRegex(step, r"A free diagnosis does not reach it")
        self.assertEqual([m.start() for m in re.finditer(r"\*\*Demand: ", self.raw)], [self.raw.index("**Demand: ")])
        self.assertGreater(self.raw.index("**Demand: "), self.raw.index("**The offer: "))

    def test_it_says_which_legs_were_skipped_and_why(self):
        step = self.step(8)
        self.assertTrue(step.startswith("8. Say which legs were skipped and why"))
        self.assertIn("## Skipped legs", step)
        self.assertIn("- <leg>: skipped, because <reason>.", step)
        self.assertIn("A leg is never left out silently.", step)
        for n, reason in ((2, "Direct page"), (2, "Without claude-seo"), (2, "has Search Console access"), (4, "without a form"),
                          (4, "skip it with its reason"), (5, "Without the owner"), (7, "does not reach it")):
            self.assertIn(reason.lower(), self.step(n).lower(), "step %d: %s" % (n, reason))
        for n in range(2, 8):
            self.assertRegex(self.step(n), r"(?i)skip", "step %d names what it skips" % n)

    def test_a_test_lead_needs_the_owners_yes(self):
        step = self.step(5)
        self.assertIn("form_consent.py", step)
        self.assertIn("owner's yes", step)
        self.assertIn("the command is shown and the yes asked in the chat, as `form.md` step 7 says", step)
        self.assertNotRegex(step, r"(?i)asks about before|before every|always asks")
        mark = self.raw.index("\n5. ")
        self.assertNotIn("form_consent.py", self.raw[:mark])
        self.assertNotIn("form_consent.py", flat(step_of(self.raw, 4)))
        self.assertIn("stop before its step 6", self.step(4))

    def test_the_internal_report_has_a_section_per_leg(self):
        step = self.step(9)
        self.assertIn("<project folder>/Buyer-Path Diagnosis — <Site> — <YYYY-MM-DD>.md", step)
        names = ["## Traffic and search", "## The page", "## Form and behaviour", "## Follow-up", "## The offer", "## Demand",
                 "## Skipped legs", "## Leaks in fix order"]
        at = [step.index(name) for name in names]
        self.assertEqual(at, sorted(at))
        self.assertIn("`score.py`'s `line` word for word", step)
        self.assertRegex(step, r"an earlier leg first where two cost about the same")

    def test_the_client_version_follows_client_version_md(self):
        step = self.step(10)
        self.assertIn("<project folder>/Buyer-Path Diagnosis — <Site> — <YYYY-MM-DD> — client.md", step)
        self.assertIn(self.REF + "client-version.md", step)
        self.assertIn("the three costliest leaks across the legs, in the order to fix them", step)
        self.assertIn("no score", step)
        self.assertIn("Public pages only. No logins, and no form was sent.", step)
        self.assertRegex(step, r"says where it was seen")

    def test_it_runs_client_check(self):
        step = self.step(10)
        self.assertIn("python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/client_check.py <client file>", step)
        self.assertIn("fix every FAIL", step)

    def test_it_starts_no_subagents(self):
        self.assertIn(self.NO_SUBAGENTS, self.before)
        self.assertEqual(self.text.count(self.NO_SUBAGENTS), 1)

    def test_every_path_it_names_exists(self):
        paths = re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\s`'\"<>)]+)", self.raw)
        paths = [p.rstrip(".,;:") for p in paths]
        self.assertGreaterEqual(len(paths), 8)
        for path in paths:
            self.assertTrue((ROOT / path).is_file(), path)
        for script in ("doctor.py", "search_check.py", "form_consent.py", "client_check.py", "score.py"):
            self.assertIn(script, self.raw)
            self.assertTrue((ROOT / "skills" / "cro" / "scripts" / script).is_file(), script)

    def test_it_names_no_source(self):
        self.assertTrue(self.raw, "diagnose.md is missing")
        for word in ("founder-playbook", "skills/diagnose", "obviously-awesome", "100m-leads", "spin-selling", "One-Skill",
                     "Misdiagnosis"):
            self.assertNotIn(word, self.raw)
        bare = re.sub(r"`[^`\n]*`", "", self.raw)
        for domain in re.findall(r"\b[\w-]+(?:\.[\w-]+)*\.(?:[a-z]{2,})\b", bare):
            self.assertTrue(domain.endswith(".example"), domain)

    def test_attribution_maps_diagnose_to_its_source(self):
        text = read("ATTRIBUTION.md")
        sentence = ("Its diagnostic questions, read in `skills/diagnose`, inform the legs of `skills/cro/references/diagnose.md`, "
                    "which walks them in the buyer-path order with demand last rather than in the source's order.")
        row = next((r for r in text.splitlines() if "getagentseal/founder-playbook](" in r), "")
        self.assertIn(sentence + " The licence notice and the source books follow this section's notes.", flat(row))
        rows = [r for r in text.splitlines() if r.startswith("| `skills/cro/references/diagnose.md`")]
        self.assertEqual(len(rows), 1)
        self.assertIn("`getagentseal/founder-playbook` at `e811e63`, `skills/diagnose`", rows[0])
        self.assertIn("its five questions only", rows[0])
        self.assertRegex(flat(rows[0]), r"walked in the buyer-path order with demand last rather than in the source's order")
        self.assertRegex(flat(rows[0]), r"no term kept word for word")
        self.assertRegex(flat(rows[0]), r"The legs' commands, references and outputs are the plugin's own\.")


class RouterTests(unittest.TestCase):
    NEW_COMMAND = ("python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/setup.py --permissions --plugin-root ${CLAUDE_PLUGIN_ROOT} "
                   "--data-dir ${CLAUDE_PLUGIN_DATA}")
    SPACE_PARAGRAPH = ("A rule matches a command only when the command names the plugin's folder exactly as the rule writes it. "
                       "If that folder's path holds a space, the commands have to quote it, so the rules do not match and "
                       "Claude Code keeps asking before each script.")
    FORM_PARAGRAPH = ("`/nca-conversion:cro form` reads a form without sending it. Its simulated success and simulated error press the submit "
                      "button, but after the plugin's route is installed it replies in place of the form's own address, so nothing reaches the owner. A real "
                      "test submission runs only through `form_consent.py`, and only with the owner's yes for that test. "
                      "Whatever the permission mode, the model shows you the exact command with every value it will send and "
                      "waits for your yes in the chat before it runs. Claude Code's own prompt comes on top in its default permission mode "
                      "until you choose \"don't ask again\", because no `allowed-tools` rule pre-approves the script and "
                      "`/nca-conversion:cro setup --permissions` prints no rule for it; it does not come in auto mode, with permission "
                      "prompts off or under an allow rule of your own (see https://code.claude.com/docs/en/permissions and "
                      "https://code.claude.com/docs/en/permission-modes).")
    GUARDED_NEW = ("Rendered checks run only through the plugin's own scripts, which share one guard: `render_check.py`, "
                   "`launch_render.py`, `form_check.py` and `form_consent.py`.")
    GUARDED_OLD = "Rendered checks run only through `render_check.py`."
    SENTENCES_NEW = ("Only GET, HEAD and OPTIONS leave the browser, apart from the one consented test submission described below. "
                     "The browser presents an ordinary Chrome user agent, and every blocked request is written to a log. "
                     "Outside the form test, no form is sent and nothing is clicked.")
    SENTENCES_OLD = ("Only GET, HEAD and OPTIONS leave the browser, the browser presents an ordinary Chrome user agent, and every "
                     "blocked request is written to a log. No form is sent and nothing is clicked.")
    RESEARCH_NEW = ("where the site has it, never invented: read GA4 and Microsoft Clarity as "
                    "`${CLAUDE_PLUGIN_ROOT}/skills/cro/references/data.md` says, or use exports the user supplies.")

    def allowed(self):
        fm, body = frontmatter_and_body(CRO)
        return re.search(r"^allowed-tools:\s*(.+)$", fm, re.M).group(1)

    def readme_section(self):
        text = README.read_text(encoding="utf-8")
        start = text.index("\n## Version 2: the front door\n")
        return text[start:text.index("\n## ", start + 1)]

    def test_consent_script_is_never_pre_approved(self):
        allowed = self.allowed()
        self.assertNotIn("form_consent.py", allowed)
        entries = re.findall(r"Bash\([^)]*\)", allowed)
        self.assertEqual(len(entries), 18)
        with tempfile.TemporaryDirectory() as tmp:
            done = subprocess.run([sys.executable, str(ROOT / "skills/cro/scripts/setup.py"), "--permissions",
                                   "--plugin-root", str(ROOT), "--data-dir", tmp], capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr)
        rules = json.loads(done.stdout[:done.stdout.rindex("}") + 1])["permissions"]["allow"]
        self.assertNotIn("form_consent", done.stdout)
        self.assertEqual(len(rules), len(entries))

    def test_no_skill_pre_approves_the_consent_script(self):
        # Every SKILL.md in the repo, by the script's name and by any rule, wildcard or bare Bash, that would also cover it.
        run = "${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/form_consent.py https://example.com --owner Someone --date 2026-01-01 --email a@example.com"
        commands = ["python3 " + run, "python " + run, "${CLAUDE_PLUGIN_DATA}/venv/bin/python " + run]
        found = 0
        for skill in sorted((ROOT / "skills").glob("*/SKILL.md")):
            fm, _body = frontmatter_and_body(skill)
            line = re.search(r"^allowed-tools:\s*(.+)$", fm, re.M)
            if not line:
                continue
            found += 1
            self.assertNotIn("form_consent", line.group(1), skill.parent.name)
            self.assertFalse(re.search(r"(^|\s)Bash(\s|$)", line.group(1)), "a bare Bash rule allows every command: " + skill.parent.name)
            for entry in re.findall(r"Bash\(([^)]*)\)", line.group(1)):
                pattern = entry.replace(":*", " *")
                for command in commands:
                    self.assertFalse(fnmatch.fnmatchcase(command, pattern), "%s: Bash(%s) covers the consent script" % (skill.parent.name, entry))
        self.assertGreaterEqual(found, 2)

    def test_router_has_no_not_built_yet_bullet(self):
        fm, body = frontmatter_and_body(CRO)
        self.assertNotIn('A "not built yet" row: say so and name its slice.', body)
        route = body[body.index("## Route"):body.index("## Rules")]
        self.assertEqual(len([line for line in route.splitlines() if line.startswith("- ")]), 3)

    def test_readme_lists_all_seventeen_commands(self):
        section = self.readme_section()
        self.assertEqual(len(CroRulingsTest.ROWS), 17)
        for cell, goes, status in CroRulingsTest.ROWS:
            self.assertTrue(any(line.startswith("| " + cell + " |") for line in section.splitlines()), cell)

    def test_readme_form_section_says_the_consent_script_always_asks(self):
        text = README.read_text(encoding="utf-8")
        a = text.index("### Rendered checks and your client's analytics")
        b = text.index("### The form test and the consent script")
        c = text.index("### Script permissions last one turn")
        self.assertLess(a, b); self.assertLess(b, c)
        self.assertIn(self.FORM_PARAGRAPH, flat(text[b:c]))
        self.assertEqual(len([line for line in text[b:c].splitlines() if line.strip() and not line.startswith("#")]), 1)

    def test_readme_names_every_guarded_renderer(self):
        text = flat(README.read_text(encoding="utf-8"))
        for new in (self.GUARDED_NEW, self.SENTENCES_NEW):
            self.assertIn(new, text)
        for old in (self.GUARDED_OLD, self.SENTENCES_OLD):
            self.assertNotIn(old, text)

    def test_readme_drops_the_next_release_sentence(self):
        self.assertNotIn("next planned release", README.read_text(encoding="utf-8"))

    def test_research_reads_behaviour_data_through_cro_data(self):
        text = read("skills", "cro", "references", "research.md")
        self.assertIn(self.RESEARCH_NEW, text)
        self.assertNotIn("is not built yet", text)
        self.assertEqual(len(re.findall(r"^\d+\. ", text, re.M)), 11)

    def test_setup_reference_says_a_spaced_path_keeps_the_prompts(self):
        text = read("skills", "cro", "references", "setup.md")
        self.assertEqual(text.count(self.SPACE_PARAGRAPH), 1)
        self.assertLess(text.index("Merge the printed rules"), text.index(self.SPACE_PARAGRAPH))
        self.assertLess(text.index(self.SPACE_PARAGRAPH), text.index("## The PageSpeed key"))
        self.assertIn(self.NEW_COMMAND, text)

    def test_every_rule_matches_how_the_references_run_its_script(self):
        # a rule matches literal text (Task 12 Step 0): the interpreter a reference writes must be the rule's
        rules = {}
        for entry in re.findall(r"Bash\(([^)]*) \*\)", self.allowed()):
            interpreter, script = entry.split(" ", 1)
            rules[script] = interpreter
        files = [*sorted((ROOT / "skills").glob("*/references/*.md"))]
        cro_body = frontmatter_and_body(CRO)[1]
        run = re.compile(r"(\S+) (\$\{CLAUDE_PLUGIN_ROOT\}/skills/[a-z-]+/scripts/([A-Za-z0-9_]+)\.py)")
        seen = set()
        texts = [(path.name, path.read_text(encoding="utf-8")) for path in files] + [("SKILL.md", cro_body)]
        for name, text in texts:
            for interpreter, script, stem in run.findall(text):
                if stem == "form_consent":
                    continue
                interpreter = interpreter.strip("`'\"(")
                self.assertIn(script, rules, f"{name}: {script}")
                self.assertEqual(interpreter, rules[script], f"{name}: {script}")
                seen.add(script)
        self.assertEqual(seen, set(rules))

    def test_no_cro_file_says_not_built_yet(self):
        paths = [p for p in (ROOT / "skills" / "cro").rglob("*") if p.is_file() and "__pycache__" not in p.parts]
        paths.append(README)
        for path in paths:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for phrase in ("not built yet", "v1 engine until slice 3", "next planned release"):
                self.assertNotIn(phrase, text, f"{path.relative_to(ROOT)}: {phrase}")


REFS = ROOT / "skills/cro/references"


class RoundFixTests(unittest.TestCase):
    def test_check_redirect_status_is_the_final_answer(self):
        text = (REFS / "check.md").read_text(encoding="utf-8")
        step = [l for l in text.splitlines() if l.startswith("4.")][0]
        self.assertIn("final answer", step)
        self.assertIn('{"from": "http://example.com/", "to": "https://example.com/", "status": 200}', step)

    def test_design_step_8_states_a_missing_render_tier(self):
        step = [l for l in (REFS / "design.md").read_text(encoding="utf-8").splitlines() if l.startswith("8.")][0]
        self.assertIn("render tier off", step)
        self.assertIn("without `--render`", step)
        self.assertIn("design notes", step)

    def test_form_tests_write_to_separate_folders(self):
        form = (REFS / "form.md").read_text(encoding="utf-8")
        for folder in ("read-only", "simulated-success", "simulated-error", "consent"):
            self.assertEqual(form.count('--out "<folder>/%s"' % folder), 1, folder)
        self.assertIn("simulated-success/form.json", [l for l in form.splitlines() if l.startswith("5.")][0])
        seen = {}
        for path in sorted(REFS.glob("*.md")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if "form_check.py" in line or "--simulate" in line:
                    outs = re.findall(r'--out "[^"]*"', line)
                    self.assertTrue(outs or "--simulate" not in line, "%s: a form_check run without its own --out" % path.name)
                    for out in outs:
                        self.assertNotIn(out, seen, "%s and %s run form_check on the same %s" % (seen.get(out), path.name, out))
                        seen[out] = path.name


class ScoreRulePinsTest(unittest.TestCase):
    def anchors(self):
        return flat((ROOT / "skills/cro/references/score-anchors.md").read_text(encoding="utf-8"))

    def test_factor_four_ties_the_button_to_the_headline_promise(self):
        t = self.anchors().split("## 4. What do I do next?")[1].split("## 5.")[0]
        self.assertIn("or it promises something other than the headline does", t)
        self.assertIn("its label names the outcome the headline promised", t)

    def test_register_rule_never_costs_a_swiss_b2b_page_for_no_urgency(self):
        self.assertIn("Register rule: a conservative Swiss B2B page never loses points for having no urgency or scarcity", self.anchors())

    def test_three_states_are_missing_not_applicable_and_not_checked(self):
        t = self.anchors()
        self.assertIn("Three states.", t)
        self.assertIn("A thing the page should have and lacks (a form, a button, proof) is a finding and scores low.", t)
        self.assertIn("A thing the page role does not need is handled by the role line under that factor.", t)
        self.assertIn("A thing that could not be observed is `not_checked`: it is left out of the total and lowers coverage", t)

    def test_wireframe_says_which_layout_route_was_used(self):
        t = flat((ROOT / "skills/cro/references/wireframe.md").read_text(encoding="utf-8"))
        self.assertIn("When UI/UX Pro Max is on, run its layout pass", t)
        self.assertIn("When it is off, use the table alone", t)
        self.assertIn("Say in the output which of the two was used.", t)


class AttributionTextTests(unittest.TestCase):
    def test_every_skill_file_and_reference_has_a_derivation_row(self):
        section = read("ATTRIBUTION.md").split("## 3. Derivation map", 1)[1]
        rows = [r for r in section.splitlines() if r.startswith("| `")]
        tracked = subprocess.run(["git", "ls-files", "skills/*/SKILL.md", "skills/*/references/*.md"], cwd=ROOT,
                                 capture_output=True, text=True, check=True).stdout.split()
        self.assertGreaterEqual(len(tracked), 60)
        for path in tracked:
            hit = [r for r in rows if r.startswith("| `%s`" % path)]
            self.assertGreaterEqual(len(hit), 1, path)


class EvidenceRulesTextTests(unittest.TestCase):
    def test_evidence_rules_use_no_browser_tool_and_click_no_banner(self):
        text = flat(read("skills/conversion-page-audit/references/evidence-rules.md"))
        for gone in ("browser automation tool", "click the accept control", "real browser"):
            self.assertNotIn(gone, text)
        self.assertIn("The plugin's guarded capture cannot accept a banner and nothing in it is clicked, so a tag that a consent "
                      "banner holds back goes to Could not check with that reason, not to not installed.", text)
        self.assertIn("Rendered evidence comes only from the plugin's scripts, with analytics blocked, and no browser tool is run "
                      "on a page that is not the user's own.", text)
        self.assertNotIn("Accept the consent banner before auditing tags", text)
        self.assertIn("### A tag behind a consent banner is not checked, not missing", text)


if __name__ == "__main__":
    unittest.main()
