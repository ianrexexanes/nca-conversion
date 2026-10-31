---
name: copy-sweeps
description: "Use when editing or tightening any written marketing copy — page copy, an email, a proposal, an ad, a post. Runs seven passes: Clarity, Voice, So What, Prove It, Specificity, Heightened Emotion, Zero Risk. Also use when the user says 'edit this', 'tighten this copy', 'make this better', 'this reads flat', 'punch this up', or pastes copy and asks for a second look. Optional expert-panel mode."
license: MIT
metadata:
  version: 0.2.0
---

# Copy sweeps

Something is already written. This skill improves it without taking it over. Seven passes, each
looking for one kind of defect, because a single read that watches for everything reliably notices
whichever problem is loudest and walks past the rest.

## No Conversion Brief is required, and that is the point

Every other skill in this plugin either produces a Conversion Brief or reads one. This one runs on
whatever is in front of it: an email, half a landing page, a proposal paragraph a client sent back
with a question mark on it. Editing is where work arrives unannounced, and a gate here would mean
the pass never runs.

If a brief does exist — `03 Projects/<Project>/_Research/[C] Conversion Brief — *.md` under this
vault's filing, or wherever else your project keeps research — read three of its sections first,
because they change what the passes are permitted to do rather than merely informing them: the
**Register** it names, its ranked **Objections**, and what it lists under **Proof available**.

Without one, run anyway, and carry two habits:

- **Infer the register from the copy, label the inference, and do not silently correct toward your
  own taste.** Copy written in an unfamiliar register reads as wrong to an editor who has not been
  told which one it is in, and the resulting edit is the most expensive kind: fluent, confident, and
  aimed at the wrong reader.
- **An edit that changes what is being claimed is a different act from an edit that changes how it
  is said.** Flag the first kind separately and hand it back as a question. You do not know what the
  business can actually deliver, and a sharpened claim nobody can honour is a defect you introduced.

## Register decides what each pass is allowed to do

The seven passes are the same everywhere. What each one may change is not. The clearest case is
Heightened Emotion: in `Conservative B2B (DACH)` that pass adds no adjectives at all — it deletes
hedges, because what carries feeling for that reader is a plain statement of his own situation, and
every "can help" and "is designed to" drains it. The same pass in `Direct-response` genuinely adds.
Two opposite operations, one pass name.

The five: `Conservative B2B (DACH)` · `Technical / industrial` · `Consumer / lifestyle` ·
`Mission / nonprofit` · `Direct-response`. Defined in
`../audience-research/references/register-profiles.md`. Every pass in `references/seven-sweeps.md`
closes with a register note naming the registers where that pass behaves differently — not all five
every time. Where the register in play is not named, no special handling applies and the pass runs
as written.

## The seven passes

Run them in this order and do not reorder them — each pass hands the next one a cleaner input, and
the emotional passes are late deliberately, so they work on a claim that has already been made
specific and provable rather than dressing up one that has not.

1. **Clarity** — can the sentence be read only one way?
2. **Voice** — is one person speaking throughout?
3. **So What** — does every capability arrive with its consequence attached?
4. **Prove It** — is there an artifact behind the claim, or only the claim?
5. **Specificity** — is the claim measured, or merely enthusiastic?
6. **Heightened Emotion** — does the reader recognise their own situation in it?
7. **Zero Risk** — what is still open when the reader reaches the ask?

Full definitions, what each pass may and may not touch, a before/after, and the per-register note:
`references/seven-sweeps.md`. That file also carries the **regression rule** — the three specific
places where a later pass predictably breaks an earlier one, which is what you re-check instead of
re-running everything.

## Optional: the expert panel

The seven passes work line by line. They will make a badly aimed argument read beautifully, because
none of them is allowed to ask whether the argument is the right one. `references/expert-panel.md`
is the mode that asks — a small bench of named practitioners, each applying a position they actually
published, to the copy as a whole.

One rule governs it: **nobody on the bench gets a view that cannot be traced to a named work, and
an ungroundable seat stays empty.** That file states it in full, with the reason it is worth the
cost. Use the mode for high-stakes copy — a page about to take paid traffic, a launch email, a
proposal. Skip it for a caption.

## Vocabulary and structural tells

`references/banned-vocabulary.md` is a standalone list: words that fail for a stated reason, and the
structural rhythms that make prose read as machine-written even when every individual word is fine.

It is also this plugin's fallback. `conversion-page-build` and `offer-architect` both route finished
work through a `humanizer` skill where one is installed, and both fall back to that file where one
is not. It is written to be usable cold, by someone who has never opened this skill.

Keep the boundary straight: that file governs **words and rhythm**. Whether the claim itself is
worth making, provable and specific belongs to the passes.

## What this skill does not do

- **It does not restructure.** If the section order is wrong or a section is missing entirely, that
  is `../conversion-page-build/SKILL.md`, and the edit pass should stop and say so.
- **It does not audit a live page.** Anything requiring the rendered page, the form, the traffic
  source or the analytics is `../conversion-page-audit/SKILL.md`.
- **It does not redesign the offer.** Copy that is weak because the thing being sold is weak cannot
  be edited into strength — `../offer-architect/SKILL.md`, and say so plainly rather than sweeping
  harder.

## How edits are delivered

Every proposed edit carries the defect it fixes and which pass found it. The author keeps the copy:
present the change and the reason, then let them take it, refuse it, or write their own version.
An edit with no stated reason is indistinguishable from a preference, and preferences get argued
about instead of applied.

Where a pass finds a defect that cannot be fixed from the copy alone — a claim with no available
proof, an objection with no answer, a guarantee the business has not agreed to — write
`NOT ESTABLISHED — <what would close it>` in place of an invented fix. This is the plugin-wide
discipline and its reasoning is stated once, in `../audience-research/SKILL.md`; it applies here
unchanged.

## Output

Edited copy plus a short change log — what changed, which pass caught it, and any item handed back
as a question rather than resolved. By vault convention the edited version sits beside the original
rather than replacing it, so the two can be compared; anywhere else, keep the original recoverable.
