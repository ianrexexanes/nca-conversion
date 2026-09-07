# Test design

What makes a "Test, don't guess" entry in `report-template.md` more than a hedge. Anyone can write
"this might be worth testing" — this file is what turns that into a claim you can actually stand
behind: whether a test is warranted at all, and whether the traffic on this specific page could ever
produce a real answer.

## When a test is worth running

A test earns its place when the direction is genuinely unclear and a specific, falsifiable
hypothesis can be written for it — not "let's see what happens," but a shape like: *because
[something you observed or measured], we believe [a specific change] will cause [a specific outcome]
for [a specific audience], and we'll know it worked when [a specific metric] moves.* If you can't
fill in all five blanks, the finding isn't ready to be a test yet — it's still a hunch.

Not everything that looks like a test candidate is one. A confirmed defect — a broken form field, a
dead link, a missing alt attribute, a schema block that fails to validate — does not need a test to
justify fixing it. Testing exists for cases where reasonable people could disagree about the
direction of a change; it is not a formality to clear before shipping something that is simply
wrong. Route confirmed defects to "Fix now" and save testing for genuine uncertainty.

## What a minimum detectable effect costs at low traffic

The minimum detectable effect (MDE) is the smallest lift you'd actually act on — and the smaller it
is, the more traffic it takes to prove. The relationship is not linear, it's brutal: at a 3%
baseline conversion rate, detecting a lift as large as 50% takes on the order of ten thousand
sessions across both variants, but detecting a lift of only 10% at that same baseline takes on the
order of a quarter million — over twenty times the traffic, to catch a change a fifth the size.
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
analysis methods can shave some of the requirement down, but they close a gap of tens of percent, not
an order of magnitude — they do not rescue a test that needs ten times the traffic the page actually
gets.

## What belongs in the "Test, don't guess" entry

Every entry in that section should carry enough for the reader to judge feasibility without doing
their own arithmetic:

- The hypothesis, in the because/we-believe/will-cause/measured-by shape above.
- The page's current baseline conversion rate and approximate traffic, even when both are estimates
  — say so if they are.
- Whether, at that traffic, the test is plausibly finishable in a reasonable window, or whether it
  isn't.
- If it isn't: say that directly, and name the qualitative alternative instead of leaving a test
  recommendation on the page that can never actually close.

A "Test, don't guess" entry with no traffic context attached is not more rigorous than a straight
recommendation — it just defers the guess to whoever tries to run the test later.
