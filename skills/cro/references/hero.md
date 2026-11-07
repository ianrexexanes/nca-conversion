# The /cro hero procedure

This is the procedure `/cro hero` follows. It writes the plugin's folder as `${CLAUDE_PLUGIN_ROOT}` and its data folder as `${CLAUDE_PLUGIN_DATA}`. The shell sets neither one, so put the full paths the `cro` skill gave you in their place in every command you run and every file you read. Any argument that can hold a space, such as the deck's file name, goes in double quotes. Work through the steps in order. The output is the hero section of the page's copy deck, `<project folder>/<Page> — Copy Deck — <YYYY-MM-DD>.md`, in the project folder, else wherever the project keeps copy: three variants, a, b and c, each with its own button label. With no deck yet, the output is a new deck holding the page, meta, cta and hero keys.

1. Read the Conversion Brief, where `audience-research` saves it: its Page modes and keywords, Traffic and awareness, Register, Objections, Proof available and Visual inventory sections. Ask once, in one message, for whatever the brief lacks of these: the mode (Search or Direct), the page role (homepage, service or landing), the traffic source, the awareness (cold or warm), the register, the language, and the one action the page asks for. Ask for the brief's Proof available section too when it has none. With no brief, ask for all of them and say that `/cro research` writes one. The answers become the deck's page keys: `search` or `direct`; `homepage`, `service` or `landing`; `cold-outreach`, `ads`, `search`, `email` or `mixed`; `cold` or `warm`; a register name; a language code such as `en` or `de-CH`. On a Search page also take the keyword and its spelling variants, which the plugin never picks.
2. Pick the hero type by awareness, as the "By awareness" section of `${CLAUDE_PLUGIN_ROOT}/skills/hook-lab/references/hero-build.md` says. Cold, problem-aware visitors get an image or video hero, followed by the pain section. Warm, solution-aware visitors get a form hero. The offer in the button follows the temperature. The deck has no slot for the type, so the visual brief (step 6) opens with it: `Form hero:`, `Image hero:` or `Video hero:`. Never invent a key for it.
3. Build three variants, a, b and c, with `${CLAUDE_PLUGIN_ROOT}/skills/hook-lab/references/hero-build.md`. Variant a leads with transformation. Variants b and c each take another hook type from `${CLAUDE_PLUGIN_ROOT}/skills/hook-lab/references/hook-taxonomy.md`: they change the hook type and never the structure, which is the headline build in hero-build.md (the end result with a figure the brief supports, the time it takes, the feeling). When the brief's Objections record one fear that stops the click, variant c uses the second build there instead: the same end result and time, ending "without" that objection in the buyer's own words. Transformation follows the register: the index in hook-taxonomy.md says what it becomes (a measurement pair in Technical / industrial, the system's change in Mission / nonprofit), and that change is a register line (step 7). The variants share the other hero slots; a slot that has to change to fit its headline takes the lettered key. By mode, as hero-build.md's "By mode" says. On a Search page each variant's H1 carries the keyword near the front with the promise, and the hero carries `answer`, the first sentence after the H1, which answers first and names the business and the keyword (the placements are in `${CLAUDE_PLUGIN_ROOT}/skills/cro/references/modes.md`). Then `meta.title`, `meta.description` and `meta.slug` carry the keyword too, with no slug on a homepage, and there are no benefit lines. On a Direct page the hero can carry up to five benefit lines, and the headline continues the ad or message that earned the click. A headline whose figure the brief does not support keeps its build and holds `[NEEDED: <the figure and what would close it>]` where the figure goes. In the deck every gap is written that way, never as the `NOT ESTABLISHED` marker the brief and hero-build.md use.
4. Fill `prooftop` and the strip from the brief's Proof available table. An item goes in only when its May be shown cell clears it, at the place its Where it goes cell names; an item that is not cleared stays out. The strip carries a different kind of proof from `prooftop`, and `prooftop` sits where hero-build.md puts it for the page's mode. A slot with nothing cleared holds `[NEEDED: <what the brief must supply>]` and is reported to the user. The rule is to never invent proof: no rating, count, name, logo or quote that the brief does not hold.
5. Write the button as the "The button" section of hero-build.md says. The default label goes in `cta.button`. Each variant gets its own label in `cta.hook.<v>` (`cta.hook.a`, `cta.hook.b`, `cta.hook.c`) that completes its own headline and passes the "so what" test: the reader can tell what happens at the click. `cta.fud` holds the doubt reducers and names the commitment point, so every variant describes the same click. Each variant's `<ns>.hero.<v>.cta` holds that variant's own label.
6. Write the visual brief: the real product or outcome, never stock, taken from the brief's Visual inventory. Open it with the hero type from step 2. When the inventory lists no image for the hero, the visual brief still describes the real product or outcome and marks the shot `[NEEDED: <the shot>]`.
7. Write the register notes, in the deck's `## Register notes` section, as hero-build.md's "Register notes" says: one line per rule the register changed, in the form `- <rule>: <what changed>, because <why>.`, or, when it changed none, the one line `- None: the register changed no rule.` The register's row in hero-build.md's translation table, and its section in `${CLAUDE_PLUGIN_ROOT}/skills/audience-research/references/register-profiles.md`, name what can change.
8. Write the hero into the deck. This is the form, with placeholders only:

   ````
   ## <ns>: <Title>

   ```copy
   <ns>.page.mode: <search or direct>
   <ns>.page.role: <homepage, service or landing>
   <ns>.page.traffic: <cold-outreach, ads, search, email or mixed>
   <ns>.page.awareness: <cold or warm>
   <ns>.page.register: <register name>
   <ns>.page.language: <language code>
   <ns>.page.keyword: <the keyword, Search pages only>
   <ns>.page.variants: <spelling variants separated by semicolons, Search pages only>
   <ns>.meta.title: <title>
   <ns>.meta.description: <description>
   <ns>.meta.slug: <slug>
   <ns>.cta.button: <default label>
   <ns>.cta.hook.a: <label that completes headline a>
   <ns>.cta.hook.b: <label that completes headline b>
   <ns>.cta.hook.c: <label that completes headline c>
   <ns>.cta.fud: <doubt reducers that name the commitment point>
   <ns>.hero.prooftop: <the first proof slot>
   <ns>.hero.a.h1: <headline a>
   <ns>.hero.b.h1: <headline b>
   <ns>.hero.c.h1: <headline c>
   <ns>.hero.sub: <subheadline>
   <ns>.hero.benefit1: <a benefit line, Direct pages only>
   <ns>.hero.answer: <the answer-first sentence, Search pages only>
   <ns>.hero.strip: <the proof strip under the button>
   <ns>.hero.visual: <hero type, then the visual brief>
   <ns>.hero.a.cta: <the same label as cta.hook.a>
   <ns>.hero.b.cta: <the same label as cta.hook.b>
   <ns>.hero.c.cta: <the same label as cta.hook.c>
   <ns>.hero.<slot>: [NEEDED: <what is missing>]
   ```

   ## Register notes

   - <rule>: <what changed>, because <why>.
   - None: the register changed no rule.
   ````

   Rules for the form. The heading is `## <ns>: <Title>`, with `<ns>` a short name of lowercase letters and digits. The section holds one fenced block, opened by a line that is exactly three backticks and `copy` and closed by a line of exactly three backticks. Each line in it is `<key>: <value>`: the key's parts are lowercase letters and digits joined by dots, and its first part is the section's `<ns>`. Shared hero slots (`sub`, `strip`, `prooftop`, `visual`, `answer`, the benefit lines) are written once as `<ns>.hero.<slot>`. A slot that differs by variant takes the lettered form, `<ns>.hero.<v>.<slot>`, which wins over the shared key for that variant; `h1` and `cta` are always lettered here. `## Register notes` is a `## ` line at the left margin, after the fence. On an existing deck, keep its page and meta keys, write the hero and cta keys, and when `cta.button` changes, change every `<ns>.<section>.cta` with it, because the page has one action. With no deck, write a new one at the path in the note above, holding the page, meta, cta and hero keys, then `## Register notes`.
9. Run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/deck_check.py "<deck>" --part hero` and fix every FAIL. Report each WARN to the user. An open gap stays a gap and is never filled to quiet the check.
10. Route the text through `humanizer` when it is installed, else through `${CLAUDE_PLUGIN_ROOT}/skills/copy-sweeps/references/banned-vocabulary.md`. The voice pass keeps the keys, the gaps and the form of the register lines. German copy is flagged for the user's own check. Then run step 9's check once more and fix any new FAIL.
