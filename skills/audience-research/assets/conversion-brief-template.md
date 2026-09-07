# Conversion Brief template

This is the artifact `audience-research` writes and every downstream skill reads. Copy it, fill
every section, and treat gaps as findings rather than as formatting to clean up before delivery.

> **A section that cannot be filled is written as `NOT ESTABLISHED — <what it would take>`, never
> deleted.** Deleting an empty section hides the gap. The brief exists to record what is known and
> what is not; a missing section reads as "not researched," while `NOT ESTABLISHED` reads as
> "researched, and here is the specific unanswered question." The second is the one that gets
> unblocked. Write it even when the answer is boring — "NOT ESTABLISHED — client has not shared
> churn data; would need a CRM export."

The filled example below runs through all ten sections as one coherent brief for a single
fictional company, **Lindero Systems**, a fictional B2B inventory-forecasting software vendor
selling into mid-market manufacturers. Lindero Systems does not exist. Replace every line of the
example with your own client's material — nothing in this file is real research.

The brief carries its own frontmatter when filled. It is not this file's frontmatter — this file
is a template being read, not a brief being written — so the shape is shown as a fenced block:

```yaml
---
type: note
author: <researcher>
project: <client / project name>
date: <YYYY-MM-DD>
register: <one of the five archetypes — see Register section below>
tags: [conversion-brief, audience-research]
---
```

---

## ICP

**Establishes:** the company profile the offer is built for — size, sector, buying structure, and
the trigger that puts them in-market. Not a persona; personas are the people inside this company.

**Failure mode of leaving it thin:** every downstream skill inherits whatever ICP is here without
re-checking it. A vague ICP ("mid-sized companies that need better software") lets offer design and
page copy each quietly narrow it differently, and the page ends up arguing to no one in particular.

**Filled example — Lindero Systems:**
Manufacturers running discrete or batch production, 80–400 employees, on-premise or hybrid ERP
(SAP Business One, NetSuite, or a spreadsheet-plus-ERP hybrid), no dedicated demand planner on
staff. In-market trigger is a stockout or overstock event bad enough that it reached a director's
desk — not a routine software refresh. Company is past the stage where a spreadsheet was tenable
but has not yet budgeted for an enterprise planning suite.

## Personas

**Establishes:** who inside the ICP actually reads the page, in what role, and who else has to
sign off. A committee sale needs every seat in the room named, not just the champion.

**Failure mode of leaving it thin:** a page written for the champion alone stalls in procurement,
because nobody wrote anything the approver needed. This is the single most common cause of a page
that reads well and converts at zero on a considered purchase.

**Filled example — Lindero Systems:**
Primary — Operations Director, mid-40s, owns the P&L line the stockout hit, technically literate
but not a planner, evaluates on "will this actually get used" more than feature count. Secondary
— Controller or CFO, signs the check, reads for total cost and integration risk, never sees the
top of the page, goes straight to pricing and the security page. Tertiary — whoever currently
runs the spreadsheet, usually a supply chain coordinator, quietly threatened by the purchase and
capable of talking the Director out of it if the tool looks like it replaces rather than assists.

## Problems, ranked

**Establishes:** the ICP's problems in the order they actually decide the purchase, not the order
a features list would present them. Ranking is the point — an unranked list lets the page argue
its favorite problem instead of the reader's.

**Failure mode of leaving it thin:** copy built off an unranked list over-indexes on whichever
problem is easiest to write about, which is rarely the one that closes the sale.

**Filled example — Lindero Systems:**
1. Stockouts on top-selling SKUs during demand spikes — direct revenue loss, the trigger event.
2. Overstock tying up working capital on slow movers — CFO's problem, surfaces in the budget
   conversation even when it didn't trigger the search.
3. Planning currently lives in one person's spreadsheet — a bus-factor risk nobody names out loud
   until asked directly.
4. Manual reconciliation between the spreadsheet and the ERP eats a day a week — real but never
   the reason anyone searches; only surfaces once they're already evaluating.

## Voice of customer

**Establishes:** the actual words the ICP uses for their own problem, pulled from reviews, sales
call notes, support tickets, or forums — not the vendor's internal terminology translated into
what sounds like customer language.

**Failure mode of leaving it thin:** copy written in vendor vocabulary reads as accurate and
converts as foreign; the reader recognizes the problem but not the words, and recognition is what
makes a headline stop a scroll.

**Filled example — Lindero Systems:**
From sales call notes: "we keep guessing and getting it wrong," "it's all in Dana's head," "we
either run out or we're drowning in it." From a G2-style review of a competitor: "finally stopped
finding out about a stockout from an angry customer." Note the recurring frame — reactive
discovery ("finding out"), not proactive planning — which the vendor's own internal language
("demand forecasting accuracy") never uses.

## Competitive landscape

**Establishes:** who the ICP actually compares this offer against, including "do nothing" and
"keep the spreadsheet," which are real competitors and usually the strongest one.

**Failure mode of leaving it thin:** a competitive section that only names other named vendors
misses the comparison that actually happens in the buyer's head, and differentiation built against
the wrong competitor argues a point nobody was contesting.

**Filled example — Lindero Systems:**
Named competitors: two enterprise planning suites (too expensive, too slow to implement for this
ICP — 6+ month rollouts) and one direct competitor at a similar price point (weaker ERP
integration, per sales team's win/loss notes). Unnamed competitor, and the real one: the existing
spreadsheet, which costs nothing incremental and requires no committee approval. Any page that
doesn't out-argue "just keep doing what we're doing" loses regardless of how it stacks against the
named vendors.

## Differentiation

**Establishes:** the specific, defensible reason to choose this offer over the alternatives named
above — mechanism, not adjective. What does it actually do differently, and can the claim survive
a reader who checks it.

**Failure mode of leaving it thin:** differentiation stated as a quality ("more accurate," "easier
to use") rather than a mechanism is unfalsifiable and every competitor claims the same adjective,
so it persuades nobody and gives an auditor nothing to verify.

**Filled example — Lindero Systems:**
Native two-way sync with the three ERPs that cover 70% of this ICP (per the ICP section) with no
middleware layer — the named competitor requires a separate integration tool, which is the actual
source of its longer, more expensive rollouts. Mechanism: forecasts recompute directly against ERP
inventory movements rather than a nightly batch export, so the Director sees a stockout risk the
same day the sell-through spikes rather than the next morning.

## Objections

**Establishes:** the specific reasons this ICP does not buy, ranked, each paired with what would
actually resolve it — not a generic FAQ list assembled after the copy is written.

**Failure mode of leaving it thin:** an objections section that lists surface questions ("how much
does it cost") misses the load-bearing one underneath ("will my team actually use this instead of
the spreadsheet"), and a page can answer every listed objection and still fail on the real one.

**Filled example — Lindero Systems:**
1. "We tried a planning tool before and nobody used it" — resolved by workflow proof (screenshots
   of the actual daily view), not a features list.
2. "Our ERP is old / heavily customized, will this even connect" — resolved by naming the specific
   ERP versions supported and a stated fallback for unsupported customizations.
3. "This is Dana's job, are we replacing her" — never answered on the page directly; this is a
   sales-conversation objection, and the page should avoid language that reads as job-replacement.
4. Price, always last — this ICP does not lead with budget, per sales notes; the Controller
   persona raises it, not the Director.

## Proof available

**Establishes:** what evidence the client can actually produce today — named customers, numbers
with a source, case studies, certifications — scoped to what is real and checkable, per the
register's proof requirements.

**Failure mode of leaving it thin:** a proof section padded with claims the client cannot back
sets up page copy that fails the moment a reader checks it, and per the register rules a single
unbackable claim discredits every checkable one beside it.

**Filled example — Lindero Systems:**
Available: three named reference customers willing to be quoted with role and company (Operations
Director titles, matches the persona), one before/after stockout-rate case study with a stated
measurement period. Not available: no third-party audited results, no published benchmark against
the named competitor. `NOT ESTABLISHED — client has not confirmed whether the case study's
stockout-rate figure was measured the same way before and after; would need the underlying method
from their analytics team before it can be published as a comparable number.`

## Register

**Establishes:** which of the five archetypes this brief commits to, chosen once here and
inherited unchanged by every downstream skill. See `../references/register-profiles.md` for the
full profiles, their failure modes, and the "Signals it's the right pick" test for each.

The five, byte-exact: `Conservative B2B (DACH)`, `Technical / industrial`, `Consumer / lifestyle`,
`Mission / nonprofit`, `Direct-response`.

**Failure mode of leaving it thin:** an unset or vaguely stated register lets each downstream skill
pick its own, which produces a page that is internally inconsistent — per the register profiles,
a page written in two registers cannot be defended at all, where a page written entirely in the
wrong one at least can be.

**Filled example — Lindero Systems:**
`Technical / industrial`. Signals matched: the buyer (Operations Director) personally answers for
the choice, the sale runs through ERP compatibility checks that function like a qualification
process, and the Controller and Director are different people asking different questions. Not
`Conservative B2B (DACH)` — sales cycle is weeks, not the months that register assumes, and there
is no formal-address language market in play (US/English-speaking ICP). Not `Direct-response` —
the Controller persona has to approve the spend, which the register profile calls a disqualifying
test on its own.

## Open and unconfirmed

**Establishes:** every question raised in the sections above that is not yet answered, in one
place, so a reader does not have to re-scan the whole brief to find every `NOT ESTABLISHED` line.

**Failure mode of leaving it thin:** open items scattered only inline get missed by whoever picks
up the brief next; a single consolidated list is what actually gets closed before the page ships.

**Filled example — Lindero Systems:**
- Case study measurement method for the before/after stockout figure (see Proof available).
- Whether the Controller persona ever visits the page directly or only sees a forwarded PDF —
  changes whether the pricing page needs to stand alone.
- No confirmed data on how much of the ICP is on NetSuite versus SAP Business One versus a
  spreadsheet hybrid; differentiation claim in this brief assumes the sales team's estimate is
  representative and has not been checked against a larger sample.
