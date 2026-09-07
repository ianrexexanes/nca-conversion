# The seven passes

One defect class per pass. Each section below gives what the pass hunts, the boundary on what it is
allowed to change, one before/after, and the register note — because several of these passes run in
opposite directions depending on who is reading.

Two things hold across all seven and are not restated in each:

- **The argument is the author's.** A pass changes how a claim lands, never what is being claimed.
  Where an edit would alter the substance, it comes back as a question instead of an edit.
- **Every change carries its reason.** See `../SKILL.md`.

Register names are `Conservative B2B (DACH)`, `Technical / industrial`, `Consumer / lifestyle`,
`Mission / nonprofit`, `Direct-response`, defined in
`../../audience-research/references/register-profiles.md`.

---

### Pass 1 — Clarity

**Hunts:** sentences that survive two readings with two different meanings. Pronouns whose referent
sits three sentences back or nowhere. Terms used before the reader has been given them. A point that
arrives only after its own qualifications have been disposed of. Two arguments sharing one sentence.

**May change:** word order, sentence boundaries, where a qualification sits, whether a term gets
introduced. **May not change:** which qualifications exist. Deleting a caveat because it slows the
sentence down is how an editor converts an accurate claim into an overstated one.

Before: *Following the onboarding session, which most teams complete within the first fortnight
subject to scheduling, access to the reporting layer is provisioned.*
After: *Your reporting access is switched on at the end of the onboarding session. Most teams book
that session in their first two weeks.*

**Register note.** What counts as unclear moves. In `Technical / industrial` a long clause-heavy
sentence is not a defect if every clause carries a condition or a tolerance — the fix there is
usually to lift the conditions into a table, not to shorten the prose, and a spec broken into short
sentences reads as data that went missing. In `Consumer / lifestyle` the opposite: a sentence can be
grammatically unambiguous and still fail this pass, because an abstraction the reader cannot picture
has not been understood in any useful sense. In `Mission / nonprofit` the recurring clarity defect
is the agentless sentence — support is provided, needs are met — where the reader cannot tell who
did anything.

---

### Pass 2 — Voice

**Hunts:** more than one person apparently writing. The drift from *we* to *the organisation* and
back. Second person that appears in the opening and vanishes by the third section. A joke in a
document that is otherwise straight. Vocabulary borrowed from a different register — one
direct-response line in a formal document does more damage than the whole document being informal.

**May change:** person, address, formality, word choice. **May not change:** the register itself.
Register is set once per client in the brief and inherited; if the copy is consistently in a
register the brief did not name, that is a finding to raise, not a thing to quietly correct across
forty paragraphs.

Before: *We're thrilled to partner with you. The organisation subsequently conducts a requirements
assessment prior to implementation.*
After: *We start by working out what you actually need, then we build it.*

**Register note.** The defect is drift, but the direction that matters differs. In
`Conservative B2B (DACH)` watch for drift toward warmth and informal address — consistent formal
address is load-bearing there, and a single slip into casual reads as carelessness about the whole
document. In `Consumer / lifestyle` watch for the reverse: a paragraph that turns corporate mid-page
kills whatever mood the surrounding copy had built. In `Direct-response` the failure is borrowed
cadence — the rhythm of a famous marketer reproduced without the numbers underneath, which reads as
imitation rather than as an operator describing his own business. In `Mission / nonprofit` the drift
to catch is into institutional passive, which reads as an organisation shielding itself.

---

### Pass 3 — So What

**Hunts:** a capability stated with its consequence left off. A fact about the seller where a
consequence for the reader was needed. Company milestones — funding, headcount, anniversaries —
occupying space that has to argue for a purchase. The test is blunt: read the sentence, then ask
what follows for the person reading it. If nothing does, the sentence is decoration.

**May change:** adding the consequence, cutting the sentence, or moving it somewhere it is
load-bearing. **May not change:** inventing the consequence. If nobody can say what follows from a
feature, that is a finding about the offer, not a gap for the editor to fill.

Before: *Built on a distributed architecture with regional failover.*
After: *Built on a distributed architecture with regional failover, so a single data-centre outage
does not take your checkout offline.*

**Register note.** The answer to "so what" is a different kind of statement per register. In
`Technical / industrial` it is a specification consequence — what the tolerance means for his
installation, what the standard means for his approval process — and a warm benefit sentence bolted
onto a spec reads as marketing in a slot that wanted data. In `Mission / nonprofit` the answer is
what the organisation contributed, attributed honestly, rather than what the reader will feel about
it. In `Consumer / lifestyle` the answer is what the reader will be doing, and when. In
`Conservative B2B (DACH)` it is frequently what this lets the reader tell his own colleagues, which
is the purchase he is actually making.

---

### Pass 4 — Prove It

**Hunts:** load-bearing claims with nothing a reader could inspect. Superlatives with no way to
settle them. Numbers with no denominator, no period, and no method. Proof present but scoped to a
different product than the one the page is selling — an artifact that looks supportive and works
against the page the moment its scope is noticed.

**May change:** attaching proof that already exists elsewhere in the copy or the brief, moving proof
next to the claim it supports, or lowering a claim to the level the available evidence carries.
**May not change:** the evidence itself. An editor does not supply testimonials.

Which proof types are worth what, and what each costs to obtain, is
`../../conversion-page-build/references/proof-library.md` — this pass does not re-rank them, it
finds the claims that have none.

Before: *Trusted by thousands of leading companies.*
After: *Used by 2,400 companies, including [named three the client has cleared for use].* Where none
are cleared: `NOT ESTABLISHED — needs three logo permissions or the claim comes out.`

**Register note.** The register decides what to do when the proof is simply absent. In
`Conservative B2B (DACH)` the move is to say so — a stated absence is credible to that reader and a
disguised one is not, and the contamination cost of one unbackable claim sitting among checkable
ones is set out in that register's Claim-intensity failure mode, which is worth reading before
deciding to leave the claim in. In `Consumer / lifestyle` a written disclaimer reads as an odd legal
artifact;
the move is to replace the unprovable claim with a specific image, since specificity is doing the
persuading there anyway. In `Direct-response` a weak proof asset is worse than none, because that
audience has more practice than any other at spotting fabricated proof.

---

### Pass 5 — Specificity

**Hunts:** adjectives standing where a measurement belongs. Quantities the reader cannot picture —
*many*, *significant*, *a range of*. Claims that would survive unchanged on a competitor's page.
Round numbers with no source. Outcomes with no interval attached.

**May change:** replacing a vague word with the figure the client has already stated somewhere,
cutting a sentence that cannot be made specific, or flagging the gap. **May not change:** producing
a number. A figure invented at the editing stage is a fabrication with an editor's fingerprints on
it, and it will be quoted back as agreed.

Before: *Significantly reduces reporting time.*
After: *Cuts month-end reporting from three days to about four hours.* Where the client has never
measured it: `NOT ESTABLISHED — needs the before figure; claim comes down to "reduces" until then.`

**Register note.** Specificity means four different things. In `Direct-response` it is arithmetic
said out loud — the input, the output, the interval — and the register's characteristic failure is
copying the volume while dropping the maths. In `Technical / industrial` it is the operating
condition attached to the figure; an unqualified performance number invites the reader to assume the
worst case and disbelieve the page. In `Consumer / lifestyle` it is a sensory image rather than a
number, and a number can even weaken it. In `Mission / nonprofit` it is attribution and a
denominator, and this is the register where over-specifying is the most damaging available error,
because funders, partners and the community served are both the audience and the people
positioned to check the figure, and they lose more than the figure when it does not hold.

---

### Pass 6 — Heightened Emotion

**Hunts:** copy that states a situation the reader lives inside and generates nothing. Pain
described from outside it, in words the seller would use and the reader would not. Aspiration asserted
as a noun — *peace of mind*, *confidence* — where an actual scene would do the work.

**May change:** the concreteness of a described situation, whose words it is described in, and how
much hedging sits on it. **May not change:** the intensity ceiling the register sets. This pass is
where an editor most often does real damage, by adding force a register cannot carry.

Before: *Our solution provides peace of mind for finance teams.*
After (`Direct-response`): *You stop finding out about the overspend in the following month's
close.*
After (`Conservative B2B (DACH)`): *The overspend appears in the current period, not at the next
close.* Same fact, no adjectives added, the hedge removed.

**Register note.** This is the pass whose direction reverses most sharply. In
`Conservative B2B (DACH)` it is a **subtraction pass**: it adds no adjectives and no imagery, it
strips the hedges — *can help*, *is designed to*, *may allow* — that leave the reader unable to tell
whether anything is being claimed at all. Feeling in that register comes from an accurate statement
of his own situation, and each hedge removes some of it. In `Direct-response` the pass genuinely
adds, and its own limit is the arithmetic: force applied to a number the business cannot defend is
the worst combination available. In `Mission / nonprofit` the pass is capped by dignity before it is
capped by taste — heightening by describing a beneficiary's condition more vividly is the one move
that is off the table regardless of how well it converts. In `Technical / industrial` the pass
mostly does not run; emotional texture in a specification slot reads as an absence of data.

---

### Pass 7 — Zero Risk

**Hunts:** everything left unresolved at the moment of the ask. What happens after the click, stated
nowhere. An objection raised earlier in the copy and never answered. A commitment implied but not
named — how long, how much, who is on the call. Fine print that introduces a doubt the body copy had
already closed.

**May change:** stating what already exists — the actual next step, an existing trial, a term the
client has already agreed. **May not change:** offering a guarantee, a refund, a trial or a price
that nobody has approved. That is the single most expensive edit available in this skill.

The instruments themselves — which risk-reversal device fits which buyer, and what the word
*guarantee* costs in each register — are
`../../offer-architect/references/guarantees-risk-reversal.md`. This pass locates the unresolved
risk; that file decides what to do about it.

Before: *Get started today.*
After: *Book a 30-minute call. You will speak to the engineer who would run the project, and you
will leave with a written scope whether or not you go ahead.*

**Register note.** The risk being carried is different per reader. In `Conservative B2B (DACH)` it
is career risk — the buyer is choosing what he will have to defend internally — so the effective
move is describing exactly what happens next, and a loud money-back guarantee makes it worse by
reading as a fraud signal beside the checkable claims. In `Direct-response` an explicit risk
reversal is expected, and its absence is itself the unresolved risk. In `Consumer / lifestyle` the
risk is usually disappointment rather than money, and it is closed with reviews and honest
photography near the ask. In `Mission / nonprofit` it is where the money goes, closed with the
programme-to-administration split rather than with any reassurance.

---

## The regression rule

The passes are ordered so each hands the next a cleaner input, but three later passes predictably
damage specific earlier ones. Re-check those three pairs. Do not re-run all seven passes after every
edit — a full re-sweep after each change costs more attention than it returns and tends to produce
drift rather than correction.

| After running | Re-check | Because |
|---|---|---|
| Heightened Emotion (6) | Prove It (4) | Force is added by raising the claim, and a claim raised past its evidence is the defect pass 4 exists to catch. Anything sharpened in pass 6 needs its artifact checked again. |
| Specificity (5) | Clarity (1) | Numbers, units, periods and denominators arrive as extra clauses. A sentence made precise in pass 5 is frequently a sentence that can no longer be read in one go. |
| Zero Risk (7) | Voice (2) | Terms, conditions and next-step detail import a contractual register. A page that has been made safe often stops sounding like whoever wrote the first six sections. |

One more, less predictable and worth a look on longer copy: pass 3 removes company-facing sentences,
which can leave a section with a weak opening it did not have before. Read the first sentence of
each section once at the end.

## When to stop

Stop when a full pass produces no change. Two practical limits sit before that:

- **A pass that keeps finding the same defect is reporting an upstream problem.** Six claims with no
  proof is not six editing findings; it is one finding about the brief's Proof-available section.
  Say that once rather than writing six `NOT ESTABLISHED` lines.
- **Copy that needs every pass to fire heavily is usually copy that should be rewritten.** Editing
  preserves an argument. If the argument is not there, hand it to
  `../../conversion-page-build/SKILL.md` and say why — that is a faster and more honest answer than
  seven passes of repair.
