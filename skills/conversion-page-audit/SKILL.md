---
name: conversion-page-audit
description: "Use when auditing a live landing page, sales page, pricing page or signup flow for conversion problems — given a URL or a page the user wants reviewed. Produces a ranked report: Fix now, Test don't guess, Not a problem, and Could not check. Also use when the user says 'audit this page', 'why isn't this converting', 'review my landing page', 'CRO audit', 'conversion audit', or pastes a URL and asks what is wrong with it. Works without a Conversion Brief but notes its absence as a limitation."
license: MIT
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/conversion-page-audit/scripts/page_facts.py *)
metadata:
  version: 0.1.0
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
   returns ten keys parsed from static markup only — `url`, `title`, `meta_description`,
   `headings`, `ctas`, `forms`, `schema_types`, `images`, `lcp_candidates`, `notes`. Treat `notes`
   as an unordered set and match entries by their content, never by position — the array's order
   has already changed once between tasks and carries no guarantee it won't again. `lcp_candidates`
   are the first images in document order, not a measured Largest Contentful Paint; see
   `references/audit-framework.md` for exactly what that distinction does and does not license you
   to claim.
3. **Get a rendered capture via the Playwright MCP, if it is available.** This is the single most
   important instruction in this skill: **if Playwright is not available, every rendered-only
   check goes to "Could not check" — never to "Not a problem."** Static markup cannot see layout,
   scroll-gated content, consent-gated tags, or anything CSS hides. `references/evidence-rules.md`
   is the full account of what that blindness costs when it gets ignored instead of named.
4. **Check for a Conversion Brief** at `03 Projects/<Project>/_Research/` — or your project's
   research folder if you're not running this inside that setup. Use it if present, to check the
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

By convention in this vault, the report lands at
`03 Projects/<Project>/[C] Conversion Audit — <Page> — <date>.md` — or wherever your project keeps
audit output if you're not running this inside that setup.

If the `humanizer` skill is available, run the finished report through it before sending it
anywhere a client will read it. That step is optional — the audit is complete without it.
