# Guarantees and risk reversal

Risk reversal is the mechanism: the buyer's downside gets smaller because the seller absorbs some of
it. A guarantee is one instrument for delivering that mechanism, and in several registers it is the
wrong one. Keeping the two words apart is the whole reason this file is not called "guarantees."

The question is never "should we add a guarantee." It is: **what specifically does this buyer stand
to lose, and which term of sale takes that particular loss off them at a cost the business can
actually carry?**

## Three tests every candidate term has to pass

Run these before writing any wording. A term that fails one of them is not a weaker guarantee — it is
a support ticket, a margin hole, or a line nobody reads.

**1. Is the trigger a fact or a judgement?** A term that fires on something observable — an
attendance record, a date passing, a delivery not shipping, a measured figure crossing a threshold —
settles itself. A term that fires on whether something was "good enough," whether the buyer "did the
work," or whether a document "counts" as complete needs someone to adjudicate it, and adjudication
between a customer and the person who took their money has no good outcomes. Where a term needs a
judgement, either replace the trigger with a fact or accept in writing that you are budgeting for
disputes.

**2. Does it answer *this* offer's risk, or a generic one?** The relevant risk is usually specific
and often recent. A format that spans a long window creates a risk that did not exist when the same
content was delivered in one block — *what if I do the first part and then my situation changes
before the second?* Nothing in a standard money-back clause answers that. A careful buyer will raise
it whether or not the page does, so the absence is not a marketing gap, it is a missing term of sale.

**3. What does honouring it cost, at what invocation rate?** Work the arithmetic at a plausible rate,
not at zero. A refund costs revenue. Open-ended continued work costs delivery capacity indefinitely
and has no ceiling. A deferred place in a later cohort costs capacity the business already controls
and is close to free. Terms that look equally generous on the page differ by an order of magnitude in
what they cost to keep, and that difference is usually the deciding factor.

## The trigger-existence check

**A term pinned to a moment the offer no longer has is not weakened. It is unenforceable.** When a
delivery format changes — a single event becomes two, a fixed programme becomes rolling, a milestone
moves — re-read every existing commitment and check that the moment it names still exists. This
sounds obvious and it is one of the most common defects in a real offer, because the format change
gets decided in one conversation and the terms of sale live in a different document nobody reopened.

The remedy is usually re-pointing rather than replacing. A promise that a buyer leaves with a
specific written artefact still works perfectly once it is re-pointed at a milestone that exists —
and it keeps whatever made it credible in the first place, which is normally a stated mechanism: the
artefact is produced in the room, in a scheduled block, with a named person present.

## The instruments, sorted by what risk they take off the buyer

Not a taxonomy of guarantee wording — a list of what the buyer's fear actually is and what removes
it. Corey Haines's `marketingskills` repo catalogues the same instruments by type and by business
model, in its `offers/references/guarantee-design.md`; this ordering is by the fear instead, because
that is the order the design decision actually happens in.

**"What if I go through this and get nowhere?"**
Return the money, either unconditionally or gated on something factual the buyer did. Unconditional
suits low prices and short deliberation. Gating suits anything where non-engagement is the likely
reason for failure — but keep the gate to one or two conditions that are observable, because a list
of five conditions reads as a refund made deliberately unreachable and costs more trust than the
term buys.

**"What if it isn't finished / doesn't arrive?"**
A service-level commitment: a named deliverable, by a named date, or a stated consequence. This is
the strongest instrument in registers that read commercial terms as competence, and it needs the
deliverable defined tightly enough to be unarguable.

**"What if it works but not far enough?"**
Continued work until a stated threshold. Powerful and dangerous: it has no natural ceiling unless one
is written in. Bound it by a number of sessions, a period, or a defined scope, or the term becomes an
open liability on the day one buyer decides to use it fully.

**"What if my circumstances change before I can use it?"**
Deferral and transfer rights: the place carries to the next delivery at no cost, or transfers to a
colleague. This is the instrument that most offers never consider and the one that most often fits.
It answers the specific risk created by long or split delivery, it fires on a fact, and in a
capacity-constrained delivery it costs the business capacity it already owns rather than revenue.

**"What if I commit and then find out it isn't for us?"**
A gated first stage — a paid pilot, a first milestone with an exit at the end of it, a first month
that decides the rest. Suits engagements where the real decision is whether to continue rather than
whether to start, which is most of B2B.

**"What if the invoice lands and there is nothing on record to show for it?"**
Payment contingent on a measured result. Only viable where the result is measurable, attributable to
you, and available on a timescale that does not wreck cash flow. Where any of those three is shaky,
this instrument creates the dispute it was meant to prevent.

**"Actually, none of the above."**
The stated absence. Some markets and some price points are better served by declining to offer
protection and saying why — the qualification process, the selection, the fact that this is not a
transactional purchase. It works only where proof is already strong and the buyer is experienced.
Where it doesn't fit, it reads as arrogance rather than as confidence, and there is no middle ground.

## The absence is a position, not a neutral

Before concluding that no risk reversal is needed, check what the benchmark set publishes. Where
competitors at a fraction of your price offer continued support with no time limit, or return the
money on request, an offer at the top of the market with nothing at all is not quiet — it is
conspicuous, and it is the first thing a comparison-shopping buyer notices.

Conversely: where a term was recently removed and nothing replaced it, say so explicitly in the
diagnosis. A removal is a change to the offer, and it will be read as one by anyone who saw the
earlier version.

## By register

Register decides the instrument and the vocabulary, not whether the mechanism is needed. Read only
the row the brief named.

| Register | What risk reversal looks like here | What the word *guarantee* costs |
|---|---|---|
| Conservative B2B (DACH) | A term of sale, stated plainly among the other terms: a named deliverable produced at a named point, plus a deferral or transfer right. Enforceable on facts, adjudication-free, and priced in capacity rather than revenue. | High. A loud refund promise at a serious price is a direct-response device, and this buyer audits claims rather than averaging them — one such device causes him to re-read the checkable claims beside it as marketing. Deliver the mechanism and avoid the word. |
| Technical / industrial | An acceptance test. Stated tolerances, a defined test the delivery has to pass, a warranty period with its scope written out, a documented remedy. Reads as normal commercial practice, because it is. | Moderate. Not offensive, but vaguer than this reader expects — an unspecified promise where a specification belongs invites the question of what is being left out. |
| Consumer / lifestyle | Short, unconditional, and stated in one sentence. The buyer will not read conditions and will assume the worst about any they notice. | Low. The word is expected and does its job. Conditions are what cost here, not the word. |
| Mission / nonprofit | Accountability rather than protection: what the money does, what gets reported back, how a participant or donor stops without friction or awkwardness. The risk being reversed is misuse and entanglement, not disappointment. | High in a different way. Commercial guarantee language misreads the relationship and can make a contribution feel like a transaction the reader did not intend. |
| Direct-response | The strongest instrument the margin will carry, stated prominently and early. Aggressive risk reversal is the market convention; a plain refund window fails to distinguish the offer from everything else the reader has seen this week. | None. This is the register the instrument was built for. The constraint here is arithmetic — model the invocation rate before promising, because the failures in this register are public. |

## Where the recommendation goes

Produce **one** recommendation with its reasoning, plus the strongest alternative you considered and
why you set it aside. Name what the recommended term costs to honour and what fact triggers it.

Then mark it as a recommendation. Risk reversal is a commercial term, the client holds the cost side
and the consequences, and the value of this analysis is that they can accept it, reject it, or ask
for the alternative — not that it arrives pre-decided. See the recommendation boundary in
`../SKILL.md`.
