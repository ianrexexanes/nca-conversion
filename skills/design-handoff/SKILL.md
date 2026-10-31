---
name: design-handoff
description: "Use when approved page copy becomes a design spec — before opening a design tool. Covers section type, purpose, content hierarchy, components, responsive intent, visual hierarchy, emphasis, above-the-fold priority, scan path. Also use when the user says 'hand this to design', 'wireframe this', 'Relume brief', 'Figma spec', 'turn this copy into a layout', or has finished copy and asks what's next."
license: MIT
metadata:
  version: 0.2.0
---

# Design handoff

The copy is approved. What a designer or a wireframe generator needs from it is not the words — it
is what each block of words has to do to the reader, in what order, and which of those things has to
survive a phone. This skill turns the one into the other, and decides nothing the copy already
decided.

## The gate: approved copy, and a section spec per section

Two inputs. The second is the one that goes missing.

**Approved copy, not a draft.** A layout built around a paragraph that is still being argued about
gets rebuilt, and the rebuild is always worse, because by then it is a patch on a shape that was
chosen for different words. If the copy is still moving, stop and say so.

**A section spec per section.** `../conversion-page-build/SKILL.md` produces one alongside the copy,
under its `## The section spec` heading, and this skill reads it by five key names and no others:
`section_type`, `purpose`, `content_hierarchy`, `components`, `responsive_intent`. That file owns
the shape of the spec and the reason it is written after the copy rather than before it.

Copy that arrives without specs can still be handed off — write the specs from the copy first, and
**mark them inferred in the output**. A spec reverse-engineered from finished copy records what the
copy appears to do, which is not the same thing as what it was built to do. Where those two differ,
a designer will faithfully lay out the wrong intent, and nothing downstream will catch it.

## The sequence

Four steps. The first three always run. The fourth usually does not.

1. **Map each section spec to components** — `references/section-to-component.md`. Turns the five
   keys into a component list per section, plus the one thing about that section that constrains a
   layout.
2. **Write the wireframe brief** — `references/relume-brief.md`. Page-level framing, then one block
   per section: structure and content function, no appearance.
3. **Write the refinement spec** — `references/figma-refinement-spec.md`. Visual hierarchy,
   emphasis, above-the-fold priority and scan path: the four things the wireframe does not settle.
4. **Platform notes, conditionally** — see below.

Steps 2 and 3 stay separate documents on purpose, and in that order. The reason is stated in
`references/figma-refinement-spec.md`'s opening and is not repeated here.

## The platform pass runs only when the platform was named

**Do not open `references/platform-notes-wordpress.md` unless the build target has been named and it
is WordPress.** A Webflow build, a Framer build, a hand-coded build and an unnamed build all load
nothing here.

This is not filing tidiness. A platform note describes a constraint that is real on one platform and
false on another, so a spec carrying a constraint that does not apply makes the designer solve a
problem that is not there — and then defend the solution when someone questions it. Wrong notes cost
more than no notes.

If the target has not been named, ask. If the answer is "not decided yet", write the handoff
platform-free and record in the output that **the platform pass has not run**, so whoever picks up
the build knows a check is outstanding rather than assuming it passed.

**Every platform file has the same shape and nothing else in it:** one note per behaviour, each
stating three things — the platform behaviour, the failure that behaviour causes, and the wording
that avoids it. A platform with no file in this skill gets no notes; never the WordPress ones as a
default, which is the specific mistake the conditional exists to prevent.

## The tool names are on the doors, not in the method

Two reference files are named after tools — `references/relume-brief.md` and
`references/figma-refinement-spec.md` — because those are the names people ask for. Nothing in either depends on the tool, and **neither makes a
claim about what any tool does with what it is given.**

That restraint is deliberate. A skill that says "tool X accepts a description shaped like this" is
making a claim about somebody else's product that goes stale silently, and the reader has no way to
tell a current claim from a two-year-old one. So these files describe what the document contains and
why it is shaped that way. Where something about a tool genuinely was checked, the file says so with
the date it was checked, and says nothing beyond what the check covered.

## Register reaches design in exactly one place

Register is inherited from the Conversion Brief and never re-decided here; the reasoning behind that
belongs to `../audience-research/SKILL.md`. The five profiles themselves live in
`../audience-research/references/register-profiles.md`.

It touches one decision in this skill: **how much emphasis the page is allowed to spend.** Everything
else here is structural and travels unchanged — the same section has to do the same thing to a
reader whoever that reader is. `references/figma-refinement-spec.md` carries that one intersection,
and it is the only file in this skill that reads a register row.

## What this skill does not do

- **It does not rewrite copy.** If a section cannot be laid out because the copy never says what the
  section is for, that is `../copy-sweeps/SKILL.md` when the problem is phrasing and
  `../conversion-page-build/SKILL.md` when the problem is a missing argument. Name which one, and
  stop.
- **It does not choose a visual style.** No palette, no type scale, no spacing values, no breakpoint
  numbers. It sets rank and relationship; a design system supplies the values.
  `references/figma-refinement-spec.md` states the refusal in full and what to do when there is no
  design system to supply them.
- **It never works from a page that has already shipped.** This skill runs forwards, from approved
  copy toward a layout nobody has built. Judging a layout that exists runs the other way and needs
  evidence this skill does not have — `../conversion-page-audit/SKILL.md`.
- **It does not build.** The platform notes exist so a spec does not ask for something the build
  target cannot do cheaply. They are not build instructions and they do not make this a build skill.

## Unresolved items

Anything the handoff cannot settle from the copy and the brief is written
`NOT ESTABLISHED — <what would close it>` in the document rather than guessed. The discipline and
its reasoning are stated once for the whole plugin in `../audience-research/SKILL.md` and apply here
unchanged. Two cases come up most: an asset the layout depends on that nobody has produced yet, and
a proof element the copy promises that does not exist.

## What this produces

A single handoff document. Under this vault's filing it lands at
`03 Projects/<Project>/<Page>/[C] Design Handoff — <Page>.md`; anywhere else, wherever the project
keeps specs. It carries, in this order: the per-section component map, the wireframe brief, the
refinement spec, and — only where a platform was named — the platform notes that apply to it.

Say where you filed it, and say whether the platform pass ran. A handoff that is silent on the
platform reads as a handoff where the platform was checked.
