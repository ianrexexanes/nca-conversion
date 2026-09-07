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

Every enabled plugin's component list costs a few tokens in every conversation, whether or not you
touch it that session. A **disabled** plugin costs zero listing tokens. There's no penalty for
installing the whole toolkit and switching it off between projects:

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
- **`design-handoff`** — turns finished copy into a Relume brief and a Figma spec.

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

## Attribution

The external frameworks and structural patterns this plugin draws on, and their licences, are
credited in [ATTRIBUTION.md](./ATTRIBUTION.md).

## Licence

MIT — see [LICENSE](./LICENSE).
