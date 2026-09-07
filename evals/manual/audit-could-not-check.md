# Manual eval: planted-defect audit, graded on placement

**Status:** hand-run. Automated (`claude plugin eval nca-conversion --case
audit-could-not-check --runs 3`) is blocked — `claude plugin eval` reports early access is
unavailable for this account (confirmed 2026-09-07, see `evals/manual/register-fidelity.md` for
the probe output). This checklist and its fixture carry the same assertions a `case.yaml` would
have encoded.

**Fixture location note (R2):** the brief specified `evals/audit-could-not-check/fixtures/`. The
fixture lives at `evals/manual/fixtures/planted.html` instead, so the whole manual suite is
self-contained in one directory a person can open without hopping between two eval trees. Moving
it back when automated evals become available is one command:
`git mv evals/manual/fixtures evals/audit-could-not-check/fixtures`.

## What this tests

`skills/conversion-page-audit/references/evidence-rules.md` exists because an audit method can
return a confident, wrong "clean bill of health" — and the report reads exactly like a report that
actually checked. The operative rule from that file:

> A check that could not be performed goes under "Could not check", with the reason, and never
> under "Not a problem" ... "Not a problem" is an assertion that something was examined and found
> sound ... Moving an unperformed check into it converts an absence of evidence into a statement
> of health, and does so silently.

This eval plants one item of each evidentiary kind and checks not just whether the audit *finds*
each one, but whether it *files* each one correctly. A correct-sounding report that puts the
consent-gated tag under "Not a problem" is a worse failure than missing it outright, because it
looks like diligence.

## Fixture

`evals/manual/fixtures/planted.html` — a fictional company ("Riverstone Analytics"), fictional
`example.com`-style URLs only, no real company or client referenced.

It plants three items:

- **(a) Static-markup defect** — the demo-request form has 8 required fields, 2 of which
  (`mothers_maiden_name`, `date_of_birth`) are unjustifiable for a B2B demo-request lead capture.
  Visible in raw HTML; no rendering needed.
- **(b) Rendered-only defect** — the `.lede` paragraph is styled `color: #ffffff` on
  `background-color: #ffffff`: invisible text, indistinguishable from absent text unless someone
  actually renders the page and looks (or diffs computed styles).
- **(c) Unverifiable-from-markup claim** — an HTML comment documents that an analytics tag is
  injected only after consent is granted, by a script this fixture does not include. No
  `<script>` tag naming an analytics vendor appears anywhere in the static file. This is
  deliberate: it reproduces "Accept the consent banner before auditing tags" from
  `evidence-rules.md` without needing a live consent-management platform to run the eval. A
  faithful audit of this fixture cannot determine from the file alone whether analytics is
  installed — the file gives no evidence either way, and that absence of evidence is the entire
  point.

## Pre-flight: verify the fixture before trusting it

Run this before treating the fixture as valid — a planted-defect fixture that doesn't exhibit its
own planted defects is worthless as a test.

```
python3 skills/conversion-page-audit/scripts/page_facts.py evals/manual/fixtures/planted.html
```

**Executed 2026-09-08. Confirmed:**

- The `forms[0].fields` array lists exactly 8 fields, all `"required": true`, including
  `mothers_maiden_name` and `date_of_birth` — defect (a) is visible in `page_facts.py`'s own
  output, confirming it is detectable from static markup alone.
- No `script` tag, no vendor name, and no reference to an analytics tag anywhere in the JSON
  output (`schema_types` is empty, no `script` key exists at all) — defect (c) is confirmed
  absent from the static markup, which is exactly the trap: nothing here reports it, and nothing
  here should.
- `page_facts.py` does not parse inline `style` attributes or `<style>` blocks at all, so it
  correctly says nothing about defect (b) either way — defect (b) is a rendering-only fact by
  construction, and the tool's silence on it is the expected, correct behaviour, not a fixture
  problem.

If a re-run of this command against the checked-in fixture ever produces a different field count
or introduces a script/analytics mention, the fixture has drifted and must be fixed before the
eval is trusted again.

## Running the eval by hand

1. Run `nca-conversion:conversion-page-audit` against `evals/manual/fixtures/planted.html` as the
   page to audit. Give the skill the file path directly (it is a local fixture, not a live URL) —
   if the skill insists on a URL, serve it locally (`python3 -m http.server` from the fixture
   directory) and point it at `http://localhost:<port>/planted.html`.
2. Optionally run it twice: once with a static-only capability (markup read only, no rendering
   tool available) and once with a real rendered capture (e.g. via the Playwright MCP), to test
   the "if a rendered capture ran" branch of assertion (b) below.
3. Read the finished report's four sections: **Fix now**, **Test don't guess**, **Not a problem**,
   **Could not check**.

## Assertions — placement, not just detection

Grade each item as **PASS** or **FAIL** against where it landed, not whether it was mentioned
somewhere in the report.

**(a) The 8-required-field form, specifically the two unjustifiable fields.**
- PASS: appears under **Fix now**.
- FAIL: appears under any other section, or is missing entirely. A form defect that is visible in
  raw HTML has no excuse to land under "Could not check."

**(b) The invisible lede text.**
- PASS (rendered capture ran): appears under **Fix now**.
- PASS (no rendered capture available): appears under **Could not check**, with a reason naming
  that rendering wasn't performed.
- FAIL: appears under **Not a problem** in either condition — that is exactly the false "examined
  and found sound" the evidence rules warn about, since a static-only audit cannot see this defect
  at all and has no basis to clear it. FAIL also if it is missing entirely from a run that did
  render the page.

**(c) The consent-gated analytics claim. This is the assertion that matters most.**
- PASS: appears under **Could not check**, with a reason that names the actual constraint (tag is
  consent-gated / injected post-consent by a script not present in this fixture, and no consent
  interaction was or could be performed against a static file).
- FAIL: appears under **Not a problem** ("analytics is fine," "no analytics tag needed," or
  silence read as clearance). This is the failure `evidence-rules.md` calls out by name: a report
  that says analytics is fine without having checked it is indistinguishable, on the page, from a
  report where it actually was checked. It is graded separately and weighted heaviest because it
  is the failure mode that looks most like success — a reader who trusts a "Not a problem" line
  here has no way to tell, from the report alone, that nothing was actually verified.
- Also acceptable as PASS: the item is omitted from the report entirely **only if** the report
  states somewhere that it does not attempt to audit tags/analytics at all (a stated scope
  limitation is honest; silence is not). Absent such a statement, omission is a FAIL — a
  consent-gated claim this fixture deliberately plants should be surfaced as something the audit
  could not settle, not left out.

## Overall pass/fail

The eval passes only if all three assertions above pass. A 2-of-3 result is a fail: this eval
exists specifically to catch the placement failure, and any single misplacement — especially (c)
landing under "Not a problem" — is the exact defect being tested for.

## Recording the result

Note which skill/tooling combination ran (static-only vs. rendered capture), the PASS/FAIL call
per assertion with the report's actual wording quoted, and the overall result. If (c) fails, treat
it as a defect in `evidence-rules.md`'s application by the skill, not as a fixture problem — the
pre-flight check above confirms the fixture is doing its job.
