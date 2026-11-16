# The design rules

These are the rules a wireframe and a design are checked against. `/cro wireframe` and `/cro design` apply them, `/cro check` measures what it can of them on the built page. Those commands point here and do not restate it.

A Search page is one whose visitors arrive from organic search for a keyword. A Direct page is one whose visitors the owner sends: paid ads, cold outreach, email. This is not the analytics channel of the same name, which means typed addresses and bookmarks.

## The six rules

1. **The headline is three to four times the body size.** The size gap tells the eye where to start. The ratio is a rule of this plugin, not a measured fact, so a design that misses it is told so as a warning, and the design system supplies the actual sizes.
2. **Body text is dark grey, not black.** Softer body text sets the bold headline apart from it. The grey still has to clear the contrast thresholds below.
3. **The hero has a directional cue toward the button or the form.** A person in the picture looking toward it, or a shape drawn from the brand that points to it. Where the picture has no person, use the shape.
4. **The main visual carries the emotional, social and functional reasons to buy.** Show how the buyer feels once it works, who else uses it, and what it does. A generic stock photo carries none of the three, and neither does an invented picture of a customer.
5. **The page has no carousels.** Reviews and benefits sit on the page in a grid or a list, where every item can be seen without a click or a swipe.
6. **Use tight hero padding on a phone.** The headline, the answer and the button all fit in the first phone screen. The phone layout is its own single column, not a shrunk desktop layout, and its headline is set smaller than the desktop one.

## Measured thresholds

These are the only measured rules in this file. They come from the Web Content Accessibility Guidelines 2.2, https://www.w3.org/TR/WCAG22/, a W3C Recommendation dated 12 December 2024, read on 2026-11-07. Everything else here is a rule of this plugin.

| Success criterion | Level | What it asks |
| --- | --- | --- |
| 1.4.3 Contrast (Minimum) | AA | Text against its background at least 4.5:1; large text at least 3:1. |
| 1.4.11 Non-text Contrast | AA | A control, or the part of a graphic needed to understand it, against its surroundings at least 3:1. |
| 2.5.8 Target Size (Minimum) | AA | A tap or click target at least 24 by 24 CSS pixels. |
| 2.5.5 Target Size (Enhanced) | AAA | A target at least 44 by 44 CSS pixels. Recommended here, not required. |

## What design never does

Design earns its place on a conversion page. It makes the page credible, familiar and clean. Motion appears only where it has a job, such as showing how an input becomes a result. The page never uses:

- award-chasing layouts, built to impress other designers instead of the visitor
- scroll-jacking, which takes the page's scroll away from the visitor
- preloaders, which make the visitor wait to see anything
- sliders, in the hero or anywhere else
- autoplaying background video

`/cro check` reports sliders and autoplaying video; the rest of this list is a design-time rule, which the optional motion review in `/cro check` also reads. `/cro design` guards the blur test on the main button, contrast, hierarchy and standard navigation.

## Design skills, by mode

The design skills disagree with each other, so one ladder decides. The top rung wins. Each row says what its rung decides, and then how that works on a Direct page and on a Search page. A skill that is not installed is skipped, and the output says it was skipped.

| Rung | What it decides | On a Direct page | On a Search page |
| --- | --- | --- | --- |
| 1. WCAG 2.2 and the safety rules | The thresholds above, plus: analytics and tags are blocked on the page the plugin's own renders and checks test, so a test never lands in its data, and no form is sent without the owner's yes. | Never departed from. | Never departed from. |
| 2. The conversion rules | The method, the hero and page rules, and the mode's own rules. They win wherever they meet a design skill; each departure is a ruling line. | The hero may run long, with three to five stacked benefit lines, doubt reducers and two kinds of proof. No keyword placement. | The keyword sits in the H1 near the front, with the promise. The rest of the hero stays short. The line-width rules still hold. |
| 3. Impeccable, the design authority | Direction, craft floor and refusals. They hold unless a conversion rule needs the element. | The line above the H1 (`prooftop`) is the standing departure from its eyebrow ban; see Rulings. | `prooftop` sits under the H1 block, so the eyebrow ban holds. A small keyword H1 above a big headline is a written exception. |
| 4. Hallmark | The Floor, as design rules. Its audit is a review the user runs by name. Its word, section and hero caps never apply to a conversion page. | Where the Floor meets a conversion rule, the conversion rule wins, and the departure is the user's ruling, written as a ruling line. | The Floor holds in full, as does the headline length ladder. Only the caps are set aside, because they would cut words. |
| 5. Taste, UI/UX Pro Max and frontend-design | Inputs for style and layout. | Used when they agree with the rungs above; they lose when they do not. | Same. Taste's eyebrow tags lose to Impeccable and Hallmark. |
| 6. Emil Kowalski's skills | A review of built code, in `/cro check` only, never on a wireframe or a design frame. | Motion only where it has a job. | Same. |

## Rulings

A departure from a design skill is written down as a ruling line, in this form:

- <skill> <rule>: <what this page does instead>, because <conversion rule>; mode <search or direct>.

Hallmark's Floor allows no waiver, so a departure from it is the user's ruling and not a Hallmark waiver. Every FAIL that Hallmark's lint reports is matched to a ruling line or fixed. A lint run needs the design to exist as HTML.

Hallmark runs its audit only when the user names it, so the design step does not run it. It hands the user one line, `/hallmark:hallmark audit <file>`, and says that line is waiting.

The standing pair of lines for the Direct page's `prooftop`. Every Direct page that uses the slot carries both. The slot holds an audience call-out or the strongest proof. It is set above the H1 in the body face, in sentence case and untracked, never as a pill or in tracked capitals.

- Impeccable eyebrow ban: the line above the H1 stays, set in the body face, sentence case and untracked, because the four-question hero must tell the visitor at once who the page is for or why to believe it, and with an audience call-out the proof strip under the button carries two kinds of proof; mode direct.
- Hallmark Floor rule on eyebrows: the same line stays, in the same form, because the visitor's first question is whether the page is for them, and the line answers it before the headline does; mode direct.
