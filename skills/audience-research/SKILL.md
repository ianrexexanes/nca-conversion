---
name: audience-research
description: "Use before writing landing/sales page or campaign copy when the audience isn't documented. Produces a Conversion Brief: ICP, personas, ranked problems, voice-of-customer, competitors, differentiation, objections, proof, register. Required before conversion-page-build; optional for conversion-page-audit."
license: MIT
metadata:
  version: 0.3.0
---

# Audience research

**Nothing gets written before this.** `conversion-page-build` refuses to write page copy until a
Conversion Brief exists for the client. `conversion-page-audit` can run without one, but an audit
without a brief has no register to check the page against and no ranked problem list to check the
argument against — run this first when either is missing.

## Research modes

Three modes, in cost order — cheapest first, escalate only when the cheaper one is exhausted. See
`references/research-modes.md` for what each yields, what it costs, and the signal that means it's
exhausted and the next mode is warranted.

## The brief

Fill `assets/conversion-brief-template.md` — copy it, don't summarize it. Thirteen sections: Page modes and
keywords, Traffic and awareness, ICP, Personas, Problems (ranked), Voice of customer, Competitive
landscape, Differentiation, Objections, Proof available, Visual inventory, Register, Open and
unconfirmed. Each section in the template states what it
establishes and the failure mode of leaving it thin — read those before filling, not after.

Three sections have their own reference file, because getting them wrong is expensive and the
reasoning doesn't fit in the template margin:

- **Voice of customer** — `references/voice-of-customer-mining.md` (where the verbatim language
  actually lives, and how not to paraphrase it into marketing register on the way in).
- **Register** — `references/register-profiles.md` (the five archetypes, their seven dimensions
  each, and which one this client's buying situation actually signals).
- Choosing which market or sub-market the ICP even is — `references/market-selection.md`, and once
  the market is chosen, `references/persona-and-jtbd.md` for who inside it the page is written to.

## Where the brief goes

By convention in this vault, the file lands at
`03 Projects/<Project>/_Research/[C] Conversion Brief — <Client>.md` — or your project's research
folder if you're not running this inside that setup.

## NOT ESTABLISHED

A section you cannot fill is written as `NOT ESTABLISHED — <what it would take>`, never deleted or
left blank. A missing section reads as "not researched"; `NOT ESTABLISHED` reads as "researched,
here's the specific gap" — the one that actually gets closed. See the template's opening note for
why this is the rule rather than a suggestion.
