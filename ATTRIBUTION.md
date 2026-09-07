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
| [autonnel/autonnel-skills](https://github.com/autonnel/autonnel-skills) | autonnel | Apache-2.0 | The four-section audit report shape (Fix now / Test, don't guess / Not a problem / Could not check), the evidence-boundary pattern, and — from that repo's `landing-page-conversion-audit` skill — the impact-ordered check categories (message match, above-the-fold clarity, offer clarity, trust at the decision moment, the path after conversion, measurement), redistributed under a page-section structure. |

**Note on Alex Hormozi:** Alex Hormozi is a real person. This plugin describes frameworks as
Hormozi-derived. It is not affiliated with, endorsed by, or authored by him.

**Repositories considered and excluded:** two further repositories were evaluated during research
and are deliberately not listed as sources — `rediumvex/hormozi-sales-cold-outreach-claude` and
`Microck/ordinary-claude-skills`. Both carry no licence (NOASSERTION — all rights reserved under
default copyright), so nothing was drawn from either.

## 2. Statement of changes

Required by Apache-2.0 §4(b) for the derivation from `autonnel/autonnel-skills`.

The `conversion-page-audit` skill adapts two structural ideas from that repository, both from its
`landing-page-conversion-audit` skill.

The first is the practice of splitting an audit report into four sections by evidence status —
findings to fix now, findings that need a live test rather than a guess, items checked and found
not to be a problem, and items that could not be checked from the evidence available. That shape,
and the underlying discipline of never asserting "not a problem" without having actually checked,
is what `references/report-template.md` reproduces.

The second, added when `references/audit-framework.md` was written, is that skill's procedure
section: a set of impact-ordered categories for auditing a page under paid traffic — message match
between the traffic source and the page, above-the-fold clarity on a mobile viewport, offer clarity
(what it is, who it's for, what it costs, what happens on click), trust signals placed at the
moment of decision rather than left in the footer, what happens after the conversion action, and
whether the funnel is actually measured. `audit-framework.md` does not keep that skill's ordering
or its lettered grouping: it redistributes the same categories under the eleven page sections
`conversion-page-build` writes, because that page-section structure — not a checklist ordered by
paid-traffic impact — is what the rest of this plugin needs the audit to line up against. The
categories and the reasoning behind each are adapted; the structure they are organized into is this
project's own.

Beyond these two adaptations, nothing else was taken. All prose in this repository was written
independently for `nca-conversion` — no file, sentence, or code snippet from
`autonnel/autonnel-skills` was copied, translated, or reproduced. No source files from that
repository are vendored anywhere in this repository.

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
| `skills/conversion-page-audit/references/audit-framework.md` | `autonnel/autonnel-skills` — `landing-page-conversion-audit` (Apache-2.0) | Structural pattern and reasoning framework: the impact-ordered check categories (message match, above-the-fold clarity, offer clarity and risk reversal, trust signals at the decision moment, the path after conversion, measurement) are adapted from that skill's procedure section, then redistributed under this file's own page-section headings rather than kept in the source's lettered grouping or order. The per-section checks, the markup-versus-rendered caveats tying each check back to `evidence-rules.md`, and all prose are original. No text copied. |
| `skills/conversion-page-audit/references/audit-framework.md` | `coreyhaines31/marketingskills` — `cro` skill (MIT) | Structural pattern: the seven impact-ordered dimensions in that skill's "CRO Analysis Framework" (value proposition clarity, headline effectiveness, CTA placement/copy/hierarchy, visual hierarchy and scannability, trust signals and social proof, objection handling, friction points) map onto this file's Hero, CTA, Proof, Objections and page-level headings. Terminology and impact-ordering only; the mapping onto an eleven-section, builder-aligned structure and all prose are original — the source organizes by dimension, never by page section. No text copied. |
| `skills/conversion-page-audit/references/report-template.md` | `autonnel/autonnel-skills` — `landing-page-conversion-audit` (Apache-2.0) | Structural pattern only, the same one recorded for `evidence-rules.md` above, applied here to the actual fillable template: the four-section split by evidence status and the discipline that an unrun check cannot be reported as "Not a problem." The bracketed fill-in structure, the per-section evidence and feasibility instructions, and all prose are original — this file's shape is four sections, not that skill's five (it also emits a page-level "Verdict" section this file deliberately omits). No text copied. |
| `skills/conversion-page-audit/references/form-and-signup-audit.md` | `coreyhaines31/marketingskills` — `cro/references/form.md`, `signup` and `popups` skills (MIT) | Reasoning framework: the field-cost-by-count rule of thumb, the required-vs-deferrable field test, the label-versus-placeholder distinction, and the popup trigger types (time delay, scroll depth, exit intent, click-triggered) with frequency-capping discipline are drawn from those three files. The framing of each as a markup-checkable-versus-rendered-only signal (tied back to `evidence-rules.md`), the specific detection gaps named for `page_facts.py` (no label/placeholder distinction, no `checked` attribute, no social-auth CTA hints), and all prose are original — none of the three sources discusses what a static-markup parser can or cannot see. No text copied. |
| `skills/conversion-page-audit/references/test-design.md` | `coreyhaines31/marketingskills` — `ab-testing` skill and `ab-testing/references/sample-size-guide.md` (MIT) | Reasoning framework: the hypothesis structure (because/we-believe/will-cause/measured-by), the definition of minimum detectable effect, and the illustrative relationship between effect size and required sample size are drawn from those two files; the specific comparison used here (a 3%-baseline, 10%-lift-versus-50%-lift contrast) is a rewritten illustration of the same relationship the source's tables show, not a reproduction of the tables themselves. The "why most SME pages cannot A/B test" argument and all prose are original — the source states sample-size mechanics but does not make the small-traffic non-viability argument this file makes. No text copied. |
