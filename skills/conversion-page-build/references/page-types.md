# Page types

`page-architecture.md` describes the full eleven-section run — the shape a page takes when it has to
carry a reader from cold to convinced entirely on its own. Most pages don't do that. What follows is
which of the eleven each page type keeps, compresses, or drops, and why the job that page does inside
the funnel is what decides it — never a template to fill in regardless of the traffic arriving on it.

The question to ask before applying any of these: **how much conviction does a reader already have
when they land here, and how much does this specific page have to add?** A page meeting a cold reader
has to run more of the eleven than a page meeting someone who arrived already halfway convinced.

## Sales page (long-form)

**Walks in:** anywhere from cold to warm. **Has to walk out:** convinced enough to act, on this page
alone, with no other page in the funnel expected to close the remaining gap.

Runs all eleven sections, in the order `page-architecture.md` sets out, uncompressed. This is the
only page type where that's the right call — every other type below is a deliberate subset of this
one, cut down because the reader arriving on it doesn't need the full argument re-run.

## Home page

**Walks in:** cold, warm, and returning visitors at once, with no single traffic source to write a
matched Hero for. **Has to walk out:** oriented — the "ready to buy" visitor pointed at where to buy,
the "still researching" visitor pointed at where the research lives, neither one served a
one-size-fits-all argument that satisfies neither.

A home page cannot run one full eleven-section argument because it has no single reader to run it
for. What it runs instead is a compressed Hero → Solution → Proof loop, repeated once per audience
segment the site actually serves, each loop ending in a CTA that routes to that segment's own
dedicated page — which is where the rest of the eleven, Mechanism through Guarantee, actually lives.
Problem gets a light touch per segment rather than the full section `page-architecture.md` describes;
Value stack, Objections, Guarantee and FAQ are almost always absent here entirely, because none of
them make sense without first knowing which segment's argument they'd be resolving. A home page that
tries to run Objections or Guarantee for an undifferentiated audience ends up resolving objections
nobody on the page actually has yet.

## Opt-in page (lead magnet, newsletter, waitlist)

**Walks in:** cold to warm, arriving for content or access, not a purchase. **Has to walk out:** an
email address or equivalent low-commitment action — the actual ask this page makes is orders of
magnitude smaller than a sales page's, and the section set shrinks with it.

Keeps Hero, Problem, Outcome, Solution and CTA — the core of what's being offered and why it matters
still has to be argued. Runs a light version of Proof (a name and a number, rarely a full case study)
because the commitment being asked for doesn't carry enough risk to need heavy corroboration. Drops
Mechanism, Value stack, Guarantee and Objections almost entirely: Mechanism because "how it works" is
usually beside the point when what's being given away is the mechanism itself; Value stack and
Guarantee because there's no price to anchor against or risk to reverse; Objections because the
commitment is too low for most of a buyer's objections to have engaged yet. FAQ, where it appears at
all, answers logistics ("what will I get, how often") rather than buying objections. The framework
lever doing the most work here is reciprocity — see `conversion-psychology.md` — not the objection
handling machinery a purchase decision needs.

## Pricing page

**Walks in:** already convinced this is the right category and, usually, this specific vendor —
Hero through Mechanism have typically already happened somewhere else in the site or in a sales
conversation. **Has to walk out:** having picked a tier, not having been convinced the offer works at
all.

Starts near Value stack rather than at Hero — re-running Problem or Outcome here argues a case the
reader already accepted to get here, and wastes the one thing a pricing page has that a sales page
doesn't: a reader who is actively comparing options right now. Value stack does the section's
heaviest work, but takes a shape the eleven don't natively provide for: tier-by-tier comparison,
where the real decision isn't "buy or don't" but "which of these am I," and a recommended tier needs
to be visually obvious rather than left for the reader to compute. Proof and a compressed Guarantee
usually appear beside the tiers rather than as separate sections. Objections narrows to the handful
that are specifically about picking a tier — "what happens if I outgrow this one," "can I switch" —
not the full ranked list from the brief, most of which was already resolved upstream of this page.
CTA is usually one per tier rather than one for the whole page, which the eleven-section model, built
around a single primary action, doesn't natively describe either — treat each tier's CTA as its own
small instance of the CTA row in `section-playbooks.md`.

## Feature page

**Walks in:** already evaluating the product broadly, looking at one specific capability. **Has to
walk out:** either satisfied this capability covers their use case, or routed to a broader page if it
doesn't.

Runs a fragment of the eleven centered on one Mechanism–Proof pair for the specific capability, not a
full argument. Problem and Outcome are usually compressed into a single framing line ("for teams who
need X") rather than full sections, because the broader problem and outcome were already argued on
whatever page sent the reader here. Value stack, Guarantee and the bulk of Objections don't belong on
a feature page at all — those are whole-offer decisions, and a feature page is answering a narrower
question than the whole offer's price or risk. CTA routes back to the broader evaluation (trial,
demo, pricing) rather than closing a sale on its own.

## What doesn't fit any of these five

A page that serves genuinely two audiences with materially different needs — the `Mission /
nonprofit` register's standing case, per `register-profiles.md` — usually isn't better described by
inventing a sixth page type. It's the home-page pattern above (a segment loop routing to dedicated
pages) or the mission register's own carried-together exception (several participation paths held on
one page rather than split across several), which is a departure from the one action and is written in
the deck's `## Register notes`. Which of those two applies is a register decision, not a page-type
one. Don't force a page that doesn't match one of these five shapes into the nearest
one; name what's actually different about it and adjust the section set from first principles using
`page-architecture.md`'s dependency logic rather than this file's five templates.

## The four skeletons

Four starting shapes, described in words and never linked to a live page. A lead-generation page has
two of them, chosen by the visitor's awareness (see `page-architecture.md`, Skeleton by awareness).

- **Lead-generation page, image or video hero.** For cold, problem-aware visitors. The hero carries an
  image or video of the real product or outcome. The pain section follows it, then proof, and the page
  runs the long-form order from there.
- **Lead-generation page, form hero.** For warm, solution-aware visitors. The form sits in the hero
  beside the promise. Proof comes before pain, and the page runs the long-form order, every repeat of
  the button leading back to that form.
- **The e-commerce homepage.** Described, not scored. It sends shoppers to the categories and the best
  sellers they came for, carries the promise and the proof of delivery and returns, and routes each
  shopper on to a product page.
- **The e-commerce product page.** Described, not scored. It shows one product with its images, benefits,
  price, reviews, delivery and returns, and asks for one action: add it to the basket.

"Not scored" means no rule or check in this plugin scores a page against the two e-commerce
descriptions. They are here so a build can start from a stated shape.
