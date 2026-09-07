# Manual eval: register fidelity

**Status:** hand-run. Automated (`claude plugin eval nca-conversion --case register-fidelity
--ablation with-without --runs 3`) is blocked — `claude plugin eval` reports early access is
unavailable for this account (`init` and the runner both exit 1 with that message; confirmed
2026-09-07). This checklist carries the same assertions a `case.yaml` would have encoded, so the
move to automated form is a transcription, not a redesign.

This is spec §10's "the eval that matters most": whether the register layer
(`skills/audience-research/references/register-profiles.md`) actually changes anything, or is
along for the ride. A page that reads the same in two registers means the register input is
decorative, and every skill downstream of it (offer-architect, conversion-page-build, hook-lab,
copy-sweeps) is not doing the thing it claims to do.

## Setup

One offer, held constant across all three arms below:

> **Offer:** A project-management tool for small agencies (5-20 people) that replaces
> spreadsheets and email threads for client work tracking. $49/user/month, annual plans get two
> months free, 14-day free trial, no credit card required to start the trial.

Pick a single deliverable type to hold constant across arms — a hero section (headline + one
supporting line + CTA) is short enough to compare quickly and long enough to show all seven
dimensions. Use `nca-conversion:conversion-page-build`'s hero step, or `hook-lab` if you only want
headline-level output — either is fine as long as all three arms use the *same* skill and the same
brief section.

## Arms

**Arm A — Conservative B2B (DACH) register.**
Run the offer above through the chosen skill with register explicitly set to
`Conservative B2B (DACH)`. Save the output as `arm-a-conservative-b2b.md` (not committed; this is
a scratch run).

**Arm B — Direct-response register.**
Same offer, same skill, same deliverable type. Register explicitly set to `Direct-response`. Save
as `arm-b-direct-response.md`.

**Arm C — No-plugin baseline (R3).**
Disable the plugin (`claude plugin disable nca-conversion@nca-conversion`), then, **from a
directory outside this repository** (this repo IS the plugin source — a session run from inside it
can read `skills/` off the filesystem regardless of enablement state, which would leak the exact
thing this arm is supposed to exclude), ask a fresh Claude Code session to write the same hero
section for the same offer, with no register specified and no reference to this plugin's
frameworks or terminology. Save as `arm-c-no-plugin.md`. Re-enable the plugin afterward:
`claude plugin enable nca-conversion@nca-conversion`.

> **On Arm C's evidentiary weight:** this is a hand-run substitute for `--ablation with-without`'s
> mechanical score delta, which spec §12 criterion 1 ("the plugin beats no plugin") was meant to
> be measured by. A human skimming two outputs and judging "the plugin version is better" is
> weaker evidence than a scored delta across multiple runs — it has no baseline distribution, no
> repetition, and is vulnerable to the rater's own priors about which one is "supposed" to win.
> Grading it yourself, having just written or read Arm A/B, is weaker still — you already know
> which output is "supposed" to be the plugin's. **Arm C on its own does not establish
> criterion 1.**

**Arm C rubric.** Judge Arm C only against Arm A (the register actually chosen for the offer —
Conservative B2B fits a B2B project-management tool best; use that arm as the comparison), on
these three dimensions, each scored DIVERGE-FOR-PLUGIN / SAME / DIVERGE-FOR-BASELINE:

1. **Proof requirements** — does Arm A back its claim with something concrete (a specific
   mechanism, a scoped number, a named proof type) that Arm C's output lacks or does more
   generically?
2. **CTA directness** — does Arm A's call to action follow the value-equation-driven structure the
   framework layer specifies (a clear next step tied to the offer's actual terms — trial length, no
   card required) more precisely than Arm C's?
3. **Claim intensity** — does Arm A make a sharper, more specific claim about the offer than Arm
   C's more generic "helps you manage projects" framing, while still qualifying it the way
   Conservative B2B requires?

- **Arm C PASS** (suggestive only, per the caveat above): at least 2 of 3 dimensions score
  DIVERGE-FOR-PLUGIN.
- **Arm C FAIL** (a real finding, not just weak evidence): 0 or 1 of 3 dimensions score
  DIVERGE-FOR-PLUGIN, or any dimension scores DIVERGE-FOR-BASELINE — concretely, this means the
  no-plugin output reads as good as or better than the plugin output on that axis, which is the
  literal failure of spec §12 criterion 1 ("the plugin beats no plugin") that this arm exists to
  hand-check.

## Assertions — Arm A vs. Arm B

Grade strictly on the seven dimensions `register-profiles.md` defines for each archetype. Do not
grade on any dimension it does not name.

For each dimension below, mark **DIVERGE** (the two outputs are recognisably different on this
axis, in the direction the two profiles predict) or **SAME** (no meaningful difference):

1. **Sentence rhythm** — Conservative B2B should read as measured, complete sentences;
   Direct-response should show shorter, punchier cadence built around one countable outcome.
2. **Claim intensity** — Conservative B2B should hedge and qualify; Direct-response should make a
   sharper, more specific claim (and, per its own failure mode, should still show the arithmetic
   behind it rather than bare confidence).
3. **Proof requirements** — what each arm points to as evidence should differ in kind, not just
   wording.
4. **Urgency and scarcity handling** — Conservative B2B should carry little or no urgency device;
   Direct-response should use one, and it should not be a device that "resets" (its own named
   failure mode).
5. **CTA directness** — Direct-response's CTA should ask more plainly and immediately than
   Conservative B2B's.
6. **Formality** — Conservative B2B should read distinctly more formal/institutional than
   Direct-response.
7. **Language notes** — idiom, contraction use, and address (formal vs. direct address) should
   differ.

## Pass / fail

- **PASS**: at least 5 of 7 dimensions score DIVERGE, and the direction of each divergence matches
  the profile each arm was assigned (not just "different," but different the way the two profiles
  predict).
- **FAIL**: 4 or fewer dimensions DIVERGE, or the divergences run backwards (e.g. Arm A reads more
  urgent than Arm B).
- **What a FAIL means**: this is not a case to re-word or re-run for luck. A near-identical pair of
  outputs under two different registers means the register layer described in
  `register-profiles.md` is not being applied — spec §4's two-layer architecture (framework layer
  vs. register layer) is failing at the layer that is supposed to vary. Report it as a defect in
  the register-selection or register-application step of whichever skill was run, not as an eval
  that needs a better prompt.

## Recording the result

Note, per run: which skill was used, the DIVERGE/SAME call per dimension with a one-line reason,
the overall Arm A/B PASS/FAIL, and the Arm C rubric score (which of the 3 dimensions scored
DIVERGE-FOR-PLUGIN, with a one-line reason each) plus its PASS/FAIL verdict and the weaker-evidence
caveat restated alongside it. Keep scratch arm outputs out of the repo (they are not fixtures with
known content — they are one-off model output) unless a specific run needs to be preserved as a
regression example.
