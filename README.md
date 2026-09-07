# nca-conversion

**nca-conversion** is a Claude Code plugin for conversion-centred landing page work — audience
research, offer architecture, page copy, conversion audits, copy editing, hooks, and design
handoff, all in one toolkit. It is framework-driven (the Value Equation, evidence-bounded audits,
seven-sweep editing) and register-aware, so the same reasoning produces deliberately different
copy for different brands rather than one house voice.

## Install

```
/plugin marketplace add ianrexexanes/nca-conversion
/plugin install nca-conversion@nca-conversion
```

## The toggle, and why it exists

Every enabled plugin's component list costs tokens in every conversation, whether or not you touch
it that session — for this plugin, currently about 1,140 tokens (`claude plugin details
nca-conversion` reports the live figure, per-component). A **disabled** plugin costs zero listing
tokens. There's no penalty for installing the whole toolkit and switching it off between projects:

```
claude plugin disable nca-conversion@nca-conversion
claude plugin enable nca-conversion@nca-conversion
```

Leave it off until you're actually doing landing-page or offer work, then switch it on for that
session.

## The seven skills

- **`audience-research`** — produces the Conversion Brief; gates the rest of the build path.
- **`offer-architect`** — Value Equation, value stack, guarantees, and pricing.
- **`conversion-page-build`** — section-by-section landing page copy.
- **`conversion-page-audit`** — ranked findings across four evidence-bounded sections.
- **`copy-sweeps`** — seven editing passes, plus an expert-panel mode.
- **`hook-lab`** — eight hook types, each run through the active register.
- **`design-handoff`** — maps copy to components, then turns it into a Relume brief and a Figma
  spec.

## How the skills chain

The main path is `audience-research` → `offer-architect` → `conversion-page-build` →
`design-handoff`: the brief feeds the offer, the offer feeds the page copy, and the approved copy
feeds the handoff. `conversion-page-audit` also works standalone, against a page that already
exists, with no Conversion Brief required. `copy-sweeps` and `hook-lab` cross-cut — either can run
on copy from any stage that needs editing or headline variants, not just at the end.

Several skills mention `03 Projects/<Project>/...` paths. That's the author's own Obsidian vault
convention, not a requirement of this plugin — every one of those skills also names a fallback
("or your project's research folder"), so any project folder works.

`conversion-page-build` and `conversion-page-audit` both mention an optional `humanizer` skill for
a final pass over reader-facing copy. It isn't part of this plugin; if it isn't installed, both
skills fall back to `copy-sweeps/references/banned-vocabulary.md` instead.

## How registers work

The frameworks above are the reasoning engine, and they travel to any brand or market unchanged.
How that reasoning gets *voiced* is a separate, explicit input — the **register** — chosen per
brand rather than assumed by default. Every skill that writes reader-facing copy asks which
register applies before it writes a word.

Five register archetypes ship with this plugin:

- `Conservative B2B (DACH)`
- `Technical / industrial`
- `Consumer / lifestyle`
- `Mission / nonprofit`
- `Direct-response`

Pick the one that fits the brand, or describe your own on the spot — the framework layer doesn't
change; only its voice does.

## Evals

Automated evals (`claude plugin eval`) are gated behind early access, which this account does not
currently have — `init` and the runner both exit non-zero with that message. Until that opens up,
the two planned cases exist as hand-run checklists under `evals/manual/`:

- `evals/manual/register-fidelity.md` — the same offer at two registers, asserting the outputs
  diverge on the dimensions `register-profiles.md` defines, plus a manual no-plugin baseline arm.
- `evals/manual/audit-could-not-check.md` — a planted-defect fixture
  (`evals/manual/fixtures/planted.html`) graded on whether the audit files each defect under the
  right section, not just whether it finds it.

Both carry the same assertions the automated `case.yaml` files would have encoded, so moving to
automated form later is a transcription, not a redesign.

## Attribution

The external frameworks and structural patterns this plugin draws on, and their licences, are
credited in [ATTRIBUTION.md](./ATTRIBUTION.md).

## Licence

MIT — see [LICENSE](./LICENSE).
