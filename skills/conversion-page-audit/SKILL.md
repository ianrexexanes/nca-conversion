---
name: conversion-page-audit
description: "Use when /cro audit runs it, or when an unscored audit is asked for by name. Returns the four-section report: Fix now, Test don't guess, Not a problem, Could not check."
license: MIT
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/conversion-page-audit/scripts/page_facts.py *) Bash(${CLAUDE_PLUGIN_DATA}/venv/bin/python ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/render_check.py *)
metadata:
  version: 0.3.0
---

# Conversion page audit

**Read `references/evidence-rules.md` before concluding anything.** This is a hard step, not a
suggestion. Every rule in that file exists because a plausible-looking method returned a wrong
answer with total confidence, and the report shape below only stays honest if you've read it
before you start finding things.

## Procedure

1. **Read `references/evidence-rules.md` first.** Not a skim — its closing section is what makes
   the report trustworthy, and it changes how you weigh your own findings, not just how you word
   them.
2. **Gather facts.** Run
   `python3 ${CLAUDE_PLUGIN_ROOT}/skills/conversion-page-audit/scripts/page_facts.py <url>`. It
   returns twelve keys parsed from static markup only: `url`, `title`, `meta_description`, `headings`,
   `links`, `has_footer`, `ctas`, `forms`, `schema_types`, `images`, `lcp_candidates`, `notes`. Treat `notes`
   as an unordered set and match entries by their content, never by position — the array's order
   has already changed once between tasks and carries no guarantee it won't again. `lcp_candidates`
   are the first images in document order, not a measured Largest Contentful Paint; see
   `references/audit-framework.md` for exactly what that distinction does and does not license you
   to claim.
3. **Get a rendered capture with
   `${CLAUDE_PLUGIN_DATA}/venv/bin/python ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/render_check.py <url> --out <dir>`.**
   Rendered evidence comes only from `render_check.py`, the one route that blocks analytics. This
   is the single most important instruction in this skill: **if the venv is missing, every
   rendered-only check goes to Could not check, with the reason and "run `/cro setup`", never to
   Not a problem.** The same holds when the script exits 3 because the page did not load; its
   reason is under `could_not_check` in `render.json`. Static markup cannot see layout,
   scroll-gated content, consent-gated tags, or anything CSS hides. `references/evidence-rules.md`
   is the full account of what that blindness costs when it gets ignored instead of named.
4. **Check for a Conversion Brief** in your project's research folder. Use it if present, to check the
   page's argument and register against real audience research. If it's absent, note that as a
   stated limitation and keep going — a missing brief narrows what you can claim, it never blocks
   the audit.
5. **Produce the report** in the shape `references/report-template.md` defines: Fix now, Test
   don't guess, Not a problem, Could not check. Follow that file's rules for each section — they
   are what keeps a "Not a problem" line from quietly becoming a guess wearing a verified finding's
   clothes.

## What each reference file is for

- `references/evidence-rules.md` — what an audit is allowed to conclude, and from what. Read it
  first, every time.
- `references/audit-framework.md` — the checks themselves, organized by the eleven page sections
  `conversion-page-build` writes, plus the page-level checks that don't belong to any one section.
- `references/form-and-signup-audit.md` — field count, required-field justification, signup flow
  and popup behaviour, in more depth than the framework file carries.
- `references/test-design.md` — whether a "Test, don't guess" finding is actually testable at this
  page's traffic, before you recommend running it.
- `references/report-template.md` — the four-section output shape and the rule that keeps it
  honest.

## Where the report goes

The report is `Conversion Audit — <Page> — <date>.md`, in your project's folder, or wherever your
project keeps audit output.

If the `humanizer` skill is available, run the finished report through it before sending it
anywhere a client will read it. If it isn't installed — a fresh install of this plugin has no
`humanizer` — apply `../copy-sweeps/references/banned-vocabulary.md` to the report directly
instead. That step is optional — the audit is complete without it.
