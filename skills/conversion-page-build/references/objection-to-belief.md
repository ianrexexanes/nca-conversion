# Objection to belief

The Objections section — and every objection resolved earlier, in Mechanism or Proof, or later, in
FAQ — is built from a four-step chain, run once per objection in the brief's ranked Objections
section. Skipping straight from objection to answer is what produces the generic FAQ list this file
exists to prevent: an answer to the question actually asked, sitting next to the reader's real,
unstated hesitation.

## The chain

**1. Surface objection.** What the reader says, or what a salesperson hears, verbatim if you have
it — from the brief's Voice of customer section, sales call notes, or refund/decline reasons. Not
what you assume they'd say; what they actually said.

**2. Hidden objection.** The belief underneath the stated one. Almost every surface objection is a
proxy for something the reader would rather not say directly — often because saying it out loud
feels like admitting doubt about their own judgment, their team, or their budget authority.

**3. Belief shift.** The specific new belief that resolves the hidden objection, stated as a
sentence the reader could adopt — not a rebuttal of what they said, a replacement for what they
actually believe.

**4. Proof.** The concrete evidence that makes the belief shift credible rather than asserted. A
belief shift with no proof attached is just the seller's opinion restated more confidently, and a
skeptical reader treats it exactly that way.

Do all four before writing a word of the section. Writing the answer first and reasoning backward is
how a page ends up resolving the objection it wishes the reader had, rather than the one they
actually carry.

## Worked example

Using the fictional Lindero Systems brief from `../../audience-research/assets/conversion-brief-template.md`
— a B2B inventory-forecasting vendor selling into mid-market manufacturers. Lindero Systems doesn't
exist; this is the template's own example, reused here so the two files stay consistent rather than
introducing a second invented company.

**Objection 1 — "We tried a planning tool before and nobody used it."**

| Step | Content |
|---|---|
| Surface | "We tried a planning tool before and nobody used it." |
| Hidden | "Tools like this get bought with enthusiasm and abandoned within a quarter — I don't want to be the one who championed the next one." |
| Belief shift | "This one gets used because it sits inside the workflow the team already runs, instead of asking them to run a second one next to it." |
| Proof | A screenshot of the actual daily view the Operations Director's team would use, not a features list — per the brief's own Objections section, workflow proof is what resolves this one, not a features list. |

Note what the belief shift is *not*: it doesn't argue the previous tool was bad, and it doesn't
promise this team is more disciplined than the last one. It replaces the premise — this isn't a
second thing to run, it's inside the first thing — with something the workflow screenshot then has
to actually show.

**Objection 2 — "Our ERP is old / heavily customized, will this even connect?"**

| Step | Content |
|---|---|
| Surface | "Our ERP is old / heavily customized, will this even connect?" |
| Hidden | "If the integration doesn't work, I've spent political capital championing a purchase that breaks on contact with our actual systems, not a hypothetical clean one." |
| Belief shift | "This connects to your specific ERP version, and here's what happens if your customization falls outside that — a stated fallback, not silence." |
| Proof | Named ERP versions supported, plus the stated fallback for unsupported customizations — a fact, not a reassurance. |

This one shows the chain doesn't always need a dramatic belief shift — sometimes the hidden
objection is answered by a fact the page simply hadn't stated yet, and the "shift" is from
*unknown* to *known*, which is a real shift even though it isn't emotional.

**Objection 3, skipped on purpose — "This is Dana's job, are we replacing her?"** The brief itself
flags this one as never answered on the page directly: it's a sales-conversation objection, not a
page-copy one, and the page's only job regarding it is to avoid language that reads as
job-replacement. Not every objection in a ranked list gets the four-step chain run on it — some get
a deliberate no-treatment, and forcing this one through the chain anyway (inventing a belief shift
for "no, we're not replacing Dana") would put a sensitive internal-politics claim on a public page
where the brief itself says it doesn't belong.

**Objection 4 — Price, always last, per the brief's own ranking.**

Ranking matters here as much as the chain does. The brief notes price surfaces through the
Controller persona, not the Director who reads the top of the page — which means the belief shift
for price doesn't belong in the Hero-to-Mechanism run at all. It belongs where the Controller
persona actually reads: the pricing section or a forwarded page, addressed to a reader checking
total cost and integration risk, not to the reader the rest of the page is written for. Resolving a
low-ranked, differently-audienced objection in the same voice as the top-ranked one is a common
error the ranking step in the brief exists to prevent.

## Categorizing what's underneath

Hidden objections cluster into a handful of concerns, useful for noticing when a page has covered
every *surface* objection but left a whole category of *hidden* one untouched:

- **Whether it works at all** — the reader doubts the mechanism, independent of their own situation.
- **Whether it works for someone like them, specifically** — the reader believes the mechanism
  works in general but doubts their own situation is the one it was proven on. Of everything on this
  list, it's the one most often hiding behind a vague surface complaint, and it's what Mechanism and
  Proof exist to answer before Objections has to.
- **Whether the cost is justified by the outcome** — not "is it expensive" but "is it expensive
  relative to what I get," which is a Value stack problem wearing an Objections-section costume.
- **Whether adopting it costs more than the price** — time, retraining, internal politics, what it
  means for whoever currently owns the spreadsheet (Dana, in the Lindero example above). Effort &
  Sacrifice, not price.
- **Whether this is my decision to make** — the reader isn't objecting to the offer, they're
  objecting to being asked to decide something above their authority. No page copy resolves this;
  see the ranked-objection note above about routing it to the right reader instead.
- **What happens if I'm wrong** — this is what Guarantee exists to answer structurally rather than
  argue away in prose.

A page that resolves several objections from one cluster and none from another has a specific,
nameable gap — check the brief's ranked Objections section against these clusters before calling
the section finished, the same cross-check `conversion-page-audit`'s Objections check runs from the
other direction.

## Where each resolved objection actually lives

The chain doesn't only produce Objections-section copy. Once you know the hidden objection and the
proof that resolves it, place the resolution wherever it does the most good:

- A "whether it works for someone like me" objection is often better resolved inside **Mechanism**,
  before the reader has to raise it, than left for **Objections** to catch after the fact.
- A cost-justification objection restated in the brief's own words usually belongs in **Value
  stack**, as an itemized answer, not a defensive paragraph later.
- A "what if I'm wrong" objection is **Guarantee**'s job structurally, not a paragraph of reassurance
  competing with it.
- Whatever's left after all of that — real, but not load-bearing enough to interrupt the page's main
  argument — is **FAQ**.

An objection answered nowhere on the page — not in any of these four places — is a specific,
nameable gap, not a general "needs more trust signals" note.

## Voicing the shift by register

The chain itself doesn't change by register — every register still needs surface, hidden, shift and
proof identified before a word is written. What changes is how visibly the shift gets narrated on
the page:

- **Conservative B2B (DACH)** and **Technical / industrial** readers should never see the shift
  narrated back to them ("you might be thinking…"). The proof does the work; naming the reader's own
  doubt out loud reads as a technique being run on them, in a register where an unbackable claim
  discredits everything checkable beside it.
- **Consumer / lifestyle** and **Direct-response** readers can see the objection named directly and
  answered in the same breath — that directness reads as candor, not manipulation, in a register
  fluent in exactly this move.
- **Mission / nonprofit** sits closest to the first pair: name what a genuine participant or funder
  would ask, never in a tone that reads as defending the organisation.

See `section-playbooks.md`'s Objections row for the same guidance folded into the section as a
whole, and `../../audience-research/references/register-profiles.md` for the full reasoning behind
why the narration itself is the failure point in the first two registers.
