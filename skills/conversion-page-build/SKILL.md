---
name: conversion-page-build
description: "Use when writing or rewriting copy for a landing page, sales page, homepage, pricing page or opt-in page — after the audience is documented. Walks hero, problem, outcome, solution, mechanism, value stack, proof, objections, guarantee, CTA and FAQ, deciding what each section must accomplish before writing it. Also use when the user says 'write the landing page', 'rewrite this page', 'page copy', 'sales page', 'I need copy for', or hands over an offer and asks for a page. Requires a Conversion Brief — runs audience-research first if none exists."
license: MIT
metadata:
  version: 0.2.1
---

# Conversion page build

**Nothing gets written before a Conversion Brief exists.** Look for
`03 Projects/<Project>/_Research/[C] Conversion Brief — *.md` — or your project's research folder if
you're not running this inside that setup. If none exists, **stop and invoke `audience-research`**
rather than guessing the ICP, the ranked objections, or the register. A page built on a guessed
audience isn't a cheaper version of this skill — it's a different, unreliable skill wearing this
one's structure, and the brief's own Register section is the one input nothing downstream can
recover from if it's wrong (`../audience-research/SKILL.md` — register, once set, is inherited, not
re-decided).

## The procedure: two writing passes, then a spec

Every section below gets written in two passes, in that order, and the second never leaks into the
first. A third output — the section spec, covered later in this file — follows once the copy is
done:

1. **Decide what the section has to accomplish**, using the framework layer — the Value Equation's
   levers, obstacle reversed into solution, objection mapped to hidden objection mapped to belief
   shift mapped to proof, value stacked and anchored against price. This layer is structural. A
   German industrial buyer and a self-serve direct-response buyer need the exact same *thing* proven
   in the Mechanism section — that this works, specifically, for someone in their situation — even
   though nothing about how that proof gets voiced will look the same twice.
2. **Write it in the register the brief specifies.** Register decides claim intensity, what counts
   as proof, whether urgency is usable at all, and how directly the page asks — it is not a tone
   pass applied after the copy is otherwise done. Pull the register named in the brief's Register
   section and hold it across all eleven sections without re-deciding it mid-page.

Skip step 1 and you get fluent copy arguing the wrong thing to the right person. Skip step 2 and you
get an accurate argument nobody in this register will finish reading. Merge them into one pass and
the result is a copy generator wearing this skill's name — the failure this skill exists to prevent.

3. **Produce the section spec**, once the copy for that section is written — see `## The section
   spec` below. A run that stops after steps 1 and 2 has copy but no handoff artifact; the spec is
   not optional trailing paperwork, it is this skill's third output.

## The eleven sections

Hero, Problem, Outcome, Solution, Mechanism, Value stack, Proof, Objections, Guarantee, CTA, FAQ —
in that order, for a page that runs the full argument. `references/page-architecture.md` is that
order and the case for why it's that order and not another. `references/section-playbooks.md` is
what each section has to accomplish and how that changes across the five registers — read the
brief's Register line once, then read only that column for every section, not all five.

Not every page needs all eleven, or in this sequence — `references/page-types.md` covers what a
home page, an opt-in page, a pricing page, a feature page and a full sales page each keep, compress,
or drop, and why the job that page does in the funnel is what decides it.

Two sections carry enough of their own reasoning to need a dedicated file rather than a playbook
column:

- **Objections** — `references/objection-to-belief.md` walks surface objection → hidden objection →
  belief shift → proof, built from the brief's own ranked Objections section rather than a generic
  FAQ list assembled after the copy is already written.
- **Proof** — `references/proof-library.md` ranks proof types by strength and by what each one
  actually costs to obtain, so the section gets built from what the client can produce this week,
  not from what would be nice to have.

`references/conversion-psychology.md` is the mental-model layer the framework reasoning in every
section draws on. Read it once per project, not once per section — it explains *why* a lever works,
not what to write.

## The section spec

Produce one section spec per section, alongside the copy, in this exact shape — `design-handoff`
consumes it by these five key names and no others:

```yaml
section_type: <one of the eleven>
purpose: <what this section has to accomplish, from the framework pass>
content_hierarchy: <what a reader takes in first, second, third within the section>
components: <the concrete elements — heading, subhead, media slot, form, comparison table, badge…>
responsive_intent: <what stacks, collapses, reorders, or hides first on a narrow viewport>
```

Write the spec after the copy, not before. It describes what the copy actually needs to hold, and a
spec written first tends to lock in a layout the copy then gets bent to fit rather than the reverse.

## Before you ship it

If a `humanizer` skill is available in this environment, route the finished copy through it before
calling the page done. If it isn't installed — a fresh install of this plugin has no vault and no
`humanizer` — apply `../copy-sweeps/references/banned-vocabulary.md` to the draft directly instead.
One of the two always runs; which one depends on what's installed, not on whether either step
matters.

## Where the page goes

By convention in this vault, finished page copy lands alongside the brief it was built from —
`03 Projects/<Project>/_Research/[C] Page Copy — <Page> — <date>.md` — or wherever your project
keeps drafted copy if you're not running this inside that setup. This skill produces two things:
the copy itself, and the section spec per section that `design-handoff` consumes. Say where you
filed the copy; a page nobody can find is not a shipped page.
