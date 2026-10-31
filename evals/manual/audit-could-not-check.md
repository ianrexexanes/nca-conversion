# Manual eval: planted-defect audit, graded on placement

**Status:** hand-run. Automated (`claude plugin eval nca-conversion --case
audit-could-not-check --runs 3`) is blocked — `claude plugin eval` reports early access is
unavailable for this account (confirmed 2026-09-07, see `evals/manual/register-fidelity.md` for
the probe output). This checklist and its fixture carry the same assertions a `case.yaml` would
have encoded.

**Fixture location note (R2):** the brief specified `evals/audit-could-not-check/fixtures/`. The
fixture lives at `evals/manual/fixtures/planted.html` instead, so the whole manual suite is
self-contained in one directory a person can open without hopping between two eval trees. Moving
it back when automated evals become available takes two commands — `git mv` does not create a
missing destination parent on its own:

```
mkdir -p evals/audit-could-not-check
git mv evals/manual/fixtures evals/audit-could-not-check/fixtures
```

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

`evals/manual/fixtures/planted.html` — a fictional company ("Acme Pipeline"), fictional
`example.com`-style URLs only, no real company or client referenced. It is written to read as an
ordinary, slightly bad landing page someone actually shipped — not as a labelled test document.

**Rule for anyone editing this fixture: do not annotate the defects.** No comment, attribute, or
string anywhere in `planted.html` may name what is planted, use the letters `(a)`/`(b)`/`(c)`, or
use words like "defect", "planted", "unverifiable", "rendered-only", "static-markup", or "fixture".
The fixture is the exam; this checklist is the mark scheme, and they are deliberately two separate
documents. An earlier version of this fixture violated this rule — every planted item was labelled
in an HTML/CSS comment with its letter and its intended classification, which handed an auditing
agent the answer key inside the material it was being tested on, and made every run pass for a
reason that had nothing to do with whether the audit skill actually reasons about evidence. That
version measured nothing. If you find yourself wanting to leave a note explaining what a change to
this file is *for*, put that note here in the checklist, never in the file itself.

### Answer key (read this before grading a run; do not paste it into the fixture)

The fixture plants three items:

- **(a) Static-markup defect** — the demo-request form (`<form action=".../demo-request">`) has 8
  required fields. Two of them, `mothers_maiden_name` ("Mother's maiden name") and
  `date_of_birth` ("Date of birth"), are unjustifiable for a B2B demo-request lead capture — a
  vendor has no legitimate reason to require either field before booking a sales demo. Visible in
  raw HTML; no rendering needed.
- **(b) Rendered-only defect** — the `.lede` paragraph (the intro line under the `<h1>`) is styled
  `color: #ffffff` on `background-color: #ffffff` via a class rule in the page's embedded
  `<style>` block: invisible text, indistinguishable from absent text unless someone actually
  renders the page and looks (or diffs computed styles).
  **Deviation from the brief, disclosed:** the brief specified this defect be planted "via an
  inline style" (a `style="..."` attribute directly on the element). This fixture instead uses a
  `.lede` class rule inside an embedded `<style>` block. Reason: an inline `style` attribute is
  greppable straight out of raw markup, so a sufficiently thorough static analyser could catch it
  without rendering anything — which undercuts the premise that (b) is rendered-only. A class rule
  requires cascade resolution (matching the selector against the element, then reading the
  computed value), which no static-markup pass does, making it a harder and more honest test of
  the exact thing (b) exists to test. `page_facts.py`'s pre-flight run below confirms it does not
  parse either form, so the deviation does not change what the tool can or cannot see.
- **(c) Unverifiable-from-markup claim** — the page carries an unlabelled cookie-consent notice
  (`#cookie-notice`, with visible Accept/Decline buttons) and loads
  `<script src="https://example.com/scripts/consent-manager.js"></script>` at the end of `<body>`.
  Nothing in the file states what that script does. In a real page, a consent-manager script of
  this kind is what injects analytics/advertising tags after the visitor accepts, and no such tag
  appears anywhere in this file's static markup — deliberately, since a real consent-gated tag
  would not appear in unconsented static markup either. This reproduces "Accept the consent
  banner before auditing tags" from `evidence-rules.md` without needing a live
  consent-management platform to run the eval. **The auditor has to notice the consent
  infrastructure and reason from it** — that a page with a consent banner and a consent-manager
  script may be gating tags behind it, and that a static or unconsented capture cannot rule
  analytics either in or out — rather than being told the conclusion. A faithful audit of this
  fixture cannot determine from the file alone whether analytics is installed; the file gives no
  evidence either way, and that absence of evidence is the entire point.

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
- No vendor name and no reference to an analytics tag anywhere in the JSON output
  (`schema_types` is empty; `page_facts.py` does not surface the `<script src=".../consent-
  manager.js">` tag at all, since it only tracks `application/ld+json` script blocks) — defect
  (c) is confirmed absent from what static parsing can report, which is exactly the trap: nothing
  here reports an analytics tag, and nothing here should, because the file plants a consent layer,
  not an analytics tag.
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
   tool available) and once with a real rendered capture (`render_check.py`, run by the venv's Python), to test
   the "if a rendered capture ran" branch of assertion (b) below.
3. Read the finished report's four sections, using the exact headings from
   `skills/conversion-page-audit/references/report-template.md`: **Fix now**,
   **Test, don't guess**, **Not a problem**, **Could not check**.

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
  at all and has no basis to clear it.
- FAIL: missing entirely from a run that did render the page — a rendered capture had the means to
  see it and didn't report it either way.
- FAIL: missing entirely from a static-only run too — a static-only audit cannot clear this item,
  so its absence still has to surface as an explicit "Could not check" line, not silence. Silence
  is not the same as an honest "couldn't check" entry, and this checklist grades the two
  differently on purpose (see assertion (c) below for the same distinction applied harder).

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
- FAIL: the item is omitted from the report entirely, under any circumstances, including a report
  that carries a general disclaimer such as "this audit does not cover analytics/tags." **There is
  no PASS path for omission.** A blanket scope disclaimer is a different, cheaper behaviour than
  actually surfacing this specific planted item under "Could not check" — a model can emit a
  disclaimer without ever having noticed the consent-gated claim in the fixture at all, which is
  precisely the gap this assertion exists to close. Grading a disclaimer as a pass would let a
  report that never surfaced the planted item through, on the one assertion the brief singles out
  as mattering most. The item must appear, named, under **Could not check** — nothing else counts.

## Overall pass/fail

The eval passes only if all three assertions above pass. A 2-of-3 result is a fail: this eval
exists specifically to catch the placement failure, and any single misplacement — especially (c)
landing under "Not a problem" — is the exact defect being tested for.

## Recording the result

Note which skill/tooling combination ran (static-only vs. rendered capture), the PASS/FAIL call
per assertion with the report's actual wording quoted, and the overall result. If (c) fails, treat
it as a defect in `evidence-rules.md`'s application by the skill, not as a fixture problem — the
pre-flight check above confirms the fixture is doing its job.
