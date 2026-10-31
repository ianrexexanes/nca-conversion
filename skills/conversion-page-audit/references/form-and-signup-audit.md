# Form and signup audit

Depth on the one section `audit-framework.md` deliberately keeps thin: any form on the page,
whether it's a lead-capture form in the Solution section, an email field in a popup, or a full
signup flow the page hands off to. Read `evidence-rules.md` first regardless — the same rung
discipline applies here: `page_facts.py`'s `forms` key is a fetched-markup source, reliable for
field count and type, blind to anything about layout, timing or interaction.

## Field count and friction

Each field beyond the minimum a visitor must clear has a real cost in how many of them finish.
Visitors tend to finish short forms more often than long ones, and the longest forms lose the most of them.
Treat that as a prioritization signal for which field to question first,
not as a lift you can promise for this specific page — a benchmark from elsewhere does not transfer
to this form's audience or its offer, the same caution `evidence-rules.md` applies to any borrowed
number.

`page_facts.py`'s `forms[].fields` gives the field list straight from markup: name, type, and
whether `required` is present. That's enough to count fields and flag which ones are marked
required — it is not enough to say whether a field is genuinely necessary, which is a business
question, not a markup question.

## Required-field justification

For every field marked required, separate what the business genuinely needs before it can help this
particular visitor from what it would merely like to know sooner rather than later — the second
category can wait until after the value has already been demonstrated, whatever the form's current
requirements claim. Phone number and company
name are the fields most often required out of habit rather than necessity — both are usually
deferrable. Email (and a password, if the flow needs an account) is normally the only field that
earns "required" outright.

A required field that fails this test is a "Fix now" candidate: cut it, or move it to a
post-conversion step. A field that passes — required and justified — belongs under "Not a problem,"
named as checked, so nobody re-flags it next audit.

## Field-level friction signals

- **Labels versus placeholders.** A field whose only label lives inside its `placeholder`
  attribute loses that label the instant a visitor starts typing into it — there's nothing left on
  screen to remind them what the field was even asking for. `page_facts.py` does not currently
  distinguish a `<label>` element from a field's `placeholder` attribute, so this check needs a
  rendered look at the form, not the JSON output — route it to "Could not check" without one.
- **Single-column versus multi-column layout, and multi-step thresholds.** More than five or six
  fields is the point where a single long form usually loses to a multi-step flow with a progress
  indicator. Field count comes from `forms[].fields`; whether a progress indicator exists, or
  whether the layout is actually single-column, is a rendered check.
- **Confirmation fields.** A second field of the same type — two `email` fields, or an email field
  plus an explicit confirmation field — is friction with no real benefit; flag it directly from
  `forms[].fields` when you see the type repeated within one form.

## Signup-flow specifics

- **Password UX.** A visible strength meter and a permissive approach (allowing paste, not
  rejecting a password for looking "too random") beat a rigid rule list shown only after a failed
  attempt. This is a rendered/interaction check — markup can tell you a password field exists, not
  how its validation behaves.
- **Social authentication.** A "Continue with Google" or SSO option, prominently placed, frequently
  outperforms a plain email signup for audiences where that identity provider is already trusted
  and heavily used. Watch for a
  detection gap here: `page_facts.py`'s CTA hint list has no entry for "Google," "Microsoft," or
  "continue with," so a social-auth button will not appear in the `ctas` array even when it's the
  most prominent action on the page. The script parses every `<a>` and `<button>` internally but
  only exposes the hint-matched subset in its JSON output — it does not expose the full list — so
  confirm a genuine absence by reading the raw markup directly or by inspecting the rendered page,
  never by `ctas` alone coming up short of anything social-auth-shaped.
- **Single-step versus multi-step.** A short form tends to work fine as a single step;
  once a B2B flow needs more than that, splitting it into steps that each take only a few seconds
  to clear usually converts better, with anything sensitive or effortful pushed to the very end.

## Popup behaviour

- **Trigger fit.** A popup's trigger should match the page it's on and the traffic reaching it: a
  time delay long enough for the visitor to have read something, or a scroll-depth trigger partway
  down the page, suits engaged, organic reading; exit intent suits e-commerce and lead gen; a click
  trigger (opening a form only when the visitor asks for one) carries no annoyance cost at all.
  Judge the trigger against the page's actual traffic and purpose, not against a single "best"
  default.
- **Frequency and dismissal.** A popup earns at most one appearance per visit and should remember
  that it was already dismissed for a real stretch of time afterward, rather than resetting itself
  on every fresh page load. This behaviour only shows up across
  repeated interaction — a reload, a second visit — which static markup and a single-page capture
  both miss. Route it to "Could not check" unless you've actually tested reload behaviour.
- **Pre-checked consent.** A checkbox that starts checked for a marketing opt-in is a compliance
  problem, not a UX nitpick. `page_facts.py` currently records whether a field is `required`, not
  whether a checkbox carries a `checked` attribute — that is a real gap in what the script can tell
  you, not a "not a problem" by omission. Confirm this by reading the rendered form or the raw
  markup directly for a `checked` attribute on the relevant input.
- **Mobile behaviour.** A popup that covers the whole screen before a visitor has seen any of the
  page underneath reads as significantly more hostile on a phone than the identical popup does on a
  desktop monitor, where there's more page visible around it — judge the two viewports separately
  rather than assuming one verdict covers both. This is a rendered, per-viewport check.

## Where this connects back

`audit-framework.md`'s Solution and CTA sections flag *that* a form exists and where; this file is
what you open once that flag is raised, to say specifically what's wrong with the form itself. Keep
findings from this file in whichever page section the form actually lives on when you write the
report — this file doesn't get its own report section.
