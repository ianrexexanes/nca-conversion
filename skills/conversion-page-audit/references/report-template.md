# Report template

*The governing rule: a finding may only appear under "Not a problem" if the check actually ran. If
it did not run, it belongs under "Could not check."*

That rule is the whole point of the shape below. Read `evidence-rules.md` before filling this in —
each section here is that file's discipline given a place to live, not a new set of rules. Delete
the bracketed instructions as you fill each section in; keep the four headers exactly as they
appear here; keep every entry inside the section its evidence actually earned it.

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
- **[What you were trying to determine]**: blocked by [no Playwright MCP available / no admin
  access / consent could not be given / a cache could not be purged / behind authentication / other].
  Unblocked by: [the specific thing that would let this be checked].
```
