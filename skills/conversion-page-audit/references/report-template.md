# Report template

*The governing rule: a finding may only appear under "Not a problem" if the check actually ran. If
it did not run, it belongs under "Could not check."*

That rule is the whole point of the shape below. Read `evidence-rules.md` before filling this in —
each section here is that file's discipline given a place to live, not a new set of rules. Delete
the bracketed instructions as you fill each section in; keep the four headers exactly as they
appear here; keep every entry inside the section its evidence actually earned it.

## Fix now

Ranked by expected impact, most impactful first — not by how easy the fix is. Every entry names the
element, the failure mode, the specific change, and the evidence it rests on: which rung
(`evidence-rules.md`'s hierarchy — rendered capture, fetched markup via `page_facts.py`, or a
Conversion Brief) and the date it was checked. Never claim a percentage lift for a specific fix — a
published case-study number does not transfer to this page. State expected direction and rank
relatively instead.

```
1. **[Element]** — [failure mode] → [specific change].
   Evidence: [rung + what was checked + date].
```

## Test, don't guess

Findings where the evidence does not justify asserting a direction — the honest answer is "probably
worth trying," not "do this." Every entry needs the hypothesis and the test that would settle it.
Check `test-design.md` before writing the test in: a "Test, don't guess" entry with no traffic
context attached is unfalsifiable, and at most SME traffic levels the test in your head may not be
runnable at all.

```
- **[Element]**: [why the direction is genuinely unclear, not just unconfirmed].
  Test: [hypothesis — because X, we believe Y will cause Z, measured by M].
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
