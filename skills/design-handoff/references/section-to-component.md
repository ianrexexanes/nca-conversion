# Section to component

This file decides **what a section needs on the page**. `relume-brief.md` decides how that gets
written down for whoever lays it out; `figma-refinement-spec.md` decides which of those elements the
reader registers first. Three different questions, three files, and none of them repeats another's
answer.

## Reading the five keys from the design side

`../../conversion-page-build/SKILL.md` owns the section spec and produces it. This table is only what
each key decides once it reaches a layout, and what it costs when it arrives empty.

| Key | What it decides here | What an empty value costs |
| --- | --- | --- |
| `section_type` | Which row of the eleven below applies, and therefore the whole starting component list | Nothing to look up; the section gets laid out from its copy alone, which is guessing |
| `purpose` | Whether a proposed component is doing the section's job or decorating around it | Every component becomes defensible, so none can be refused |
| `content_hierarchy` | The rank order the refinement spec turns into visual weight | The designer ranks by length, and the longest element wins |
| `components` | The concrete elements to name in the brief | The brief describes prose and gets back a wall of prose |
| `responsive_intent` | What stacks, collapses, reorders or hides at narrow width | The narrow layout is discovered during build, when changing it is expensive |

A spec with `purpose` filled in and `content_hierarchy` empty is the common half-filled case. Treat
it as a gap and write the rank yourself from the copy, marked inferred — an unranked section is the
one a designer is guaranteed to get wrong, because there is nothing to be wrong against.

## The component vocabulary

Deliberately small, deliberately tool-neutral:

heading · subhead · body block · list · media slot · diagram slot · primary button · secondary link ·
form · quote block · logo row · stat block · card · repeating row · comparison table · accordion ·
badge · bordered block

**Why it is not a builder's widget list.** A brief written in one page builder's component names is
a brief only that builder can read, and it quietly commits the build to that builder before anyone
has chosen it. It also hides a substitution problem: two builders' "accordion" widgets are not the
same component, and a spec that says one of them by name looks satisfied when the other is used.

If a section genuinely needs something outside the list, name it in plain words and say what it has
to do. Never reach for a vendor's widget name to say it.

## The eleven, and what each does to a layout

The eleven section types and their order belong to
`../../conversion-page-build/references/page-architecture.md`, which carries the argument for why
that order and not another. Nothing here repeats that argument. Each row below says only what that
section constrains once it becomes a layout — a different axis, and the one this skill is for.

A page that keeps fewer than eleven maps only the ones it keeps;
`../../conversion-page-build/references/page-types.md` decides which those are.

### 1. Hero

- **Layout consequence** — the only section judged before any scroll, so everything in it competes
  for one fixed area. It is the single place where adding a component subtracts from every other
  component already there.
- **Components** — heading, subhead, primary button, at most one media slot, optionally a compact
  proof strip.
- **The over-add** — a second call to action at equal weight. Two equal buttons ask the reader to
  choose before they have been given a reason to choose anything.
- **Narrow viewport** — media moves below the button or goes entirely. Heading and button are what
  must survive.

### 2. Problem

- **Layout consequence** — the reader has to recognise themselves, which is a reading task rather
  than a scanning task. This is one of the few sections where continuous prose is right and a
  three-column grid is wrong.
- **Components** — heading, body block, optionally a short list.
- **The over-add** — icon cards. They turn one person's situation into a taxonomy, and a taxonomy is
  a thing nobody recognises themselves in.
- **Narrow viewport** — already linear; nothing structural to decide.

### 3. Outcome

- **Layout consequence** — it has to be picturable. The real question is whether the picture is
  carried by an image or by the words, and doing both usually means neither lands.
- **Components** — heading, body or list, one media slot.
- **The over-add** — generic imagery standing in for a specific result. A stock photograph makes a
  specific claim read as a generic one, which is the opposite of what the section is for.
- **Narrow viewport** — media below text.

### 4. Solution

- **Layout consequence** — the first section where the reader is shown a thing rather than told
  about one, so it is the first place a component can genuinely replace a sentence.
- **Components** — heading, body, media slot, optionally a diagram slot.
- **The over-add** — a feature grid this early. The reader has not yet been given a reason to
  compare features, so a grid asks them to evaluate before they are deciding.
- **Narrow viewport** — a diagram is the element most likely to become unreadable. State its minimum
  legible width, or state that it needs a separate narrow version.

### 5. Mechanism

- **Layout consequence** — this is usually a sequence, and a sequence has a direction that a grid
  destroys. Direction is a layout property; the copy cannot carry it alone.
- **Components** — heading, numbered steps or a directional diagram, body.
- **The over-add** — an unnumbered card grid. It presents as simultaneous options what the copy
  means as "then".
- **Narrow viewport** — steps stack and any connecting arrows disappear, so the numbering has to
  exist independently of the arrows rather than being drawn by them.

### 6. Value stack

- **Layout consequence** — it has to be **countable**. A reader must be able to see how many things
  there are before reading what any one of them is. That is a layout property, and it is the thing
  this section can fail at while every line in it reads perfectly.
- **Components** — a repeating row or card, one per item, each carrying a name and a one-line
  consequence; a total; the price.
- **The over-add** — varying the item sizes for visual interest. Unequal rows make an eight-item
  stack read as three items and some noise, which is the section arguing against itself.
- **Narrow viewport** — rows stack. The total and the price must not separate from the list they
  are the total of.

### 7. Proof

- **Layout consequence** — the layout has to keep provenance visible. A quote whose attribution has
  been moved, shrunk or dropped is decoration, and decoration proves nothing.
- **Components** — quote block with attribution, logo row, stat block, case card.
- **The over-add** — a carousel. It hides most of the proof behind an action, and the reader who
  needed convincing is exactly the reader who will not take that action.
- **Narrow viewport** — logo rows break first. Say how many logos per row at the narrow end instead
  of letting them scale down to unreadable.

### 8. Objections

- **Layout consequence** — a pairing structure. Each objection needs its answer adjacent and
  visibly attached to it; an answer that has drifted away from its objection answers nothing.
- **Components** — heading, paired blocks or a two-column list.
- **The over-add** — collapsing these behind an accordion. A collapsed objection is an objection the
  reader still has. This is the opposite call from the FAQ below, and the difference is real: here
  the reader already holds the doubt.
- **Narrow viewport** — pairs stay together. The failure mode is a two-column layout that stacks
  into all the objections followed by all the answers.

### 9. Guarantee

- **Layout consequence** — it has to look like a term of sale, not like a promotion. The more it is
  styled as emphasis, the less it reads as something the business is actually bound by.
- **Components** — heading, body, optionally a bordered block.
- **The over-add** — a badge graphic carrying a number in place of the terms. The graphic is the
  part readers discount, and it is standing where the binding language should be.
- **Narrow viewport** — already linear. The risk is a badge scaling past legibility.

### 10. CTA

- **Layout consequence** — one action, and the layout's only job is to leave nothing competing at
  that moment.
- **Components** — heading, one primary button, optionally one line of risk-removal text beneath it.
- **The over-add** — a secondary link, a navigation bar, or a footer that begins too close. Each is
  an exit placed at the point of decision.
- **The repeat** — Repeating the page's one action after a section is not a second action, so the
  over-add does not apply to it. The button comes back with the same label and the same target each
  time, with the doubt reducers under it. A different label, a different target or a link to anything
  else is still the exit the over-add names.
- **Narrow viewport** — the button stays reachable without a stretch and the risk-removal line stays
  one or two lines. Once it wraps to a paragraph it stops removing risk and starts adding reading.

### 11. FAQ

- **Layout consequence** — the one section where collapsing is correct, because the reader is
  hunting for their own question rather than reading the set.
- **Components** — accordion or list, one question per row.
- **The over-add** — moving load-bearing objections in here. The test is whether the reader already
  holds the doubt (Objections, section 8) or is checking an edge case (here).
- **Narrow viewport** — an accordion is already narrow-friendly. The thing to specify instead is
  whether the answer text has to be present in the served markup, which is a platform question and
  belongs to the platform notes.

## Two rules that decide the arguments

**A component is chosen by what the content has to do, never by what the page needs visually.** A
comparison table belongs where the copy is making a comparison. If a section's component list was
picked to break up a long stretch of page, the page has a rhythm problem and the fix is upstream in
the copy, not a grid here.

**`hide` at a narrow viewport is a content decision, not a layout one.** Stacking and collapsing
keep the content; hiding removes it, and removing content is a call that belongs to whoever approved
the copy. Any `responsive_intent` that hides something gets named in the handoff as a content change
awaiting approval — not implemented quietly because the section was tight.
