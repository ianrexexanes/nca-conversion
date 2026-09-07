# Attribution

`nca-conversion` is original writing. Nothing in this repository is installed, vendored, or
copied from another project. The table below records which external repositories the *thinking*
— frameworks, structural patterns, terminology — draws on, so the intellectual debt is visible
even where no source file was ever pulled in.

## 1. Sources

| Repo | Author | Licence | What was drawn from it |
| --- | --- | --- | --- |
| [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | Corey Haines | MIT | CRO framework, copywriting, copy-editing sweeps, marketing-council/expert-panel, offers, pricing, marketing-psychology, signup, popups, ab-testing, customer-research, product-marketing. Not installed or vendored — content rewritten. |
| [alexsmedile/hormozi-skills](https://github.com/alexsmedile/hormozi-skills) | alexsmedile | MIT | Hormozi framework layer: Value Equation, offer construction, hooks, pitch formats. |
| [Mahanaicoach/alex-hormozi-coach](https://github.com/Mahanaicoach/alex-hormozi-coach) | Mahanaicoach | MIT | `VOICE.md` (five voice laws, phrase bank, say-this-not-that) — the basis for the direct-response register profile. |
| [jonathanmalkin/hormozi-brain-claude-project](https://github.com/jonathanmalkin/hormozi-brain-claude-project) | jonathanmalkin | MIT | Frameworks summary and `sources.csv`. |
| [autonnel/autonnel-skills](https://github.com/autonnel/autonnel-skills) | autonnel | Apache-2.0 | The four-section audit report shape (Fix now / Test, don't guess / Not a problem / Could not check) and the evidence-boundary pattern. |

**Note on Alex Hormozi:** Alex Hormozi is a real person. This plugin describes frameworks as
Hormozi-derived. It is not affiliated with, endorsed by, or authored by him.

**Repositories considered and excluded:** two further repositories were evaluated during research
and are deliberately not listed as sources — `rediumvex/hormozi-sales-cold-outreach-claude` and
`Microck/ordinary-claude-skills`. Both carry no licence (NOASSERTION — all rights reserved under
default copyright), so nothing was drawn from either.

## 2. Statement of changes

Required by Apache-2.0 §4(b) for the derivation from `autonnel/autonnel-skills`.

The `conversion-page-audit` skill adapts one structural idea from that repository: the practice of
splitting an audit report into four sections by evidence status — findings to fix now, findings
that need a live test rather than a guess, items checked and found not to be a problem, and items
that could not be checked from the evidence available. That shape, and the underlying discipline of
never asserting "not a problem" without having actually checked, is what was adapted.

Nothing else was taken. All prose in this repository was written independently for
`nca-conversion` — no file, sentence, or code snippet from `autonnel/autonnel-skills` was copied,
translated, or reproduced. No source files from that repository are vendored anywhere in this
repository.

## 3. Derivation map

Each row below names one file in this repo, the source it draws from, and the nature of the
derivation (structural pattern, terminology, or reasoning framework — never copied text). This
table is appended to by every task that draws on one of the sources above, as each one lands.

| File in this repo | Source | Nature of derivation |
| --- | --- | --- |
| `skills/conversion-page-audit/references/evidence-rules.md` | `autonnel/autonnel-skills` (Apache-2.0) | Structural pattern only: the four-section report split by evidence status, and the "Could not check" boundary that this file's closing section makes operative. The eleven rules themselves are original, written from first-hand verification failures. No text copied. |
| `skills/audience-research/references/register-profiles.md` | `Mahanaicoach/alex-hormozi-coach` — `VOICE.md` (MIT) | Reasoning framework for the `Direct-response` profile only: its voice-laws, phrase-bank and say-this-not-that structure shaped how that one register's dimensions and failure modes are characterised. Rewritten; no text copied. The other four profiles are original. |
| `skills/audience-research/references/market-selection.md` | `alexsmedile/hormozi-skills` (MIT) | Reasoning framework: the four-signal market evaluation (pain, purchasing power, ease of targeting, growth) and the practice of narrowing a category into a sub-market before building an offer, both drawn from the Value Equation / market-selection line of thinking in that repo. Terminology only; the sub-market narrowing dimensions, the scoring guidance, and all prose are original. No text copied. |
| `skills/audience-research/references/research-modes.md` | `coreyhaines31/marketingskills` (MIT) | Structural pattern: the three-mode research structure, its Mode 1/2/3 boundaries (existing assets, public/passive online sources, direct primary research) and the cost ordering — mine what's public before you ask — are drawn directly from the `customer-research` skill's "Three Modes of Research" section. The per-mode exhaustion signals (the explicit trigger for when a mode is spent and escalation is warranted), the yield/cost framing, and all prose are original — the source states the ordering but carries no equivalent exhaustion test. No text copied. |
| `skills/audience-research/references/voice-of-customer-mining.md` | `coreyhaines31/marketingskills` (MIT) | Structural pattern: the source-type list this file ranks (interview/call transcripts, support tickets, reviews, forums, churn notes) overlaps substantially with the `customer-research` skill's Mode 1 asset types and Mode 2 source table, and the "quote, don't summarize" discipline mirrors that skill's extraction-table instruction to capture "exact words — don't paraphrase." The ranking of sources by how unfiltered the language is, the "fix nothing" and "attribute the source, not the identity" rules, and all prose are original — the source does not rank its sources against each other. No text copied. |
| `skills/audience-research/references/persona-and-jtbd.md` | `coreyhaines31/marketingskills` (MIT) | Structural pattern: this file's job/trigger/what-they're-firing/what-success-looks-like persona fields track the `customer-research` skill's "Persona Structure" template fields (Primary Job to Be Done, Trigger Events, Alternatives They Consider, Desired Outcomes) closely enough to be a direct structural derivation, not merely a shared JTBD vocabulary. Correction from an earlier version of this row: attributed to "product-marketing and customer-research skills" without having fetched the product-marketing skill — that skill was never verified and the claim is withdrawn; the derivation is from `customer-research` alone. The buyer/attendee distinction, the ranking guidance (primary/secondary/tertiary), and all prose are original — no equivalent split appears in the source. No text copied. |
