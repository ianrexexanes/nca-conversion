---
name: offer-architect
description: "Use when designing, packaging or pricing an offer — before any page exists. Covers Value Equation diagnosis, obstacle mapping, value stack, guarantees and risk reversal, price anchoring, and pitch formats. Also use when the user says 'design an offer', 'package this', 'what should I charge', 'pricing', 'guarantee', 'value stack', 'grand slam offer', or describes a service and asks how to sell it."
license: MIT
metadata:
  version: 0.3.0
---

# Offer architect

The offer is decided before the page. `conversion-page-build` writes an argument for whatever it is
handed; if what it is handed is weak, the result is fluent copy for a thing nobody wants. This skill
produces the thing.

## Read the brief first, if one exists

Look for `Conversion Brief — *.md` in your project's research folder. Three of its sections are inputs here rather
than things to re-decide: **Register**, the ranked **Objections**, and **Proof available**. Register
in particular is set once per client and inherited — see `../audience-research/SKILL.md`.

Without a brief you can still run, but say so in the output and mark every audience claim
`NOT ESTABLISHED — <what would close it>`. An offer designed against an assumed buyer is an offer
whose diagnosis nobody can check later.

## The recommendation boundary

**Commercial terms are the client's decision.** Price level, discounting, contract shape, refund
exposure and who carries risk are theirs to set — they hold the cost side, the cash position and the
consequences. This skill produces the analysis, then one recommendation with its reasoning, labelled
as a recommendation, so it can be accepted, rejected, or swapped for the alternative that was
considered and set aside.

Two rules follow, and both matter more than they look:

- **Never write a number into a deliverable as though it were settled.** A price that appears
  unqualified in a document gets quoted back as agreed. If a figure has to appear, say what it is —
  a recommendation, an illustration, or the client's own stated number.
- **Say what is not established, in the document.** A cost model you do not have is the difference
  between evaluating a price structurally and evaluating it commercially, and the second one is what
  the client thinks they're getting unless you say otherwise.

## Register is inherited, and it decides more here than it looks

The framework layer travels everywhere unchanged: every buyer needs the same things established about
an offer, and the steps below establish them in the same order whoever is reading. What varies is
which instruments are usable to establish them.

**A conservative B2B guarantee is not a direct-response guarantee.** They are not the same device at
two volumes — they are different instruments serving the same job. In `Direct-response`, an
aggressive risk reversal stated loudly is what a buyer expects and its absence is a differentiation
failure. In `Conservative B2B (DACH)`, that same construction is a fraud signal that discredits the
checkable claims sitting beside it, and the mechanism has to be delivered as a term of sale instead —
often without using the word *guarantee* at all. The same asymmetry runs through scarcity, price
anchoring, stack presentation and the pitch. Every reference file below carries a five-register table
where register changes the instrument; read only the row the brief named.

The five: `Conservative B2B (DACH)` · `Technical / industrial` · `Consumer / lifestyle` ·
`Mission / nonprofit` · `Direct-response`. Defined in
`../audience-research/references/register-profiles.md`.

## The sequence

Seven steps, in order. Each one's output is the next one's input, which is why the order holds.

1. **Diagnose before designing** — `references/value-equation.md`. Four variables, read as a
   diagnostic rather than a score. The output is the binding constraint: the one variable whose
   weakness is currently doing the most damage. Everything after this step aims at that variable.
2. **Map the obstacles** — same file. What actually stands between this buyer and the outcome,
   enumerated before anything is proposed. An obstacle nobody wrote down becomes an objection later.
3. **Turn every obstacle into something that removes it, then choose how that reaches the buyer** —
   `references/delivery-models.md`. The vehicle is a design decision, not a packaging one: one
   promise is three different offers at three different prices depending on whether the buyer does
   the work alone, does it under supervision, or has it done for them — and one of the three is wrong
   for this buyer.
4. **Build the stack, then price it** — `references/value-stack-and-bonuses.md`, then
   `references/pricing-and-anchoring.md`. Stack first. A price argued against a stack that doesn't
   add up is a price with nothing behind it.
5. **Design the risk reversal** — `references/guarantees-risk-reversal.md`. What happens if this
   doesn't work, stated in terms that can actually be honoured without arbitration.
6. **Name it and pick the angle** — `references/offer-angles.md`. An angle reframes; it does not
   change the offer. If a new angle appears to fix the problem, check that the problem was framing.
7. **Produce the pitch** — `references/pitch-formats.md`. Short, medium and long, each derived from
   the same load-bearing claim rather than written independently.

## Auditing an offer that already exists

Most real work starts here rather than at step 1. `references/offer-audit-checklist.md` runs the
whole sequence backwards over an offer someone already assembled, sorts what it finds by evidence
status, and names the binding constraint. Run it first when the offer exists; the redesign steps then
have somewhere specific to aim.

## What this produces

One document, `Offer — <Name>.md`, in your project's research folder, or wherever your project keeps
research. It carries: the four-variable diagnosis and which variable
binds, the obstacle-to-solution map, the stack with each line's value provenance, the delivery model
and why, the pricing analysis with its recommendation flagged as one, the risk-reversal
recommendation and the alternatives set aside, the name and angle, and the three pitch lengths.

The stack and risk-reversal sections are what `conversion-page-build` needs in front of it when it
writes a page's Value stack and Guarantee sections. Anything left vague here gets invented there, so
a stack line with no provenance and a guarantee with no trigger are not loose ends — they are defects
handed downstream.

## NOT ESTABLISHED, and the carried-assumption rule

Two halves of one discipline. Both are skill-wide policy: the reference files apply them and point
back here rather than restating them.

**A finding you cannot evidence is written `NOT ESTABLISHED — <what it would take>`**, never
softened into a hedge and never dropped. This is the same discipline `audience-research` uses and
the same reason: a stated gap gets closed, and a quiet one gets discovered by the client.

**An unconfirmed thing the arithmetic rests on is carried, not resolved.** When an offer's numbers
depend on something nobody has actually confirmed — how many places genuinely exist, whether a
stated total is per person or for the group, whether a term was agreed or merely discussed — write
the assumption down alongside what changes if it turns out the other way, then carry on. Tax
treatment and collection timing are the two that bite most often; both are carried in
`references/pricing-and-anchoring.md`. What this forbids is settling the ambiguity silently in
whichever direction supports the conclusion you were heading for, and then building three sections
on top of it. That failure is invisible in the finished document, which is exactly why the
assumption has to be on the page rather than in your head.
