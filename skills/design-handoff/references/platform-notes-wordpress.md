# Platform notes — WordPress

Five behaviours that are true of WordPress builds and false or irrelevant elsewhere, in the
three-part shape `../SKILL.md` sets for every platform file.

That file also decides when this one loads, and why no platform file is ever read by default;
neither is repeated here. If you have opened this without WordPress having been named as the build
target, close it. The constraints below will make you specify around problems the build does not
have.

None of these notes is a build instruction.

## 1. An FAQ accordion's markup belongs to the widget, not to the spec

**Behaviour.** On WordPress an FAQ section is usually assembled from a page builder's accordion
widget. Each builder emits its own markup and its own class names for the same visible component,
and those change with the builder's own versions. Many keep the panel text in the served HTML and
hide it with CSS; others inject it only after a script runs.

**The failure.** Two, from the same root. A spec that names a class or a DOM shape is writing an
instruction the build can only honour until the widget is swapped or updated — and a widget swap is
invisible in a design review, so the instruction is silently dropped. And a spec that says "FAQ
accordion" without saying whether the answer text must be in the served HTML gets built a way that
reads perfectly to a person and is empty to anything reading the page without running scripts —
which is what breaks note 2.

**What the spec should say.** Name the component and the behaviour: one question per row, one row
open at a time or all closed on load, and **the answer text present in the served markup**. Never
name a class, a widget, or a builder. If a visual detail matters — the row divider, the open/close
affordance — describe what it has to communicate, and expect the builder's default unless someone
has budgeted for overriding it.

## 2. Structured data goes on the FAQ, and a visible summary block is a separate argument

**Behaviour.** An FAQ section can carry `FAQPage` structured data describing its question and answer
pairs. A visible summary block near the top of a page carries no structured data at all, and it
spends the most valuable reading position on the page.

**The failure.** A spec that asks for a visible summary block in order to be picked up by answer
engines adds a block the reader has to get past and produces nothing machine-readable in return.
The mirror-image failure is a spec that promises a search rich result from FAQ markup. **Checked
2026-09-08: the URL for Google's FAQ structured-data documentation now redirects to Search Central's
documentation-updates page, at an entry recording that the documentation was removed because the FAQ
rich result feature is — their words — "no longer shown in Google Search results", and, in an
earlier entry, that before the withdrawal the feature had already been narrowed to a small set of
recognised government and health sites.** Structured data still describes the page to anything
parsing it. A rich result is not what it buys, and a handoff that promises one is promising
something that has been taken away. Re-check before repeating this; it is the kind of claim that
moves.

**What the spec should say.** Put the question and answer pairs in the FAQ pattern, and state that
the structured data must describe exactly the questions and answers the page actually shows — a
schema block listing questions the page does not display is a defect, not a bonus. If a visible
summary is genuinely wanted, justify it as a reader decision on its own merits, give it a rank in
the scan path, and say what it displaces.

## 3. Language parity covers content and structured data, never internal links

**Behaviour.** Where the translation layer gives each language its own set of pages — the common
model, though not the only one — the sets are rarely identical: a page that exists in one language
often does not exist in another, or exists at a different depth. A proxy layer that generates every
URL in every language does not have that gap, but it does not remove the decision below; it only
moves it from "does this page exist?" to "is the page it points at worth pointing a reader at in
this language?"

**The failure.** A spec that says "mirror the other language's page" gets read as mirror everything,
and the internal links get mirrored with the rest — producing links that send a reader of one
language into pages in the other, or links to pages that do not exist in that language at all. Both
survive design review, because in the design the link is just a link.

**What the spec should say.** Name the layers that are mirrored — body copy, headings, meta title
and description, structured data — and state explicitly that **navigation and internal links are
decided per language, against what actually exists in that language.** Where the counterpart page
does not exist, that is a content finding for the handoff, not a link for the designer to draw.

## 4. A post-deploy check against a cache proves nothing in either direction

**Behaviour.** WordPress sites commonly run a full-page cache, often with a CDN or edge cache in
front of it. The two layers expire independently, so a page can serve pre-change HTML after a change
has been saved, and can keep serving it after one of the two layers has been cleared.

**The failure.** Someone checks the live page after a deploy and reports the result as fact. A pass
can be the old page passing; a fail can be the old page failing. The second is worse, because it
sends the build back to fix something that was already fixed, and the fix that "worked" was the
cache expiring on its own.

**What the spec should say.** Any acceptance criterion in the handoff that will be verified on the
live page carries its own verification condition: **both cache layers purged, then a fresh request,
and the response checked — not a browser tab that may be showing its own cached copy.** A screenshot
is not a check. State this next to the criteria rather than in a footnote, because the criteria are
what gets copied into a ticket.

## 5. An image optimiser can quietly refuse the loading priority the spec asked for

**Behaviour.** WordPress image-optimisation plugins and image CDNs rewrite `<img>` tags on the way
out. Some of them take loading-priority attributes such as `fetchpriority` under their own
management, applying their own policy instead of preserving what the markup asked for — so an image
a spec designates as the priority image can reach the served HTML without the attribute, and nothing
reports that it was dropped. **What each product's policy actually is, and under what conditions it
withholds the attribute, is deliberately not stated here: it differs by product and by version, and
this file has not verified any of them.** The spec does not need the mechanism. It needs to survive
the fact that there is one.

**The failure.** The spec says "the hero image loads first", the designer builds around that promise,
and the measured paint time does not move. The promise was never the build's to keep once an
optimiser sat in the path.

**What the spec should say.** Do not specify an attribute. **Name which element must be the largest
contentful paint element at each viewport that matters, and treat "is an image optimiser in the
path?" as a fact to establish before promising any loading behaviour at all.** If one is in the
path, the loading order is a build-and-measure item and the handoff should say so rather than assert
it. Where the answer is unknown, write it `NOT ESTABLISHED — <what would close it>`
(`../../audience-research/SKILL.md` states the marker).
