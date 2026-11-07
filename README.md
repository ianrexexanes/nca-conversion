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

## Version 2: the front door

Version 2 adds an eighth skill, `cro`, in front of the seven. Type `/nca-conversion:cro` and it either starts a project kickoff or sends you to the right skill. It starts no subagents.

| Command | Goes to | Status |
| --- | --- | --- |
| (none) | `references/kickoff.md` | ready |
| `audit <url>` | `references/audit.md` | ready |
| `setup` | `references/setup.md` | ready |
| `doctor` | `references/setup.md` | ready |
| `offer` | the `offer-architect` skill | ready (v1 skill) |
| `sweep` | the `copy-sweeps` skill | ready (v1 skill) |
| `research` | `references/research.md`, with the `audience-research` skill | ready |
| `page <brief>` | `references/page.md`, with the `conversion-page-build` skill | ready |
| `hero` | `references/hero.md`, with the `hook-lab` skill | ready |
| `wireframe` | the `design-handoff` skill | v1 engine until slice 3 |
| `vsl` | `references/vsl.md` | ready |
| `design` | nothing yet | not built yet, slice 3 |
| `check` | nothing yet | not built yet, slice 3 |
| `form` | nothing yet | not built yet, slice 3 |
| `data` | nothing yet | not built yet, slice 3 |
| `compare` | nothing yet | not built yet, slice 3 |
| `diagnose` | nothing yet | not built yet, slice 3 |

### Setup and the PageSpeed key

`/cro setup` builds a small Python environment with a browser for the rendered checks. `/cro doctor` changes nothing and reports what is installed and what is missing.

Built and tested on Linux with bash; needs Python 3.10 or later and Chrome.

Speed checks use a PageSpeed Insights key. Store it in `~/.config/nca-conversion/pagespeed.key` or in the `NCA_PAGESPEED_KEY` environment variable. Never type it into a chat. Without a key, the plugin falls back to local Lighthouse, labelled as lab data, or says it could not check.

### Rendered checks and your client's analytics

Rendered checks run only through `render_check.py`. The common analytics and tag hosts are blocked, and every request is logged in `network-log.json`, so you can see what was not. A finite list is not a guarantee. Only GET, HEAD and OPTIONS leave the browser, the browser presents an ordinary Chrome user agent, and every blocked request is written to a log. No form is sent and nothing is clicked. Web workers are off in the capture, so a map, video or 3D viewer can look blank there while it shows for a visitor.

With a PageSpeed key, the speed check loads the page on Google's servers, where this plugin blocks nothing, and whether that visit shows in the client's analytics is not known. Without a key, local Lighthouse runs with the blocked hosts stopped.

The block list errs toward blocking. A few rules match on the path alone, on any host, because a tag can be served from the site's own domain: an audited page whose own address looks like `/tr?id=5` or `/tr/?id=5` reads as blocked. The browser-level patterns cannot anchor a host, so an unusual host such as `myfacebook.com/tr/` is also stopped there, while the request-level check lets it through. The Meta rules are anchored in both layers, so `facebook.com/trending` stays open. The `/ccm/collect` rules are anchored only in the request-level check: the browser-level patterns cannot end at a path, so an address such as `/ccm/collections` still reads as blocked there. Hosts for which no vendor page was found are marked in `skills/cro/scripts/cro_runtime.py` as unverified.

### Script permissions last one turn

The `cro` skill pre-approves its own scripts through `allowed-tools`, and that approval lasts only for the turn that invokes the skill (see "Pre-approve tools for a skill" at https://code.claude.com/docs/en/skills). When the audit has to ask for the mode, keyword or traffic first, its scripts run in the next turn, and Claude Code asks before each one. To avoid that, give those answers in the command, for example `/nca-conversion:cro audit https://example.com/ mode: Direct; traffic: ads; page role: landing page`. To stop those questions, run `/cro setup --permissions`: it prints allow rules for the plugin's scripts, which you merge into the `permissions.allow` list of `.claude/settings.local.json` in your project. The rules name the installed version's folder, so run it again after each `claude plugin update`.

### Two modes

Every page has one mode. A Search page gets its visitors from organic search for a keyword you have researched. A Direct page gets the visitors its owner sends, such as paid ads, outreach or email. The audit asks the mode first and reads its anchors by mode. On a Search page it adds a Search check that sits outside the score. The plugin never picks a keyword: you bring it from keyword research.

## The toggle, and why it exists

Every enabled plugin's component list costs tokens in every conversation, whether or not you touch
it that session. For this plugin the listing stays under about 1,350 tokens, and
`claude plugin details nca-conversion` reports the live figure. A **disabled** plugin costs zero listing
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

Skills that save a file name it after what it holds, such as `Conversion Brief — <Client>.md`, and save it in your project's folder, or wherever your project keeps that kind of file.

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
