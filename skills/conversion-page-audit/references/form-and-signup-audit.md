# Form and signup audit

Depth on the one section `audit-framework.md` deliberately keeps thin: any form on the page,
whether it's a lead-capture form in the Solution section, an email field in a popup, or a full
signup flow the page hands off to. Read `evidence-rules.md` first regardless — the same rung
discipline applies here: `page_facts.py`'s `forms` key is a fetched-markup source, reliable for
field count and type, blind to anything about layout, timing or interaction.

## Field count and friction

Every field past the minimum costs completions — as a rule of thumb, three fields is close to a
baseline, four to six fields cost roughly a tenth to a quarter of completions, and seven or more can
cost a quarter to half. Treat those as a prioritization signal for which field to question first,
not as a lift you can promise for this specific page — a benchmark from elsewhere does not transfer
to this form's audience or its offer, the same caution `evidence-rules.md` applies to any borrowed
number.

`page_facts.py`'s `forms[].fields` gives the field list straight from markup: name, type, and
whether `required` is present. That's enough to count fields and flag which ones are marked
required — it is not enough to say whether a field is genuinely necessary, which is a business
question, not a markup question.

## Required-field justification

For every field marked required, ask: is this needed before the visitor can be helped at all, or
could it be collected later, once the value has already been demonstrated? Phone number and company
name are the fields most often required out of habit rather than necessity — both are usually
deferrable. Email (and a password, if the flow needs an account) is normally the only field that
earns "required" outright.

A required field that fails this test is a "Fix now" candidate: cut it, or move it to a
post-conversion step. A field that passes — required and justified — belongs under "Not a problem,"
named as checked, so nobody re-flags it next audit.

## Field-level friction signals

- **Labels versus placeholders.** A label that only exists as placeholder text disappears the
  moment someone starts typing, leaving them unsure what they're filling in. `page_facts.py` does
  not currently distinguish a `<label>` element from a field's `placeholder` attribute, so this
  check needs a rendered look at the form, not the JSON output — route it to "Could not check"
  without one.
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
- **Social authentication.** A "Continue with Google" or SSO option, prominently placed, often
  converts better than the email path alone for the audiences that have it available. Watch for a
  detection gap here: `page_facts.py`'s CTA hint list has no entry for "Google," "Microsoft," or
  "continue with," so a social-auth button will not appear in the `ctas` array even when it's the
  most prominent action on the page — check `links` more broadly, or look at the rendered page,
  before concluding a signup form has no social option.
- **Single-step versus multi-step.** Three or fewer fields generally works as one step; a B2B flow
  collecting more than that usually converts better split into steps that each feel completable in
  seconds, hardest questions last.

## Popup behaviour

- **Trigger fit.** A popup's trigger should match the page it's on and the traffic reaching it: a
  time delay of roughly thirty to sixty seconds or a scroll-depth trigger around a quarter to half
  the page suits engaged, organic reading; exit intent suits e-commerce and lead gen; a click
  trigger (opening a form only when the visitor asks for one) carries no annoyance cost at all.
  Judge the trigger against the page's actual traffic and purpose, not against a single "best"
  default.
- **Frequency and dismissal.** A popup should show once per session and remember a dismissal for
  some real span of time, not reappear on every page load. This behaviour only shows up across
  repeated interaction — a reload, a second visit — which static markup and a single-page capture
  both miss. Route it to "Could not check" unless you've actually tested reload behaviour.
- **Pre-checked consent.** A checkbox that starts checked for a marketing opt-in is a compliance
  problem, not a UX nitpick. `page_facts.py` currently records whether a field is `required`, not
  whether a checkbox carries a `checked` attribute — that is a real gap in what the script can tell
  you, not a "not a problem" by omission. Confirm this by reading the rendered form or the raw
  markup directly for a `checked` attribute on the relevant input.
- **Mobile behaviour.** A full-screen interstitial that blocks content before the visitor has seen
  anything is treated as a poor experience on mobile specifically, distinct from the same popup's
  behaviour on desktop. This is a rendered, per-viewport check.

## Where this connects back

`audit-framework.md`'s Solution and CTA sections flag *that* a form exists and where; this file is
what you open once that flag is raised, to say specifically what's wrong with the form itself. Keep
findings from this file in whichever page section the form actually lives on when you write the
report — this file doesn't get its own report section.
