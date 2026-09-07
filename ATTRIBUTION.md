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
| [autonnel/autonnel-skills](https://github.com/autonnel/autonnel-skills) | autonnel | Apache-2.0 | The four-section audit report shape (Fix now / Test, don't guess / Not a problem / Could not check), the evidence-boundary pattern, and — from that repo's `landing-page-conversion-audit` skill — the impact-ordered check categories (message match, above-the-fold clarity, offer clarity, trust at the decision moment, the path after conversion, measurement), redistributed under a page-section structure, plus one reporting-discipline rule (never promise a percentage lift for a specific fix; rank relatively instead). |

**Note on Alex Hormozi:** Alex Hormozi is a real person. This plugin describes frameworks as
Hormozi-derived. It is not affiliated with, endorsed by, or authored by him.

**Repositories considered and excluded:** two further repositories were evaluated during research
and are deliberately not listed as sources — `rediumvex/hormozi-sales-cold-outreach-claude` and
`Microck/ordinary-claude-skills`. Both carry no licence (NOASSERTION — all rights reserved under
default copyright), so nothing was drawn from either.

## 2. Statement of changes

Required by Apache-2.0 §4(b) for the derivation from `autonnel/autonnel-skills`.

The `conversion-page-audit` skill adapts three ideas from that repository, all from its
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

The third is a specific report-writing rule from that same skill's rules for its output shape:
never attach a promised percentage lift to an individual fix, because a lift figure measured on one
page does not transfer to another — state expected direction and use a relative ranking instead.
`references/report-template.md` carries this rule in its "Fix now" section, in wording rewritten to
a different construction from the source's own sentence.

**Correction, made during a review pass:** an earlier version of `references/report-template.md`
stated this third rule in wording close enough to the source's own sentence — sharing its opening
clause nearly verbatim and reordering the remainder — that it was a close paraphrase rather than an
independent formulation, while this section and that file's derivation row in §3 both asserted at
the time that no text had been copied. Both statements were wrong as shipped. The sentence has
since been rewritten to a genuinely different construction, the third adaptation above has been
added here to disclose the rule explicitly instead of leaving it implicit, and the §3 row for
`report-template.md` has been corrected to match. Because that review pass found this failure mode
once, every other new reference file introduced alongside it was re-checked against its cited
source for the same thing — not "was a paragraph copied" but "is any clause of mine reproducible
word for word from theirs" — and several further close paraphrases were found in
`references/audit-framework.md`, `references/form-and-signup-audit.md` and
`references/test-design.md` and reworded. Each is noted in that file's own row below rather than
re-narrated here.

Beyond these three adaptations, nothing else was taken. All prose in this repository, as currently
shipped, is written independently for `nca-conversion` — no file, sentence, or code snippet from
`autonnel/autonnel-skills` is copied, translated, or reproduced. No source files from that
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
| `skills/conversion-page-audit/references/audit-framework.md` | `autonnel/autonnel-skills` — `landing-page-conversion-audit` (Apache-2.0) | Structural pattern and reasoning framework: the impact-ordered check categories (message match, above-the-fold clarity, offer clarity and risk reversal, trust signals at the decision moment, the path after conversion, measurement) are adapted from that skill's procedure section, then redistributed under this file's own page-section headings rather than kept in the source's lettered grouping or order. **Corrected during review, in two passes** (a manual re-read, then an automated word-for-word overlap check against the fetched source once manual review kept finding more instances): the Hero, Solution, Proof, Guarantee, CTA and Measurement bullets were initially close paraphrases of the source's own sentences, headings and example lists — including its "guarantee, trial, 'cancel anytime'" example set, its "Anonymous filler reads as fake and costs more than it earns" sentence, its "Is a conversion event firing at all?" question, its "Price presented, or hidden?" label, its "F. The path after the button" heading, and its "visible without scrolling on a [viewport]" phrase, several reproduced verbatim or near-verbatim — rather than independent restatements; all were reworded to different constructions, different examples and different labels, and the source's `links`-style internal-only field was corrected to no longer be described as something the audit can query directly. The remaining per-section checks, the markup-versus-rendered caveats tying each check back to `evidence-rules.md`, and all other prose are original. No text copied. |
| `skills/conversion-page-audit/references/audit-framework.md` | `coreyhaines31/marketingskills` — `cro` skill (MIT) | Structural pattern: the seven impact-ordered dimensions in that skill's "CRO Analysis Framework" (value proposition clarity, headline effectiveness, CTA placement/copy/hierarchy, visual hierarchy and scannability, trust signals and social proof, objection handling, friction points) map onto this file's Hero, CTA, Proof, Objections and page-level headings. **Corrected during review, in two passes** (manual, then an automated word-for-word overlap check): the Hero, CTA, Objections and Visual-hierarchy bullets were initially close paraphrases of the source's own sentences — including its "one clear primary action" language, its "Start Free Trial" vs. "Submit" CTA example pair, its own "CTA Placement, Copy, and Hierarchy" heading (reconstructed by this file's section heading plus an adjacent bold label), its "will this work for my situation" / "what if it doesn't work" objection quotes, its "FAQ sections, guarantees, comparison content, process transparency" resolution list in the same order, and its "can someone scanning get the main message" / "most important elements ... visually prominent" phrasing — rather than independent restatements; all were reworded to different constructions, different examples, and, where the source used a specific ordered list, a different order. This file's "Visual hierarchy and scannability" heading itself is knowingly kept as the source's own dimension name — that is the terminology adaptation this row already discloses — while the prose beneath it no longer echoes the source's sentences. Terminology and impact-ordering only now remain adapted; the mapping onto an eleven-section, builder-aligned structure and all other prose are original — the source organizes by dimension, never by page section. No text copied. |
| `skills/conversion-page-audit/references/report-template.md` | `autonnel/autonnel-skills` — `landing-page-conversion-audit` (Apache-2.0) | Structural pattern, the same one recorded for `evidence-rules.md` above, applied to the actual fillable template: the four-section split by evidence status and the discipline that an unrun check cannot be reported as "Not a problem." Also adapts one specific reporting rule from that skill's output-rules list: never attach a promised percentage lift to a fix — state direction and rank relatively instead. **Correction, made during review, in two passes** (manual, then an automated word-for-word overlap check, which is what caught the second and third items below): three passages were close paraphrases rather than independent constructions. The percentage-lift rule's sentence shared the source's opening clause ("Never claim a percentage lift for a specific fix") nearly verbatim. The "Fix now" section's descriptive sentence ("names the element, the failure mode, the specific change") and its bracketed fill-in line (`<element> - <failure mode> → <specific change>`) both reproduced the source's own report-line template almost exactly. All three have been rewritten to different constructions and a different template shape; the percentage-lift rule's adaptation is now stated explicitly in §2 rather than left undisclosed. The per-section evidence and feasibility instructions, the pointer to `test-design.md` for the hypothesis shape, and all other prose are original — this file's shape is four sections, not that skill's five (it also emits a page-level "Verdict" section this file deliberately omits). No text copied. |
| `skills/conversion-page-audit/references/form-and-signup-audit.md` | `coreyhaines31/marketingskills` — `cro/references/form.md`, `signup` and `popups` skills (MIT) | Reasoning framework: the field-cost-by-count rule of thumb (including its specific tier boundaries and percentage ranges, restated in prose rather than as a table), the required-vs-deferrable field test, the label-versus-placeholder distinction, and the popup trigger types (time delay, scroll depth, exit intent, click-triggered) with frequency-capping discipline are drawn from those three files. **Corrected during review:** four passages were initially close paraphrases rather than independent restatements and have been reworded — the labels-versus-placeholders sentence, a near-verbatim match of a sentence that appears identically in both `form.md` and `signup.md` ("placeholders disappear when typing, leaving users unsure what they're filling in"); the required-field question, which mirrored `form.md`'s "is this needed *now*, or can it be collected after payment?" structure; the social-auth performance claim, which reused `signup.md`'s "than the email path alone" phrase near-verbatim; and the single-step/multi-step guidance, which reused `signup.md`'s "feel completable in seconds" phrase verbatim alongside a close paraphrase of "harder questions later." The framing of each check as a markup-checkable-versus-rendered-only signal (tied back to `evidence-rules.md`), the specific detection gaps named for `page_facts.py` (no label/placeholder distinction, no `checked` attribute, no social-auth CTA hints, and no exposed field for the full link/button list `ctas` is filtered from), and all other prose are original — none of the three sources discusses what a static-markup parser can or cannot see. No text copied. |
| `skills/conversion-page-audit/references/test-design.md` | `coreyhaines31/marketingskills` — `ab-testing` skill and `ab-testing/references/sample-size-guide.md` (MIT) | Reasoning framework: the definition of minimum detectable effect and the illustrative relationship between effect size and required sample size are drawn from those two files; the specific comparison used here (a 3%-baseline, 10%-lift-versus-50%-lift contrast) is a rewritten illustration of the same relationship the source's tables show, verified against that table's own figures (5,200/10,400 at a 50% lift, 120,000/240,000 at a 10% lift), not a reproduction of the tables themselves. The five-part hypothesis structure is adapted from the source's hypothesis template. **Corrected during review:** an earlier version of this file, and of `report-template.md`, reused that template's own connective wording ("Because … we believe … will cause … for …, we'll know this is true when …") nearly verbatim; both now use a differently-worded five-part shape ("prompted by / propose / predict / for / settle it with") that keeps the same five semantic slots without the source's own sentence grammar, and `report-template.md` now points to this file for the shape instead of restating it. The "why most SME pages cannot A/B test" argument and all other prose are original — the source states sample-size mechanics but does not make the small-traffic non-viability argument this file makes. No text copied. |
