# The refinement spec

Four decisions a wireframe leaves open, and that a designer will otherwise settle by taste. The
wireframe brief said what is on the page; this says which of it the reader actually registers, and
in what order.

`relume-brief.md` owns structure and content function and deliberately carries none of this. Writing
the two together produces a wireframe with emphasis already baked in, chosen before anyone had seen
the layout it would sit in.

## 1. Visual hierarchy — rank, never size

Per section, rank the elements: first, second, third. Write the rank.

**The moment you write `28px` you have taken a decision that belongs to the design system**, and
taken it without seeing the other twenty places that value is used. Rank survives a system change, a
rebrand and a platform migration. A number survives none of them and is wrong quietly.

Where a section has more than three ranks, it has more than three things, and that is a content
finding to hand back rather than a hierarchy to express. Four ranks means the fourth is invisible;
say so instead of specifying it.

## 2. Emphasis is a budget, not a property

Emphasis is relative, which means it is finite. One emphasised element in a section is emphasis.
Three is a section with no emphasis and more noise in it.

So set the budget explicitly: **how many emphasised elements the whole page gets, and which sections
spend them.** A page-level budget is what stops each section being individually reasonable and the
page collectively shouting.

**This is the one place register decides something in this skill.** What reads as confident in one
register reads as a fraud signal in another, and the register sets the ceiling on how much emphasis
the page can spend before it starts costing credibility instead of buying attention. Read the row
the Conversion Brief named, in `../../audience-research/references/register-profiles.md` — that one
row, not all five. `../SKILL.md` states why register is inherited rather than decided here.

## 3. Above-the-fold priority is a list, not a line

There is no fold. There is a different amount of visible area on every device, so "above the fold"
names a boundary that does not exist and hides the decision it is pretending to make.

Write instead: **what must be readable in the first screen at the narrowest viewport that matters
for this audience, in priority order** — and say where the "narrowest that matters" came from. If it
came from analytics, say so. If it came from an assumption, say that, and mark it
`NOT ESTABLISHED — <what would close it>`.

Then say what happens to items three and four when the viewport is taller, so a wide layout has
somewhere defined to put the extra room instead of enlarging what was already there.

The failure this prevents is specific and common: a hero designed on a wide desktop where five
things fit, shipped to an audience reading on phones where two do — and the two that survive were
never chosen.

## 4. Scan path — the order things register when nobody reads

Most readers do not read. State, per section and once for the page as a whole, the order in which
elements register: normally the heading, then whatever carries the most visual weight, then the next.

Then run the check, which is the most useful thing in this file:

> **Read only the scan path, in order, and see whether it still makes the argument.**

If the scan path alone does not state a claim, name a reader and ask for an action, the page works
for the minority who read every word and fails the majority who do not. The fix is which elements
carry weight — not more copy, which is what gets proposed and makes it worse.

## Worked example — a hero

```
Rank             1 headline · 2 primary button · 3 subhead · 4 proof strip
Emphasis         1 element: the button. The headline holds rank by position, not by treatment.
First screen     headline, button. Subhead if it fits in two lines at the narrow end.
(narrowest viewport that matters: from analytics — 360 px wide)
Scan path        headline → button → subhead
Reads as         <the claim> → <the action> → <who it is for>
Check            The path states a claim and an action but not who it is for, which is why the
                 subhead is ranked third rather than fourth. The proof strip is decoration at
                 rank 4 and is a candidate for removal.
```

The last line is what the check is for. It found a component that the brief could justify and the
scan path cannot, and the finding is available before anything is designed.

## What this spec never contains

No typeface, no hex value, no spacing unit, no breakpoint number, no grid column count, no shadow,
no corner radius. Those belong to a design system.

**The one number that does belong is not a design value.** A viewport width cited under decision 3
is a fact about the audience, sourced from analytics or marked as an assumption. It says who is
being designed for; it does not say where a layout should change. Those are different numbers and
only the first is this spec's to state.

Where there is no design system, that is a finding to report in the handoff — not a gap to fill from
taste. A spec that invents these values creates a one-page style, and the next page then contradicts
it, which is how a site ends up with four button treatments nobody chose.

## About the name on the door

Everything in this file is a set of decisions a person applies in whatever tool is open. Why the
file carries a tool's name at all, and why it asserts nothing about that tool, is stated once in
`../SKILL.md`.
