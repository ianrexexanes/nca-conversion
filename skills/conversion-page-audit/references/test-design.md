# Test design

What makes a "Test, don't guess" entry in `report-template.md` more than a hedge. Anyone can write
"this might be worth testing" — this file is what turns that into a claim you can actually stand
behind: whether a test is warranted at all, and whether the traffic on this specific page could ever
produce a real answer.

## When a test is worth running

A test earns its place when the direction is genuinely unclear and a specific, falsifiable
hypothesis can be written for it — not "let's see what happens," but five specific things nailed
down: *prompted by [what you observed or measured], propose [the specific change], predict [the
specific effect], for [the specific audience], settle it with [the specific metric].* If you can't
fill in all five blanks, the finding isn't ready to be a test yet — it's still a hunch.

Not everything that looks like a test candidate is one. A confirmed defect — a broken form field, a
dead link, a missing alt attribute, a schema block that fails to validate — does not need a test to
justify fixing it. Testing exists for cases where reasonable people could disagree about the
direction of a change; it is not a formality to clear before shipping something that is simply
wrong. Route confirmed defects to "Fix now" and save testing for genuine uncertainty.

## What a minimum detectable effect costs at low traffic

The minimum detectable effect (MDE) sets the floor: it's the smallest lift that would actually
change what you'd recommend if you saw it, and pushing that floor lower drives the traffic
requirement up fast. The relationship is not linear, it's brutal. For instance, at a 3%
baseline conversion rate, detecting a lift as large as 50% takes about 5,000 sessions across both
variants (two-sided test, 95 per cent confidence, 80 per cent power, lift measured relative to the
baseline), but detecting a lift of only 10% at that same baseline takes about 110,000: over
twenty times the traffic, to catch a change a fifth the size.
Every step down in the effect size you're willing to call meaningful multiplies the sample you need
to prove it, and most pages don't have the multiplier.

Duration follows directly from that: roughly, the sessions a test needs divided by the page's daily
traffic (times the share of visitors actually exposed to it) gives the number of days the test has
to run before it can conclude. A page getting a few hundred sessions a month, testing for a lift
smaller than something dramatic, is not looking at a multi-week test — it's looking at a multi-month
one, if it can reach a conclusion at all.

## Why most SME pages cannot A/B test their way to an answer

Run the arithmetic above against a typical SME landing page — traffic in the hundreds or low
thousands of monthly sessions, a baseline conversion rate in the low single digits — and most
proposed tests fail before they start. A rough gut check: if the sessions needed divide out to more
than a couple of months at the page's actual traffic, the page will change, the season will change,
or the business's priorities will change before the test can conclude. At that point the test isn't
rigorous, it's theatre — a commitment to wait for a number that will arrive too late to matter, or
never arrive as anything cleanly significant at all.

That is not a reason to guess instead. It is a reason to say so plainly and reach for what actually
works at this traffic level: qualitative evidence (session recordings, direct visitor feedback, a
handful of real user tests), and first-principles fixes for anything `audit-framework.md` and
`form-and-signup-audit.md` can already identify as a defect rather than a genuine toss-up. Ranking
by confidence in the reasoning is not a lesser method than testing — it is the correct method when
testing cannot produce a trustworthy answer in a useful amount of time. Sequential or Bayesian
analysis methods can shave some of the requirement down, but they close only part of the gap. They do
not rescue a test that needs far more traffic than the page actually gets.

## What belongs in the "Test, don't guess" entry

Every entry in that section should carry enough for the reader to judge feasibility without doing
their own arithmetic:

- The hypothesis, with all five parts named in the prompted-by/propose/predict/settle-it-with
  shape above.
- The page's current baseline conversion rate and approximate traffic, even when both are estimates
  — say so if they are.
- Whether, at that traffic, the test is plausibly finishable in a reasonable window, or whether it
  isn't.
- If it isn't: say that directly, and name the qualitative alternative instead of leaving a test
  recommendation on the page that can never actually close.

A "Test, don't guess" entry with no traffic context attached is not more rigorous than a straight
recommendation — it just defers the guess to whoever tries to run the test later.
