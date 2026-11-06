# Page modes: Search and Direct

Read this before asking what a page is for. The audit and the kickoff both start from the page's mode, because the mode decides what the first screen must do and whether a keyword is expected at all. Every page has exactly one mode.

## The two modes

A Search page gets its visitors from organic search, for a keyword the research shows the page can win. A Direct page gets the visitors its owner sends: paid ads, outreach, email.

The mode belongs to the page, not to the site and not to the page's role. A website can be Direct, and a landing page can be a Search page. "Direct" here has nothing to do with the Direct channel in GA4, which holds typed addresses and bookmarks.

## Keyword research comes first

Every SEO, web design or redesign project starts with keyword research, before any copy is written. When claude-seo is installed, the research runs through its DataForSEO route. Without it, the user brings their own research result. The plugin never picks a keyword.

A keyword the page can win makes it a Search page. No such keyword makes it a Direct page. Research runs once per language, and each language version is written natively, never translated from another.

The brief records, for each page, the keyword, its spelling variants, its monthly volume, its difficulty, the tool used and the date it was checked.

## The six placements

The exact keyword goes in six places: the title tag (near the front), the meta description, the URL slug, the H1, the first sentence after the H1, and one or two H2s. The first sentence answers first and names both the business and the keyword. For a made-up example: "Harbor Lane Cycles is a family workshop that offers bike repair for commuters and weekend riders."

A home page cannot carry the keyword in its address, so the URL placement is not applicable there. The same goes for the home page of a language folder such as `/en/`.

Named variants and hyphenated compounds count as the keyword, for example "Bike-Repair" or "bicycle repair". Matching is by whole words and ignores case. There is no stemming, so a plural or a closed form such as "Bikerepair" counts only when the brief names it as a variant.

"Near the front" is a writing rule. The check reports whether the keyword is in a placement, never where. Everywhere else, in the H2 to H4 headings and the body, variants, synonyms and cluster terms appear naturally. The Search check reports how many headings carry the keyword and never fails a page on that count. These heading counts cover the headings above the footer (a `<footer>` element or an element with `role="contentinfo"`), navigation included; on a page with no footer element they cover the whole page, and the result says so: "whole page (no footer element found)". The body uses leave the footer and navigation out.

On a service page, the FAQ and its FAQPage schema carry the content for answer engines, and the schema matches the visible text.

## How the audit judges the hero

On a Search page, the one big direct-response H1 carries the keyword near the front, together with the promise; a bare keyword scores low. The first screen matches the intent behind the keyword. The rest of the hero stays short: one subheadline, one button, doubt reducers and proof.

On a Direct page, the hero can run long, up to five lines of stacked benefits. The first screen matches the ad or message that sent the visitor. No keyword is expected, and its absence costs nothing.
