# Auditing an offer that already exists

Most offer work starts with something somebody already assembled. This checklist runs the design
sequence backwards over it, so the redesign has a target instead of an opinion.

## No composite score

Do not produce a figure out of a hundred, and do not score ten dimensions out of ten and total them.
A composite averages one fatal defect against nine healthy dimensions and returns a number that
conceals which one is stopping the sale — which is precisely the thing the client is paying to find
out. It also invites a second audit later whose only visible output is that the number went up.

**Rank instead.** Name the binding constraint, then order everything else by what it costs. A client
can act on "this one thing, and here is what it costs to leave it" in a way they cannot act on 68/100.

## Sort findings by evidence status

Four buckets, in this order. This mirrors the discipline already used across this plugin — see
`../../conversion-page-audit/references/evidence-rules.md`, which governs what may be asserted about
an artefact you did not open.

- **Binding constraint** — the one finding whose resolution unblocks the most. One entry, not three.
- **Fix before launch** — real defects, ranked by cost of leaving them, each with the artefact it was
  checked against named.
- **Sound as built** — checked and found to be working. Only goes here if it was actually checked.
- **Could not check** — written as `NOT ESTABLISHED — <what it would take>`. This bucket is a
  finding, not an apology, and an audit with an empty one is usually an audit that guessed.

## The checks

### The four variables

- What does the buyer actually end up with, and is that the outcome belonging to the person who
  signs — or to somebody else in the room?
- Has the product changed recently in a way the promise never followed? If so, is this a copy gap or
  an offer gap? They cost differently and get confused constantly.
- What could a buyer verify himself, alone, in a few minutes, without contacting anyone? List the
  artefacts. If the answer is nothing, perceived likelihood is the constraint whatever else you find.
- What is the time from purchase to the *first* thing the buyer holds, separately from the time to
  the last? Is the first one stated anywhere the buyer will see it?
- What does this cost the buyer besides money, and is any part of that ask unquantified? An
  unquantified ask is priced by the buyer at its maximum.

### The stack

- Does it stack — can a reader add up the stated numbers and land near the price? Add them up and say
  what the arithmetic actually produces.
- Does every stated figure have a provenance a stranger could check: a real standalone price, a
  published comparable, or a documented avoided cost? Figures without one are findings.
- Which lines would this buyer pay for on their own, and which are the cost of being considered?
  Table-stakes inclusions are not defects, but they cannot carry price and should not be credited
  with doing so.
- Which lines are approved but unspecified, or promised but not yet deliverable? Check deliverability
  against a dated record rather than an intention — an inclusion nobody can ship is a liability from
  the day a buyer asks about it, not an asset.
- What left the stack recently, what was it justifying, and what is doing that job now?

### Risk reversal

- Does any exist? If not, what does the benchmark set publish, and is the silence therefore
  conspicuous?
- Does the trigger of any existing term still exist? A term pinned to a moment the offer no longer
  has is unenforceable, not merely weak.
- Does it answer the risk this offer actually creates — including any risk introduced by a recent
  change of format — or a generic one?
- Does it fire on a fact or on a judgement, and if the latter, who adjudicates?
- What does honouring it cost at a plausible invocation rate, not at zero?

### Price construction

- Is the anchor credible or does it read as pressure? Count the distinct scarcity and urgency devices
  visible in the price block at once. One is a mechanism; several is a signature.
- Is there a stated mechanism for why an early or discounted tier exists? Almost always missing,
  almost always cheap to add.
- Has any published scarcity number moved? A number that has moved in public is a number nobody
  believes, and it casts doubt on the ones that were always true.
- What justifies the price after the anchoring tier closes? Work out how much of the selling window
  runs with no comparison number visible.
- Is there a current cost model for the *present* shape of delivery? Without one the audit is
  structural only, and the report has to say so.

### Delivery and register

- Does the delivery model match what this buyer is actually constrained by, or was it chosen for
  margin?
- Are the offer's own instruments consistent with the register in the brief — the guarantee wording,
  the scarcity devices, the claim intensity? A single out-of-register device discredits what sits
  beside it.
- Where the offer and the register disagree, which is wrong? Occasionally the register call was made
  before the buyer was properly understood, and that is a finding about the brief.

## The two failures this checklist exists to catch

**Judging a change by its intent rather than by the buyer's default reading of it.** Whoever designed
a structural change knows why it is better and cannot un-know it. The buyer arrives with no such
knowledge and reads the change against every similar thing that has happened to them before. Run the
two-step argument in `value-equation.md` — default reading first, then what would change it and
whether that exists visibly at the moment of purchase — for every structural change, including the
ones everyone agrees are improvements.

**Reporting a strength that rests on something not yet deliverable.** The most attractive line in a
stack is frequently the one that has not shipped. Crediting it makes the audit wrong in the most
expensive direction, because the client acts on a strength they do not have. Verify against a dated
record before crediting, and where verification was not possible in this pass, say that rather than
inferring it from the fact that somebody meant to build it.

## Where the carried assumptions go

The rule itself is skill-wide: see the carried-assumption rule in `../SKILL.md`. An unconfirmed
thing the arithmetic rests on is recorded, never settled quietly in the convenient direction.

What an audit adds is **where it goes**. The assumption belongs in the report, dated, sitting next
to the finding it holds up — not in your working notes and not in a caveats paragraph at the end. An
audit whose arithmetic depends on an unstated reading is an audit nobody can check, including you,
three weeks later, and a reader who has to go looking for the caveat will finish the finding before
they reach it.
