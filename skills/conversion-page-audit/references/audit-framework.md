# Audit framework

Two layers of checks. The first is organized by the eleven page sections `conversion-page-build`
writes — Hero, Problem, Outcome, Solution, Mechanism, Value stack, Proof, Objections, Guarantee,
CTA, FAQ — so every section that skill can write, this file can check. The second is the handful of
checks that don't belong to any one section: page speed, schema, what happens after the click, and
whether the page is even being measured.

Every check below inherits the rung discipline from `evidence-rules.md`. Say which rung a finding
rests on — rendered capture, `page_facts.py`'s static-markup parse, or a Conversion Brief — and
never let a markup-only signal stand in for a rendered-layout claim. `page_facts.py`'s own `notes`
array flags several of these gaps inline (no h1, no schema, a query-string URL, an early lazy-loaded
image); read `notes` for its content, not for a fixed position — the array is not ordered by
severity or by anything else you can rely on.

Forms, signup flow and popup behaviour have their own file, `form-and-signup-audit.md` — this file
only flags that a form exists and belongs to a given section; it does not repeat the field-level
checks.

## Section-by-section checks

### Hero

- **Message match.** Does the headline restate the visitor's own trigger — the ad, the search
  query, the referring page — in that source's own words, or does it fall back to a general
  homepage claim? A mismatch here caps every other finding on the page: nothing below fixes a
  visitor who arrived expecting one thing and read another. This is a traffic-source comparison, so
  it needs the ad or query text as an input, not just the page — if you don't have it, say so under
  "Could not check" rather than assuming the headline is fine.
- **Value proposition clarity.** Can a stranger say, in five seconds, what this is, who it's for,
  and why it matters? Feature-language ("real-time dashboards") is a common substitute for
  benefit-language ("know which feature to build next") — check which one is doing the work in the
  first sentence a visitor reads.
- **Headline effectiveness.** Outcome-focused rather than company-focused, specific rather than
  clever, and consistent with the traffic source's own register. A headline that is vague enough to
  fit any page in the category is a finding, not a style preference.
- **One primary action.** Count every competing call to action in the first viewport —
  `page_facts.py`'s `ctas` array is a markup-level first pass (it matches on a fixed hint list, so
  it can under-count a CTA phrased outside those hints and it cannot tell you what's visible without
  scrolling on a phone). More than one primary action in that space is a leak; confirming what's
  actually above the fold on a real viewport needs a rendered capture.
- **LCP candidate check.** `lcp_candidates` names the first few images in document order — treat
  that as a candidate list, not an identified Largest Contentful Paint element, which depends on
  rendered layout, viewport and load timing that static markup cannot see. The one exception:
  finding one of those candidates marked `loading="lazy"` is a deterministic, markup-visible defect
  — it defers the browser's earliest likely candidate behind the lazy-load trigger — and belongs
  under "Fix now" on its own, not under a caveat about LCP in general.

### Problem

- Does the page state the visitor's problem in their own language, or in the vendor's internal
  vocabulary? Check against the Conversion Brief's Voice of customer section if one exists; without
  it, this check is a plausibility read, not a verified match, and the report should say so.
- Is the problem specific to this audience, or a generic pain statement that would fit any
  competitor's page unchanged?

### Outcome

- Is the promised outcome concrete — measurable, timeframed, or both — or is it a soft claim like
  "save time" that resists being wrong?
- Does the outcome promised here match the headline's promise, or has the argument quietly shifted
  between the top of the page and this section?

### Solution

- **Offer clarity.** Can a stranger answer, without scrolling elsewhere: what it is, who it's for,
  what it costs, and what happens when they click? Each unanswered question is a separate friction
  point, not one combined finding.
- **Price presented or hidden.** Hiding price is a legitimate choice only for high-ticket or
  call-booking funnels; anywhere else, treat a hidden price as a friction finding, not a strategy
  the page is entitled to.

### Mechanism

- Does the page explain *how* the outcome happens, in a way that's specific to this product, or
  does it only assert the outcome and expect the visitor to take it on faith? A missing mechanism
  leaves the "will this work for my situation" objection with nowhere to land — cross-check against
  the Objections section below rather than treating it as a separate gap.

### Value stack

- If the offer is described as a bundle, are its components itemized (what, and roughly what each
  is worth), or is it one undifferentiated claim of value? This file only checks whether a claimed
  stack is legible — constructing one from scratch is `offer-architect`'s job, not this audit's.

### Proof

- **Trust signals.** Customer logos, testimonials, case-study numbers, review scores — present, and
  placed near the claims and CTAs they support rather than stranded in the footer. Position is a
  rendered-layout claim; presence in the markup is not the same thing as visible near the right
  element, so keep those two findings separate.
- **Attribution quality.** A testimonial with a name, role and (ideally) a company reads as real; an
  anonymous quote reads as filler and can cost more credibility than it earns. Flag anonymous proof
  as a finding, not as proof that's merely weaker.
- **Enumerate, don't eyeball.** If you're counting logos, testimonials or reviews, enumerate the
  whole set from a rendered DOM and de-duplicate before reporting a number — `evidence-rules.md`'s
  rule on this exists because partial counts are wrong in a way that looks exactly like a right
  answer. `page_facts.py`'s `images` array is a floor for a logo count, not the count itself: it
  won't see a CSS `background-image`, an inline `<svg>`, or a `<picture>`/`<source>` logo.

### Objections

- Does the page address the objections a buyer in this category actually raises — price, "will this
  work for my situation," implementation difficulty, "what if it doesn't work" — through FAQ copy, a
  guarantee, a comparison, or process transparency? An objection with no home anywhere on the page
  (not here, not in the FAQ) is a gap worth naming specifically, not a generic "add more trust"
  finding.
- If a Conversion Brief exists, check its ranked Objections section against what the page actually
  answers — a brief that lists an objection the page never touches is a finding on the page, not on
  the brief.

### Guarantee

- Is risk reversed at all — a guarantee, a trial, "cancel anytime," a return policy — or does the
  full risk of being wrong sit with the buyer?
- Is the guarantee specific (named term, named condition) or a vague "satisfaction guaranteed" that
  reads as filler the same way an unattributed testimonial does?

### CTA

- **Placement, copy and hierarchy.** One clear primary action with value-bearing button copy ("Start
  Free Trial," not "Submit"), repeated at natural decision points rather than only once at the very
  top or bottom.
- **The path after the button.** Does clicking lead somewhere, or does the funnel dead-end at a bare
  confirmation with no next step? A dead-end "thanks" page is a finding about unmonetized or
  unguided traffic, not a compliment on a working funnel. This is a separate page from the one being
  audited — note it as a distinct finding rather than folding it into the CTA's own copy or
  placement.
- `page_facts.py`'s `ctas` array is a hint-matched subset of `links`, not a verified inventory —
  a button whose copy carries no keyword from that hint list (a "Continue with Google" button, for
  instance) will not appear in it. Absence from `ctas` is never itself a finding.

### FAQ

- Does `schema_types` include `FAQPage`, and does the schema's question/answer content match what's
  actually visible on the page? Test this against the canonical URL with no query string appended —
  `evidence-rules.md`'s rule on this exists because some configurations serve different markup to a
  parameterised URL, and a schema check run against the wrong variant produces a confident false
  negative.
- Are the questions genuine objections a buyer would raise, or unrelated trivia that pads the
  section without doing any persuasive work? Cross-check against the Objections section — the two
  should agree on what actually worries this audience.

## Page-level checks

Checks below don't belong to one page section — they're properties of the whole page, or of what
happens around it.

### Visual hierarchy and scannability

Can someone scanning, not reading, get the main message? Are the most important elements the most
visually prominent ones, and is there enough separation between sections that the page doesn't read
as one undifferentiated block? This is a rendered-layout judgment start to finish — static markup
carries no information about size, contrast or spacing. Without a rendered capture, this whole
check goes to "Could not check," not to a guess based on document order.

### Page speed and Core Web Vitals

`lcp_candidates` and the early-lazy-image note (see Hero, above) are the only page-speed signal
`page_facts.py` can produce. Actual load timing, the true Largest Contentful Paint element, and
Core Web Vitals scores require a real measurement tool — Lighthouse or the browser's own Performance
panel — and belong under "Could not check" until one has actually run.

### Schema and structured data

Cross-check `schema_types` against what the page should plausibly carry for its purpose (a
`FAQPage` block if it has a visible FAQ, `Organization` at minimum). Confirm against the canonical
URL, unmodified — the same query-string caveat as the FAQ check above applies here, and a schema
result taken from a cache-busted or parameterised fetch is not a result for the URL a crawler will
actually see.

### Path after conversion

What happens in the funnel after the CTA is clicked is not a copy problem on the audited page — it's
a separate step that can leak just as badly: a dead end, a confusing confirmation, an upsell nobody
was warned about. Note it as its own finding, scoped to whichever page or step it actually lives on,
rather than folding it into the CTA's own copy or placement.

### Measurement

Is a conversion event firing at all, and if the traffic is paid, is the platform's click identifier
(`fbclid`, `gclid`, `ttclid`, `msclkid` or equivalent) carried through to the actual conversion? An
unmeasured funnel cannot be optimized regardless of what else this audit finds, which is why this
check runs even though it isn't itself a conversion leak. `page_facts.py` cannot see script-fired
events at all — this is a network-capture or analytics-access question. Where you don't have either,
name the specific access that would close the gap (read access to the analytics account, or a
network capture during a real click-through) rather than leaving it as an unexplained gap.
