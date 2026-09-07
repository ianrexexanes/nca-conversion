# Evidence rules

Eleven rules about what an audit is allowed to conclude, and from what. Each one exists because a
method that returns an answer returned a wrong one, confidently, in a way that looked exactly like
a right one. That is the shape of every entry here: not "this check is hard" but "this check has a
failure mode that is silent from the inside".

Read this before running a conversion audit, and again before writing the report. The closing
section is the one that makes the report honest.

### Verify rendered, not fetched — and never from a document

Claims about a live page sit on three rungs and only the top one settles anything. A page rendered
in a real browser is evidence. Fetched HTML is weaker evidence: it shows what the server sent, not
what a visitor sees, and it cannot see white-on-white text, a block collapsed by CSS, content
injected by script after load, or an element the layout pushes off screen. A project document,
ticket, status banner or CMS note describing the page is not evidence at all — it is a claim about
how the page stood on the day someone wrote it. Every finding should be traceable to a rung, and
the rung should be recorded.

The wrong answer this produces is specific. An audit asserted two page-level defects: that three
biography cards all resolved to the same photograph, and that a named person's central credential
was missing from the page. Both were false. Both came from a status banner inside a project
document rather than from the page. A correction retracting the first claim had been written the
same day and filed in a neighbouring folder, where it sat unread. A single live fetch settled both
in seconds and would have cost less than writing either sentence. The document had not lied; it was
accurate when written and had simply stopped being true, which is the ordinary condition of every
document describing a live system.

Fetch before you write, every time, including — especially — when a document already answers the
question, because a document that answers the question is the thing that stops you fetching.
`curl -sL "$URL" -o /tmp/page.html` gives you the served markup; search that for the exact string
the claim depends on, not for a paraphrase of it. When the claim is about anything a visitor
perceives — visibility, contrast, stacking order, what a photograph shows, whether an element is on
screen at all — markup cannot settle it and you escalate to a real browser and look. When a
document and a live fetch disagree, the fetch wins, the document gets corrected, and the fetch date
goes beside the finding so the next reader knows how old your claim is too.

### Defeat scroll animations before calling a section blank

Scroll-triggered animation libraries render elements at `opacity: 0` and reveal them only when they
enter the viewport. An automated capture taken at load photographs a page whose content is present
in the DOM, styled invisible, and recorded as empty space. Lazy-loaded images and anything gated on
an intersection observer behave the same way. A blank region in a capture is therefore ambiguous
between two very different findings — a genuinely empty section, and a section nobody scrolled to.

The wrong answer reads like a serious finding: *"the band between the hero and the pricing block is
empty; recommend adding content."* The band was not empty. It held a three-column feature block
that was in the DOM the whole time, at zero opacity, photographed before any scroll event fired. An
empty band is a plausible defect, which is exactly why the screenshot was believed, and nothing in
a capture flags itself as unreliable. The audit shipped a recommendation to build something that
already existed.

Before reporting anything as blank or missing from a capture, scroll the whole page and capture
again, or force the reveal before capturing. In a browser automation tool, scroll to the bottom in
steps with a wait between them, or evaluate a style override that neutralises the library's initial
state — setting `opacity: 1` and clearing the transform on the animated selector class is the
general form. Then cross-check against the DOM: if the text you expected is in the markup and
absent from the picture, the picture is what is wrong. Report a section as blank only when the
markup is empty too.

### Accept the consent banner before auditing tags

Consent management platforms hold analytics, advertising and most third-party tags until the
visitor consents. That is what they are for. Before you click accept, the tag is not in the page,
its network request never fires, and every method of looking for it — DOM search, network panel,
tag-assistant extension, raw HTML fetch — correctly reports absence. Under a consent-mode
configuration the tag may load and transmit nothing, which reads identically from outside.

The wrong answer: *"analytics is not installed — no tag call and no request to the vendor domain."*
The property was installed and collecting normally. The audit had loaded the page, searched, and
never touched the banner, so it measured the pre-consent state and reported it as the installed
state. This one is dangerous on two counts: the negative is technically accurate about the moment
it was taken and wrong about the question that was asked, and "analytics missing" is a credible
enough finding that nobody goes back to re-check it.

Interact with the banner first, then measure. Load the page, click the accept control, and only
then read the network log and the DOM — in a browser automation tool that is a click on the accept
button followed by a network-request dump; by hand it is DevTools with the Network tab filtered on
the vendor domain, cleared, and the page reloaded after consent. Test the reject path as well when
the question is whether consent mode is wired correctly. If you did not or could not accept
consent, the finding is "could not check", not "not installed".

### Pass `grep -a` when searching fetched HTML

`grep` inspects the first bytes of a file, decides it is binary, and stops printing matches.
Fetched pages trigger this constantly: one byte from a mis-declared encoding, a compression
artifact, an inline base64 font or SVG, or a stray control character is enough. At a terminal the
short-circuit is not actually silent — on GNU grep 3.11 it writes `binary file matches` to
**stderr** and exits **0**, where a genuine absence prints nothing and exits **1** — so two tells
are available for free. The silent surface is narrower than the behaviour, and it is the one you
will meet in practice: consume the result through a pipeline with stderr discarded, as in
`grep … 2>/dev/null | wc -l`, and stdout reads `0` with no diagnostic anywhere. That is a zero
produced by a search that never ran, and at that point it is indistinguishable from an honest one.

The wrong answer: *"the page carries no organisation schema — zero matches for the type key."* The
JSON-LD was there. The saved file contained non-UTF-8 bytes from an embedded font, `grep`
classified it as binary, and stopped. The count came out of a pipeline that discarded stderr and
never looked at the exit status, so both of the tells that would have caught it were thrown away
before anyone saw them, and a schema block that had been live for a year was reported as missing.
Note the shape of it: the instrument did report the problem, and the harness around the instrument
deleted the report.

Always pass `-a` when searching fetched markup: `grep -ao 'application/ld+json' /tmp/page.html`.
Read `$?` before you read the output — `1` is a genuine absence, `0` with nothing on stdout is a
binary short-circuit — and do not discard stderr on a search whose zero you intend to act on. Then
prove the file is being read at all: search for a string you know is present, such as the text
inside `<title>` or the domain itself, and confirm it hits. `file /tmp/page.html` tells you what
`grep` thinks it is looking at, and `LC_ALL=C grep -a` takes locale-driven encoding decisions out
of the result. Those exit codes are GNU grep 3.11 and binary handling differs between
implementations, so the positive control is the part that transfers everywhere: a zero-match result
that has not been paired with a known-present string is not evidence of absence.

### Clear the cache before reporting a post-deploy failure

Page caches, optimisation plugins and CDN edges serve HTML they built earlier, so a change that is
live at the origin can stay invisible from outside for minutes, hours, or the full TTL. A
verification run against a cached response measures the previous deploy. What you are describing is
real; it is simply the state of a document generated before the fix existed.

The wrong answer: *"the fix did not apply — the old meta description is still being served."* It
had applied. The origin was correct and the cache layer was serving a copy built before the save.
This one costs more than a wrong sentence, because the natural next step after a failed deploy is
to change the fix — which means editing working code against a false negative and shipping a second
change to repair a problem that never existed.

A post-deploy FAIL is unproven until the cache is excluded. Purge the page at the caching layer,
re-fetch, and confirm you are looking at a fresh response by reading the headers —
`curl -sS -o /dev/null -D - "$URL"` — a `GET` with the body discarded, for the reason the next rule
gives — and check `age`, `x-cache`, `cf-cache-status` or the equivalent, and re-run only when it
reports a miss. Where you cannot purge, a cache-busting parameter proves the origin state,
but read the query-string rule below first, because that parameter can change what the origin
returns. Compare origin and edge deliberately rather than assuming they agree, and say in the
finding which one you measured.

### Probe redirects with `GET`, not `HEAD`

Many CMS and application-layer redirects run inside request-handling code rather than in the web
server, and a good number of them are registered only for `GET`. A `HEAD` request skips that path,
falls through to the ordinary router, finds nothing at the URL, and returns 404. The redirect is
working. The probe used a method the redirect does not answer.

The wrong answer: *"the old URL 404s — the redirect was never created."* `curl -I` returned
`HTTP/1.1 404`, which is about as unambiguous as a status line gets. A `GET` to the same URL
returned `301` with a correct `Location`. The audit filed the redirect as missing, someone created
a second rule for a URL that already had one, and the duplicate then had to be tracked down and
removed.

Probe with `GET` and throw the body away: `curl -sS -o /dev/null -D - -L "$URL"` prints every
response header in the chain and follows each hop. Adding `-w '%{http_code} %{url_effective}\n'`
gives the final status and final URL on one line. Never conclude anything about a redirect from
`curl -I` alone — if you used `HEAD`, the only claim you have earned is a claim about `HEAD`.

### Check the `Location` header and the final URL, not that a page rendered

A catch-all handler — a soft 404, a "did you mean" page, a theme-level fallback that sends every
unmatched path to the homepage — makes a missing redirect look like a working one. The browser goes
somewhere, renders something, and returns 200. The visual result is a functioning page. What
actually happened is that the request failed and the failure was styled. A check that stops at "the
page loaded" cannot tell a correct destination from a catch-all.

The wrong answer: *"all fifteen legacy URLs redirect correctly — every one resolves and returns
200."* Nine of them resolved to the homepage, because the site sends every unmatched path there.
Each one passed the test that was run, which was *does a page appear*; the test that mattered,
*does this URL reach the page it was mapped to*, was never run. Every 200 in that report was true,
and none of them meant what the report said they meant.

Assert the destination, not the outcome. For each mapped URL, record the intended target and
run two probes. Without `-L`,
`curl -sS -o /dev/null -w '%{http_code} %{redirect_url}\n' "$URL"` gives the status and the
immediate `Location`; with it,
`curl -sS -o /dev/null -w '%{http_code} %{url_effective}\n' -L "$URL"` gives the final destination
after every hop. (`%{redirect_url}` is empty once `-L` has followed the chain, which is why both
probes are needed.) The final effective URL must equal the intended target character for
character, and a homepage result is a failure whatever the status code says. Establish the site's
baseline first by requesting a path you know does not exist, something like
`/this-path-does-not-exist-9f3a`; whatever comes back is what a miss looks like on this site, and
any mapped URL returning the same thing has not redirected. Soft
404s need one more step, a comparison of the rendered content, because they return 200 by design.

### Test schema against the canonical URL with no query string appended

Some caching, optimisation and edge configurations change the response when a query string is
present: a different cached variant, a bypass path with different processing, or an optimisation
layer that strips or reorders injected markup. Structured data is a frequent casualty — a JSON-LD
block a plugin injects into the normal response can be absent from the `?param=` variant. The URL
you tested is then not the URL a crawler sees.

The wrong answer: *"the page has no FAQ schema."* It had one. The check had been run against the
URL with a cache-busting parameter appended — added, in that instance, to satisfy the cache rule
above — and that variant did not carry the injected block. Two rules here pull in opposite
directions, which is exactly why this one has to be written down: the parameter that guarantees a
fresh response can also guarantee a different one.

Run schema and markup-presence checks against the exact canonical URL, unmodified. Where a fresh
response is also required, purge the cache instead of appending a parameter and prove freshness
from the response headers. Where you suspect a difference, measure it rather than assuming:
count the blocks in each form with
`curl -s "$URL" | grep -ao 'application/ld+json' | wc -l` and the same command against the same
URL with a cache-busting parameter appended — `?cb=1`, or `&cb=1` if the URL already carries a
query string, since the wrong separator produces a different page rather than an error — pipe to
`wc -l` rather than using `grep -c`, whose behaviour with `-o` differs
between grep implementations (some count occurrences, some count matching lines), which silently
undercounts on minified HTML where several blocks share one line. If the counts differ, the clean
URL is the one your finding is about. Confirm the result in a validator that fetches the URL
itself rather than one that accepts your local copy.

### Prove a link is contextual by checking an unrelated page first

An internal link inside a header, footer, sidebar, related-posts block or any other template region
appears in a page's rendered HTML and is indistinguishable, from one fetch, from a link an author
placed inside body copy. The two are worth very different amounts. A contextual link is an
editorial signal about this specific page. A template link is site furniture that exists on every
URL and therefore says nothing about any of them.

The wrong answer: *"the service pages are well interlinked — each one links to three others."* The
three links were a navigation block present on all 240 URLs on the site. The count was accurate,
the pages did link to each other, and the finding recommended nothing worth doing, because the
structure it described was already universal and could not be improved by adding what was already
everywhere.

Fetch a page with no topical relationship to the link — an imprint, a privacy policy, an unrelated
blog post — and search it for the same `href`. If the link is there too, it is template. Then
confirm position rather than mere presence: extract only the `<main>`, `<article>` or body-content
container and re-run the search inside it, so the number you report is scoped to editorial content.
State that scope in the finding — "three contextual links inside the article body, excluding
navigation and footer" — so the number cannot be misread by the next person.

### Enumerate the whole set and de-duplicate before stating any number

Every count in an audit is a claim about a complete set, and a count taken from a partial view is
wrong in a way that is invisible from inside the count. A filename heuristic, a pattern that
matches most of the items, a visual tally from a screenshot, a figure carried forward from an
earlier document — each returns a number that looks like the answer. The rule has two mandatory
steps: enumerate every candidate without filtering, then de-duplicate to the entity you are
actually counting, and say which of the two numbers you are reporting.

This one has a measured history. Three separate counts of the client logos on a single page came in
at 19, 19 and 21, produced independently and confidently, and all three were wrong. The correct
answer is 22 logo elements resolving to 20 distinct companies, because two companies each loaded
twice from different filenames. The 19s came from a filename heuristic that only matched paths
containing the word "logo"; the 21 came from an internal document. Nobody was careless. Every wrong
number came from a method that inspected part of the set, and confidence does not distinguish that
from a method that inspected all of it.

Enumerate from the rendered DOM in a real browser, never by eye and never with a filter in the
first pass. Resist the regex: a pattern like `<img[^>]*>` over fetched markup is not the candidate
set and will quietly return a fraction of it. HTML tag names are case-insensitive, so an
upper-case tag is missed without `-i`; `grep` is line-oriented and cannot match a tag whose
attributes are wrapped across lines, which most page builders do; and `<picture>`/`<source>`, CSS
`background-image`, inline `<svg>` and lazy-loading attributes such as `data-src` all put visible
imagery on a page without an `<img>` tag the pattern can see. Query the live DOM for every element
type that can render one, collect each resolved URL, count the raw total, then de-duplicate on the
identity that actually matters, because the same asset routinely appears under several filenames.
Report both figures with the method beside them: "22 elements resolving to 20 distinct companies,
enumerated from the rendered DOM on 2026-09-07, de-duplicated by company", not "20 logos". If you
automate the count, run the script first against a fixture whose true content you know — the same
positive control the binary-`grep` rule asks for — because a counting script that undercounts exits
0 and is indistinguishable from a correct one. Where the full set cannot be enumerated, state no
number at all: a range with its boundary named is honest, and a precise wrong number is not.

### Treat a front-end scan as a floor, not an inventory

What is detectable from outside a site is the subset of installed software that leaves a
fingerprint in the rendered output of the URLs you happened to load. Anything deactivated,
admin-only, conditionally loaded, scoped to templates you did not visit, or bundled and minified
into a single asset by an optimisation layer is invisible. A front-end scan gives a lower bound on
what exists and no upper bound at all.

The wrong answer: *"the site runs eleven plugins."* The admin screen listed thirty-four, nine of
them with updates pending and two deactivated but still present on disk. The eleven were correct as
far as they went — each really was installed — and the sentence was read as an inventory, which
then carried a maintenance estimate and a security assessment built on a third of the real surface.
Pending updates in particular never show up in a front-end fingerprint, and they are usually the
reason someone asked the question.

For anything phrased as *what is installed*, *how many*, or *which version*, the source of truth is
the CMS admin: the plugins or extensions screen, the updates screen, the theme list. Where you have
admin access, take the inventory there and use the front-end scan only as a cross-check. Where you
do not, say so inside the finding — "detected from the front end; this is a floor, not an
inventory, and pending updates are not visible this way" — and put the real question under "Could
not check" with the access request attached. A fingerprint list published without that caveat will
be read as complete, whatever you meant by it.

## What this means for the report

Every rule above has the same shape: a method that returns an answer, and a condition under which
that answer is confidently wrong. So the useful output of this file is not a longer checklist. It
is the ability to hold three states apart — *checked and fine*, *checked and broken*, and *not
checked* — and to keep the third one visible in the report instead of letting it dissolve into the
second.

**The operative rule: a check that could not be performed goes under "Could not check", with the
reason, and never under "Not a problem".**

"Not a problem" is an assertion that something was examined and found sound. It carries the same
weight on the page as "Fix now" and is read with the same trust. Moving an unperformed check into
it converts an absence of evidence into a statement of health, and does so silently, because
nothing in the report distinguishes a line that was verified from a line that was assumed. That is
how an audit launders a gap into a clean bill of health. Nobody lies, the item is never revisited
because it has already been cleared, and the check that was never run is the one that fails later
with the audit on record saying it was fine.

The boundary is worth stating plainly, because it is the one people negotiate with themselves
about. **If a rule above applies to a check and the rule was not applied, that check did not
happen.** A schema test run against a query-string URL, a redirect test run with `HEAD`, a tag
audit run before consent, a plugin count taken from the front end, a page fact taken from a
document — each of these produced output, and the output is not a result. There are exactly two
honest options: move it to "Could not check" with the reason, or go back and run it properly. The
second is usually faster than writing the caveat.

**The same discipline points back at your own instruments. When a check fails on something you
have good reason to believe is correct, interrogate the check before you change the work.** Every
rule above describes a method that returns a confident wrong answer, and a linter, a validator, a
CI gate or a search pattern is a method like any other — it can fire on the wrong thing just as
readily as it can stay silent on the right one. Reproduce the failure, isolate which part of the
check actually fired, and print what it matched, before touching anything the check is complaining
about. This is not permission to argue with a red result, because most failing checks are right.
It is about the asymmetry in what the two mistakes cost: ignoring a true failure leaves a defect
that the next run catches again, while silencing a false one edits finished work to satisfy an
instrument, and that edit ships and is never revisited.

This file exists partly because of a live instance. A guard scanning this repository for client
names was built from unanchored substrings, one of which was a fragment of an ordinary English word
used throughout a finished file. The gate fired, the writing was correct, and the fastest way to
get a green result was to rename the concept — so the work was changed to satisfy a broken check,
which nobody noticed until someone asked which pattern had matched and on what. Isolate first: run
each pattern separately, print the matched text rather than the matching line, and fix the check
when the check is what is wrong. A gate that cannot be questioned has stopped being a gate and
started being an author.

"Could not check" entries are not an apology and not padding. They are often the most actionable
part of the report, because each one names something the client can unblock. Write each with three
things: what you were trying to determine, what specifically stopped you (no admin access, consent
could not be given, a cache you cannot purge, a URL behind authentication), and what would let it
be checked — usually a credential, a permission, or ten minutes with someone who holds one. Written
that way an entry converts into a request. Written as "unable to verify" it converts into nothing.

An audit is a credibility instrument before it is a technical one, and the findings that make it
trustworthy are the ones where you say what you did not do. A report with eight findings and four
honest gaps is worth more than a report with twelve findings, four of which were never checked. The
first can be acted on line by line. The second has to be re-verified from scratch the moment any
single item turns out to be wrong.
