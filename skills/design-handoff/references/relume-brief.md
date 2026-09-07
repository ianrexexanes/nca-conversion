# The wireframe brief

The document someone opens to lay this page out for the first time — a person, or a generator that
takes a written brief. It carries structure and content function. It carries no appearance at all.

`section-to-component.md` decided which components each section needs; this file is how that gets
written down. What the reader notices first, and how strongly, belongs to
`figma-refinement-spec.md` and is deliberately absent here.

## The one rule: function, never appearance

**No adjectives about how it should look.** "Modern, clean, with a bold hero" produces a wireframe
that is a guess wearing adjectives — and because the adjectives are unfalsifiable, nobody can say the
guess is wrong. Two rounds later the page is being redesigned by argument.

Every line in the brief should be checkable against the copy. "The stack has eight items and the
reader must be able to count them without reading them" is checkable. "The stack should feel
substantial" is not.

The one appearance-adjacent thing that does belong: **relative prominence stated as rank**, and even
that is written in the refinement spec rather than here, so the wireframe comes back with structure
that can then be weighted rather than weighting that has to be unpicked.

**Which is why the fold list is not in this brief either.** What has to be readable before any
scroll is a prominence decision, and this document makes none. `figma-refinement-spec.md` sets it at
step 3, once a layout exists to set it against. Putting it here would mean deciding what the hero
leads with before anyone has seen a hero — you hand the generator your answer and get it back as
confirmation, which is the specific thing the two-document split exists to prevent. In the assembled
handoff the list is present; it arrives with the refinement spec, not with the brief.

## Shape

A page preamble, then one block per section, in the page's order.

### Page preamble

- **What the page is** — the page type in one line (`../../conversion-page-build/references/page-types.md`
  names them), and where its traffic comes from.
- **Who reads it** — one line from the Conversion Brief's ICP. Not the persona document; one line.
- **The one action** — the single thing this page exists to get. If there are two, say which is
  primary and why the second one earns its place.
- **Sections, in order, with a count.** A generator handed nine blocks and no count cannot tell a
  nine-section page from an eleven-section page that lost two blocks in transit.
- **Assets that exist, and assets that do not.** Below.

### One block per section

```
## <n>. <section_type>
Does:            <purpose — one sentence>
Reader takes in: <content_hierarchy — ranked, first to last>
Components:      <from the vocabulary in section-to-component.md>
Narrow viewport: <responsive_intent — stacks / collapses / reorders / hides (flagged)>
Copy:            <the approved copy for this section, verbatim>
Not needed:      <the component someone will suggest and this section should refuse>
```

The first five fields come straight from the section spec's five keys
(`../../conversion-page-build/SKILL.md` owns it). `Copy` is the approved text itself, for the reason
in the next section. `Not needed` is this file's own addition and costs one line: it is the field
that survives the first review meeting, because a stated refusal is something to argue with, while
an absence is just an oversight for someone to helpfully correct.

## Include the copy, not a pointer to it

A brief that points elsewhere for the copy gets laid out from the brief alone, and the layout comes
back sized for the summary rather than for the sentences. A heading that is nine words in the copy
and three words in the brief gets a container built for three.

Where the copy is long enough that inlining it makes the brief unwieldy, inline the headings and
first lines verbatim and mark the remainder by length — "four paragraphs, roughly 180 words" — so
the container is at least sized against something real.

## Assets that do not exist yet

Name the slot, say what it has to show, and mark it `NOT ESTABLISHED — <what would close it>`
(the marker is the plugin's, stated in `../../audience-research/SKILL.md`).

Never describe a photograph someone is hoping to take as though it exists. The wireframe gets built
around it, the build gets built around the wireframe, and the page ships with a placeholder that
everyone has stopped seeing.

The same applies to proof: a logo row with four logos in the brief and two logos in reality is a
layout that breaks on the day it is populated.

## How long

Long enough that a stranger could lay the page out without asking a question. Short enough that it
is not the page. A brief longer than the copy it describes is a brief nobody reads to the end, and
the parts nobody reads are at the bottom, which is where the FAQ and the CTA live.

## The extent of what was checked

`../SKILL.md` states why these files assert nothing about the tools they are named after. What was
actually checked here, so the limit is on the record: **on 2026-09-08, Relume's own site described
its flow as starting from a brief document rather than from a form.** That is the whole of it. Field
names, accepted file formats, length limits and how anything parses what it is handed were not
verified, and all of them change without notice.

So before pasting: look at what the tool in front of you is actually asking for, and reshape the
headings to match it. The content is what has to survive the reshaping. The layout of this brief is
not load-bearing and was never meant to be.
