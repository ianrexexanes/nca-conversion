# Report template

*The governing rule: a finding may only appear under "Not a problem" if the check actually ran. If
it did not run, it belongs under "Could not check."*

That rule is the whole point of the shape below. Read `evidence-rules.md` before filling this in —
each section here is that file's discipline given a place to live, not a new set of rules. Delete
the bracketed instructions as you fill each section in; keep the four headers exactly as they
appear here; keep every entry inside the section its evidence actually earned it.

**Frontmatter.** The internal report starts with this block, filled in with the audited address and the date of the audit. The client version has no frontmatter.

```
---
type: audit
page: <the audited URL>
date: <YYYY-MM-DD>
---
```

## Conversion Score

[Scored audits only, run by `/cro audit`. An unscored audit leaves out this block and the Search check block.]

[The coverage line from score.py, word for word.]

**Mode:** [Search (keyword: <keyword>) / Direct] · **Page role:** [homepage / service / landing] · **Traffic:** [cold outreach / ads / search / mixed / unknown] · **Register:** [archetype]

| Factor | Score | What was seen |
| --- | --- | --- |
| 1. What's in it for me? | [0 to 10, or not checked] | [evidence, or what blocked the check] |
| 2. Is it for me? | [0 to 10, or not checked] | [evidence, or what blocked the check] |
| 3. Does it work? | [0 to 10, or not checked] | [evidence, or what blocked the check] |
| 4. What do I do next? | [0 to 10, or not checked] | [evidence, or what blocked the check] |
| 5. Value and how it works | [0 to 10, or not checked] | [evidence, or what blocked the check] |
| 6. Proof and trust further down the page | [0 to 10, or not checked] | [evidence, or what blocked the check] |
| 7. Objections and risk | [0 to 10, or not checked] | [evidence, or what blocked the check] |
| 8. The form and what happens after it | [0 to 10, or not checked] | [evidence, or what blocked the check] |
| 9. Design that sells | [0 to 10, or not checked] | [evidence, or what blocked the check] |
| 10. Mobile and speed, measured | [0 to 10, or not checked] | [evidence, or what blocked the check] |

## Search check

[Search pages only; leave this section out on a Direct page.]

**Keyword:** [keyword] · **Variants:** [variants, or "none"] · **Confirmed:** [yes / no]

| Placement | Status | What the page has |
| --- | --- | --- |
| Title | [found / missing / not applicable] | [text] |

[one row per placement, in this order: Title, Meta description, URL, H1, First sentence, H2]

**Headings:** H2 [exact] exact and [variant] variant of [total]; H3 [...]; H4 [...]

**Body:** [exact] exact and [variant] variant uses

## Fix now

Order these by how much each one is likely to move the outcome, biggest first — not by which one is
quickest to ship. Every entry names what's currently wrong, what to do about it, and the evidence
underneath that recommendation: which rung (`evidence-rules.md`'s hierarchy — rendered capture,
fetched markup via `page_facts.py`, or a Conversion Brief) and the date it was checked. Resist attaching a
specific percentage to any one fix's expected effect — a lift measured on someone else's page
belongs to that page, not this one, so borrowing the number is a promise this audit can't actually
back up. Say which direction the metric should move and let the item's position in the list carry
how much it matters.

```
1. **[What to change]**, on [the element it affects].
   Why it's ranked here: [expected impact relative to the other items below].
   Basis: [rung + what was checked + date].
```

## Test, don't guess

Findings where the evidence does not justify asserting a direction — the honest answer is "probably
worth trying," not "do this." Every entry needs the hypothesis and the test that would settle it.
Check `test-design.md` before writing the test in: a "Test, don't guess" entry with no traffic
context attached is unfalsifiable, and at most SME traffic levels the test in your head may not be
runnable at all.

```
- **[Element]**: [why the direction is genuinely unclear, not just unconfirmed].
  Test: [the hypothesis, in the five-part shape `test-design.md` defines].
  Feasible at this page's traffic? [yes/no, and why].
```

## Not a problem

Checked, and found sound. Name what was checked and how, so the same item does not get re-raised
next audit by someone who assumes it was never looked at. If you cannot name what was checked, the
finding does not belong here — move it to "Could not check," even if you privately suspect it is
fine. A suspicion is not a check.

```
- **[Element]**: checked via [rung + method], found [why it holds up].
```

## Could not check

Blocked, and why, and what would unblock it. This section is not padding and it is not an apology —
`evidence-rules.md`'s closing note calls it the most actionable part of the report, because each
entry converts directly into a request: a credential, a permission, or ten minutes with someone who
holds one. An entry written as "unable to verify" converts into nothing; write what you needed,
what specifically stopped you, and what would fix that.

```
- **[What you were trying to determine]**: blocked by [no rendered capture: `render_check.py` could not run (run `/cro setup`) / no admin
  access / consent could not be given / a cache could not be purged / behind authentication / other].
  Unblocked by: [the specific thing that would let this be checked].
```
