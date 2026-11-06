# Proof library

The Proof section — and every other section that leans on evidence rather than assertion — gets
built from what the client can actually produce, not from what would be nice to have. This file
ranks proof types by two things at once: how much a skeptical reader's disbelief it actually moves,
and what it costs to obtain. A weaker type you can get this week beats a stronger type that needs
three months of client cooperation you don't have, and knowing that trade-off up front is the point
of ranking on both axes instead of one.

Strength here means the same thing `register-profiles.md` means by it throughout: how hard the
artifact is to fake, and how directly it lets a reader check the claim without contacting anyone.
Cost means what obtaining it actually requires — client time, client data the client may not track,
a waiting period, or nothing beyond asking.

## The ranking

| Proof type | What it costs to obtain | Strength | Where it fails |
|---|---|---|---|
| **Named case study, method disclosed** | High — needs a real client relationship, their consent to be named, and a stated measurement method (what was measured, over what period, compared to what baseline). | Highest. A reader can check the person exists and ask them directly; the disclosed method means the number isn't just asserted. | If the method is never disclosed, this quietly degrades to the next tier down — a number with no way to verify it was measured fairly. |
| **Third-party certification, audit, or test-standard citation** | Moderate — usually already exists if the business is certified or audited; the cost is finding and citing it correctly, not producing it. | Very high in registers where it applies (Technical / industrial, Conservative B2B) — the certifying body, not the seller, is vouching. | Citing a standard incorrectly, or one that doesn't actually govern this category, reads as worse than citing none — see `../../audience-research/references/register-profiles.md`'s Technical / industrial Proof-requirements failure mode. |
| **Live or interactive demonstration** | Moderate to high — needs a working product state a stranger can actually use or watch, not a description of one. | High — the reader verifies the claim themselves in real time rather than trusting a report of it. | Only proves what it demonstrates; a demo of the easy path doesn't answer a doubt about the hard one, and claiming it does is the same substitution failure as an off-topic testimonial. |
| **Named testimonial with role and employer** | Low to moderate — needs one willing customer and their sign-off on the specific wording, but no data pipeline. | High in most registers, moderate in Technical / industrial, where a testimonial standing in a slot that wanted a spec reads as a substitution for missing data rather than as proof. | Missing the role or employer collapses this straight to the bottom tier — an unattributed quote reads as invented whether or not it is. |
| **Quantified outcome with a stated denominator** | Low to moderate — the number usually already exists internally; the work is disclosing the denominator and period alongside it rather than the number alone. | High — for instance, "40% of 200 clients" is checkable in a way "40% improvement" is not, and the missing-denominator version is one of the most common proof failures across every register. | A denominator that's technically true but not comparable to the reader's own situation (different starting point, different measurement window) is discovered eventually and read as concealment once it is. |
| **Founder or expert credential** | Low — usually already true, just needs stating with the specific, checkable claim rather than a vague title. | Moderate — raises trust fastest in registers where credentials outweigh outcome promises (Conservative B2B), does comparatively little in registers that trust reviews and photography instead (Consumer / lifestyle). | A credential stated vaguely ("industry expert") is functionally an adjective, not proof — it needs to be as checkable as any other artifact in this table. |
| **User-generated content (reviews, photos, unscripted video)** | Low — often already exists if the product has real users; the work is sourcing and attributing it, not producing it. | High specifically in Consumer / lifestyle, where it outperforms commissioned equivalents precisely because it looks less produced — worth testing on the client's own traffic rather than assuming, per that register's own Proof-requirements note. | Unsourced (no platform named) reads as invented, same as an unattributed testimonial — the source has to be named even when the content itself is real. |
| **Comparison or benchmark data against a named alternative** | Moderate to high — needs a comparison that's actually fair and current, which usually means someone ran it recently rather than reusing an old one. | High where it applies — this is the specific mechanism `register-profiles.md` names for a Technical / industrial reader "compared line by line" against a competitor's published datasheet. | Stale or cherry-picked comparisons are checkable, and getting caught having picked the flattering benchmark costs more than never having run the comparison. |
| **Mechanism walkthrough (showing exactly how the outcome was produced)** | Low to moderate — mostly a writing and disclosure task once the process itself exists; doesn't need a new client relationship. | High in Direct-response specifically, where it's named as the one proof form a competitor can't cheaply fabricate — elsewhere it does the Mechanism section's job more than the Proof section's. | A walkthrough vague enough to apply to any competitor's process isn't actually disclosing anything — it has to be specific enough that a reader could tell it apart from a generic explanation. |
| **Media mention or press citation** | Low if it already happened, otherwise high — you cannot manufacture a mention on a deadline. | Moderate — raises awareness-stage trust more than it resolves a specific doubt; rarely settles the reader's real, specific doubt on its own. | Ages badly if the mention is old enough that a reader can tell the coverage predates the current product, which reads as reaching. |
| **Bare adjective or unattributed claim ("industry-leading," "trusted by thousands")** | Effectively free. | Lowest — not proof, an assertion wearing proof's shape. Costs the claims sitting next to it, not just itself, once a reader notices one. | Everywhere. This is the default a page falls back to when the sections above weren't budgeted for, and it is worse than stating the gap honestly — see `NOT ESTABLISHED` in `../../audience-research/SKILL.md`. |

## Using the ranking

1. **Start from what the brief's Proof available section already lists**, not from this table cold —
   the brief scoped what's real and checkable for this specific client; this table is for deciding
   which of those real things to lead with, and what to ask the client for next if the strongest
   available type isn't there yet.
2. **A single unbackable claim discredits every checkable one beside it**, in every register, not
   only Conservative B2B where `register-profiles.md` states it most explicitly. When client-supplied
   proof doesn't clear the bar for the type it's being presented as, either move it down a tier to
   where it's honest, or write `NOT ESTABLISHED` and name what would close the gap — never present a
   weak type as though it were a strong one.
3. **Match strength to what the section is actually carrying.** Mechanism and Objections need proof
   that answers "will this work for someone like me" specifically — a walkthrough or a comparable
   case study does that; a media mention usually doesn't, however impressive the outlet.
4. **Enumerate before claiming a count.** If the page is going to say "50+ reviews" or show a wall of
   logos, count the real, current, de-duplicated set first — `conversion-page-audit`'s Proof check
   exists specifically to catch a partial count reported as a whole one, and a build-side page that
   ships an uncounted claim is handing the audit an easy finding.
5. **Check the register's own Proof-requirements dimension before finalizing the type**, not after —
   this table ranks proof types in general; `register-profiles.md` decides which of these general
   types actually counts as evidence for the specific reader this page is written to.

## Where proof goes

Where a piece of proof sits matters as much as which type it is. Every slot is filled from the brief.
An empty slot holds `[NEEDED: <what>]` and is reported, never filled with proof that was not supplied.

- **The hero's two slots.** `prooftop` and the proof strip, placed as "The two proof slots" in
  `../../hook-lab/references/hero-build.md` sets them out. `prooftop` is the first slot; the proof strip
  sits under the button and carries a second kind of proof.
- **Proof beside each button.** Every time the one action repeats, proof sits beside it, together with the
  doubt reducers, so the click is made with evidence in view.
- **Stacked proof.** In the Proof section and again in the closer, several kinds together (a rating,
  named clients, a case with its method) rather than one kind repeated.
- **A wall of testimonials below the fold.** Many voices, placed after the argument, for the visitor
  who scrolls down to see what other buyers said. It is the place for volume; the proof that matters
  most is already beside the buttons.
- **Verifiable, not decorative.** Proof a stranger can check outranks proof that only sits there: a
  full name, role and photo, or a platform badge the reader can follow to the platform itself. A
  testimonial missing those drops down the ranking above.
