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

- **Message match.** Line the headline up against whatever actually sent this visitor — the ad
  creative, the search query, the referring page — and check whether it continues that specific
  promise or switches to a broader, one-size-fits-all pitch instead. Get this wrong and every other
  finding on the page loses most of its value, because a visitor who arrived expecting one thing
  and read another rarely reads far enough to notice the rest is good. This is a traffic-source
  comparison, so it needs the ad or query text as an input, not just the page — if you don't have
  it, say so under "Could not check" rather than assuming the headline is fine.
- **Value proposition clarity.** Read only the first sentence a visitor would actually see and ask
  whether it names a benefit or just a feature — "real-time dashboards" describes what the product
  does, "know which feature to build next" describes what the visitor gets, and pages default to
  the first far more often than the second. If a reader would need a follow-up question to know why
  any of this matters to them, the value proposition hasn't landed yet.
- **Headline effectiveness.** Outcome-focused rather than company-focused, specific rather than
  clever, and consistent with the traffic source's own register. A headline that is vague enough to
  fit any page in the category is a finding, not a style preference.
- **One primary action.** Tally how many separate calls to action compete for attention in the
  first viewport, not just how many exist on the page. `page_facts.py`'s `ctas` array is a
  markup-level first pass (it matches on a fixed hint list, so it can under-count a CTA phrased
  outside those hints and it cannot tell you which of them a phone screen actually shows before any
  scrolling happens). A visitor
  facing two or three equally weighted options above the fold has to choose which one to ignore
  before choosing to act at all — confirming what's actually there on a real viewport needs a
  rendered capture.
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

- **Offer clarity.** A visitor should be able to name the product, its intended buyer, its price
  and what clicking actually does — all from this section alone, with no need to hunt elsewhere on
  the page. Treat each of those four as its own check: a page can nail the price and still leave
  the buyer guessing who it's for, and that's a separate friction point, not a rounding error on an
  otherwise-clear offer.
- **Showing the number, or not.** Withholding the price is defensible on a genuinely high-ticket or
  call-booking offer, where a price needs a conversation to make sense — everywhere below that
  tier, an invisible price reads as evasion, not positioning, and belongs on the fix list rather
  than getting the benefit of the doubt as a deliberate choice.

### Mechanism

- Does the page explain *how* the outcome happens, in a way that's specific to this product, or
  does it only assert the outcome and expect the visitor to take it on faith? A missing mechanism
  leaves the buyer's core doubt — that this works in general but maybe not for someone in their
  specific situation — with nothing on the page to answer it. Cross-check against the Objections
  section below rather than treating it as a separate gap.

### Value stack

- If the offer is described as a bundle, are its components itemized (what, and roughly what each
  is worth), or is it one undifferentiated claim of value? This file only checks whether a claimed
  stack is legible — constructing one from scratch is `offer-architect`'s job, not this audit's.

### Proof

- **Trust signals.** Check for the standard set — customer logos, testimonials, case-study
  figures, review scores — and then check something the presence check alone misses: whether each
  one sits next to the specific claim or CTA it's meant to back up, or whether all of it has been
  swept into one footer block a visitor has to go looking for. Position is a rendered-layout claim;
  presence in the markup is not the same thing as sitting next to the right element, so keep those
  two findings separate.
- **Attribution quality.** A testimonial with a name, role and (ideally) a company reads as real; a
  quote with none of those attached reads as invented, whether or not it actually is, and
  undermines the surrounding claims more than leaving the space blank would have. Flag unattributed
  proof as a finding in its own right, not as proof that's merely weaker.
- **Enumerate, don't eyeball.** If you're counting logos, testimonials or reviews, enumerate the
  whole set from a rendered DOM and de-duplicate before reporting a number — `evidence-rules.md`'s
  rule on this exists because partial counts are wrong in a way that looks exactly like a right
  answer. `page_facts.py`'s `images` array is a floor for a logo count, not the count itself: it
  won't see a CSS `background-image`, an inline `<svg>`, or a `<picture>`/`<source>` logo.

### Objections

- Name the specific objections a buyer in this category actually carries — cost relative to value,
  doubt that the approach fits their particular situation, how hard it is to get running, and what
  happens if it doesn't deliver — and check each one against the page rather than checking for the
  presence of an "objections section" in general. A comparison table, a process walkthrough, a
  guarantee or an FAQ answer can each resolve one, but an objection with no answer anywhere on the
  page (not here, not in the FAQ) is a specific, nameable gap, not a generic "add more trust"
  finding.
- If a Conversion Brief exists, check its ranked Objections section against what the page actually
  answers — a brief that lists an objection the page never touches is a finding on the page, not on
  the brief.

### Guarantee

- Does the page put any of the risk back on itself — a money-back guarantee, a free trial period,
  an easy-exit subscription policy, a straightforward returns process — or does the buyer carry the
  entire downside of being wrong alone?
- Where a guarantee exists, does it name concrete terms a buyer could actually hold the company to
  — a number of days, a defined condition for a refund — or is it a generic reassurance
  ("satisfaction guaranteed") that commits to nothing, the same emptiness an unattributed
  testimonial has?

### CTA

- **One button, worded as an outcome.** A page should read as making one request, not several
  equally-weighted ones, and the button making that request should describe the outcome of clicking
  it rather than the mechanics of the click — "See My Personalized Quote" tells a visitor what they
  get; "Click Here" or "Submit" tells them nothing. Whatever that primary action is, it should
  reappear at more than one natural stopping point down the page, not sit once at the top and hope
  the visitor scrolls back up.
- **What happens immediately after the click.** Follow the click through: does it land somewhere
  that keeps guiding the visitor, or does the whole experience just stop at a bare acknowledgement
  screen with nothing to do next? Stopping there wastes traffic the page worked to earn, whatever
  the confirmation screen's copy says. This is a separate page from the one being audited — note it
  as a distinct finding rather than folding it into the CTA's own copy or placement.
- `page_facts.py`'s `ctas` array is a hint-matched subset, filtered internally from a larger set of
  links and buttons the script parses but does not expose in its JSON output — it is not a verified
  inventory of every actionable element on the page. A button whose copy carries no keyword from
  that hint list (a "Continue with Google" button, for instance) will not appear in `ctas` at all.
  Confirm a genuine absence by reading the raw markup directly, or by inspecting the rendered page
  if Playwright is available — never from `ctas` alone coming up short.

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

A visitor skims before they ever commit to reading, so the test is whether the page's main point
survives being skimmed — a glance at the page should leave someone with roughly the right
impression of what it's for and what to do next, without them having read a single full paragraph.
That depends entirely on what's visually loudest, how much room sections get to breathe, and
whether one part of the page reads as clearly more important than the rest — none of which static
markup carries any information about at all (it has no concept of size, color or spacing). Without
a rendered capture, this whole check goes to "Could not check," not to a guess based on document
order.

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

Two separate questions, both outside anything markup can answer. First: does anything actually
register when this page's goal action happens, or does every visit vanish into an analytics
platform with no event attached to it? Second, for paid traffic specifically: does the ad
platform's own click identifier — Google's `gclid`, Meta's `fbclid`, TikTok's `ttclid`, Microsoft's
`msclkid`, or whichever the traffic source uses — survive all the way from the ad click to the
recorded conversion, or does it get dropped somewhere in between? Either failure means the traffic
this page attracts can't actually be optimized, whatever else this audit finds, which is why this
check runs even though it isn't a page-copy problem. `page_facts.py` cannot see script-fired
events at all — this is a network-capture or analytics-access question. Where you don't have either,
name the specific access that would close the gap (read access to the analytics account, or a
network capture during a real click-through) rather than leaving it as an unexplained gap.
