---
name: hook-lab
description: "Use when writing hooks, headlines, hero lines, subject lines, ad hooks or CTA copy, including quick one-off variant requests. Crosses eight hook types (outcome, time, effort, callout, contrarian, pain, mechanism, transformation) with register. Also use when the user says 'give me headlines', 'hook ideas', 'hero line', 'subject line', 'CTA copy', 'punchier headline', or asks for variants of a line."
license: MIT
metadata:
  version: 0.3.0
---

# Hook lab

The shortest unit of persuasion in this plugin, and the one with the worst failure characteristics.
At eight words a wrong choice has nowhere to hide: there is no second sentence to qualify it, no
proof block underneath it, and no paragraph in which the reader forgives it. A page in the wrong
register can still be read. A hook in the wrong register is simply not read.

## No Conversion Brief, no gate

`conversion-page-build` stops and sends you to `../audience-research/SKILL.md` when no brief exists,
and it is right to: a whole page argued at an assumed buyer is a week of work aimed at nobody. This
skill deliberately does not do that. Someone asking for three subject-line variants is not asking to
commission a research document, and requiring one before answering would retire the skill from the
request it exists for. `../copy-sweeps/SKILL.md` refuses the same gate for a related reason; the
habits that replace the brief are different there, because improving a claim someone else made and
inventing one from nothing are different acts.

**Read the brief when there is one.** That is
`Conversion Brief — *.md` in your project's research folder; elsewhere, whichever folder holds the
research. Three lines of it matter here: the **Register**, the ranked **Problems**, and the
**voice-of-customer** phrases. The last is the one people skip and the one that shows: a hook built
from customer wording outperforms a hook built from company wording for the mundane reason that the
reader recognises the first as a description of himself.

**With no brief at all, still run. Two habits do the load-bearing part of its job.**

- **Say which register you are writing in, in the deliverable, before the lines.** Register is
  normally inherited rather than chosen (`../audience-research/SKILL.md` states why once). When
  nothing was inherited you are choosing it, and an unlabelled choice is one nobody can correct.
  Name it, name what in the request implied it, and let the reader overrule you in one word.
- **No hook invents a specific.** A number, an interval, a named customer, a share, a rate — if the
  business has not stated it, it does not go in a line. This is the single most likely place in the
  whole plugin for a fabrication to enter, because specificity is what makes a hook work and the
  fastest way to get it is to make it up. Write `NOT ESTABLISHED — <what would close it>` in the
  slot instead; the discipline is stated in full in `../audience-research/SKILL.md`.

## Register decides which of the eight is available, not only how it sounds

Eight types: **outcome · time · effort · callout · contrarian · pain · mechanism · transformation**.
Five registers: `Conservative B2B (DACH)` · `Technical / industrial` · `Consumer / lifestyle` ·
`Mission / nonprofit` · `Direct-response`, defined in
`../audience-research/references/register-profiles.md`.

Crossing them is not a matter of turning the volume up or down. In one register a type's defining
move is unavailable altogether and something else has to stand in its place; in another the same
type is the strongest line on the page. `references/hook-taxonomy.md` holds all forty crossings,
each with the line it produces and what the register did to the move.

## The procedure

1. **Name the surface and the register.** Hero line, email subject, ad first line, social opener,
   button label — the surface sets a hard limit that no amount of craft negotiates around, and it
   binds before register does. `references/headline-formulas.md` opens with those limits.
2. **Name the one thing the line has to claim.** One. If two things are competing for the slot, the
   page needs two sections, not a longer hook. Take it from the brief's ranked problems, or ask
   exactly one question to get it.
3. **Pick three types deliberately** from `references/hook-taxonomy.md` — read the register's row
   under each, not the whole file. Three, because all eight produces forty lines, and forty lines is
   not a choice offered to the client, it is a decision handed back to them unmade.
4. **Build each into a sentence** with `references/headline-formulas.md`. Step 3 chooses the claim
   and step 4 chooses the sentence; that split is the entire boundary between the two reference
   files, and each states its own side of it.
5. **Cut to the surface limit, then read the survivors aloud.** A line that needs a breath in the
   middle is two lines. A line whose meaning arrives only at the last word will be truncated exactly
   there.
6. **Deliver five to seven, each labelled with its type, and recommend one.** The label is what lets
   the client reject an *angle* rather than a wording, which is the disagreement worth having.

## The quick lane

Most requests here are one line long: *punchier headline*, *give me a few subject lines*, *what
should the button say*. Run steps 1, 3, 4 and 6 and skip the rest. Three variants from three
different types beats seven from one, and the reason to say which types they are is that the client
usually knows which angle is right and cannot name it until he sees two that differ.

If the request is to improve a line that already exists, read it first for which type it is
currently attempting. Half the time the line is a good angle executed badly, and the fix is one
construction swap in `references/headline-formulas.md` rather than a new set.

## Where this stops

- **A page hero is built with `references/hero-build.md`.** A hero is a compressed argument in which a
  subhead, its proof slots and a button each carry part of the load. That file builds the headline,
  subheadline, proof slots and button, and the eight types choose the angle inside it. What the
  section has to accomplish on the page is still decided in
  `../conversion-page-build/references/section-playbooks.md`. A headline handed back on its own is
  not a hero handed back.
- **Not the paragraph underneath.** Once the line is settled and the copy around it needs work, that
  is `../copy-sweeps/SKILL.md`.
- **Not an offer repaired by phrasing.** A line that refuses to sound like anything usually has
  nothing standing behind it. Say that, and go to `../offer-architect/SKILL.md`, instead of
  producing a twelfth variant — which is the request this skill is most easily talked into.

## Output

The lines, each tagged with its type and, where it matters, the surface it was cut for. One
recommendation with the reason. Any slot left as `NOT ESTABLISHED` shown as it stands rather than
filled, so the gap is visible to whoever can close it. If the register was inferred rather than
inherited, that sentence goes at the top, not in a footnote.
