# The /cro page procedure

This is the procedure `/cro page` follows. It writes the plugin's folder as `${CLAUDE_PLUGIN_ROOT}` and its data folder as `${CLAUDE_PLUGIN_DATA}`. The shell sets neither one, so put the full paths the `cro` skill gave you in their place in every command you run and every file you read. Any argument that can hold a space, such as the deck's file name, goes in double quotes. Work through the twelve steps in order. The output is the page's copy deck, `<project folder>/<Page> — Copy Deck — <YYYY-MM-DD>.md`, in the project folder, else wherever the project keeps copy: one page, every section in the page's order, the hero with its three variants.

1. Read the Conversion Brief, where `audience-research` saves it: its Page modes and keywords, Traffic and awareness, Register, Objections, Proof available and Visual inventory sections. With no brief, write nothing: say that `/cro research` writes one, because the FAQ, the proof and the register all come from it. Ask once, in one message, for whatever the brief lacks, in this order: the mode (Search or Direct); then the traffic source, where the visitors come from; then the awareness (cold or warm), an answer separate from the mode, since a Direct page can have warm visitors. Then ask for the page role (homepage, service or landing), the register, the language and the one action the page asks for. On a Search page take the keyword and its spelling variants from the brief, which the plugin never picks. The answers become the deck's page keys, in the values step 1 of `${CLAUDE_PLUGIN_ROOT}/skills/cro/references/hero.md` gives.
2. Pick the skeleton by awareness, as "Skeleton by awareness" in `${CLAUDE_PLUGIN_ROOT}/skills/conversion-page-build/references/page-architecture.md` says. Cold, problem-aware visitors get the image or video hero, and pain comes before proof. Warm, solution-aware visitors get the form hero, and proof comes before pain. The skeleton follows the awareness and never the mode. `${CLAUDE_PLUGIN_ROOT}/skills/conversion-page-build/references/page-types.md` describes all four in "The four skeletons"; the two e-commerce ones are described and never scored. Then take the order from "The long-form order" in page-architecture.md: all eleven deck sections, cold as its table gives them, warm with the proof section written before the pain section. A page type that keeps fewer sections drops them as page-types.md says, and never drops the hero, the FAQ or the closer.
3. Write the hero through `${CLAUDE_PLUGIN_ROOT}/skills/cro/references/hero.md`: follow its steps 2 to 7 with the answers step 1 gathered, so nothing is asked twice. Its step 8 holds the form of the page, meta, cta and hero keys, which step 9 here writes into the deck. Its check and its voice pass run once for the whole deck, at steps 10 and 11 here. When the deck already holds a hero, as `/cro hero` writes one, keep it and its labels and write the other sections around it.
4. Write each section through its playbooks. The "Playbooks that write it" cell of the section's row in the order table names them, and they live in `${CLAUDE_PLUGIN_ROOT}/skills/conversion-page-build/references/section-playbooks.md`. Write each one in the two passes of the `conversion-page-build` skill: first what the section must accomplish, then the register row for the brief's register. The header holds the logo, the button and, where the business takes calls, a phone number. A homepage or service page also keeps its menu in the `nav` key. A landing page's header has no menu, so no link on it leads off the page. Never walk the older list of eleven sections in the `conversion-page-build` SKILL.md: it names sections the deck does not have.
5. Repeat the one action, as "Repeating the action" in section-playbooks.md says. The hero and the closer always carry the button, and no two sections in a row go without it, the header aside, so a visitor is never more than one section away from the button. Every repeat holds the label of `cta.button` in its `<ns>.<section>.cta` key, and a tested variant's page shows that variant's own label. On every page every button leads to the same place, and on a page with a form that place is the form. The doubt reducers in `cta.fud` and the proof sit beside each repeat, as `proof-library.md` says under "Where proof goes".
6. Give each section its visual, as "A visual for every section" says: every section names its visual, the real product, the real outcome or the real people, never stock, taken from the brief's Visual inventory. Every section but the header and the FAQ carries a `visual` line. A section that reads better as plain text writes `none` and the reason. A visual nobody can supply is written `[NEEDED: <the shot>]` and reported to the user.
7. Write the closer as a mini hero, as "Closer" says: a benefit headline, three to five bullets of what the buyer gets, stacked proof, the doubt reducers and the button or the form. It adds no new argument. Urgency comes only from real reasons. A register that changes that rule gets a register line in step 9.
8. On a Search page, place the keyword as the six placements in `${CLAUDE_PLUGIN_ROOT}/skills/cro/references/modes.md` say. The hero's H1, its `answer` key, which holds the answer-first sentence, and the meta keys come from step 3. Here, one or two H2s carry the keyword, and the other headings use its variants and cluster terms naturally. On every page, write the FAQ from the brief's real Objections that the page has not already answered, as `faq.q1` with `faq.a1`, then `faq.q2` with `faq.a2`, numbered from 1 without gaps. The deck has no schema key. The page is marked up as FAQPage schema where the platform supports it, and the schema repeats these pairs word for word, so it matches the visible text.
9. Write the deck, at the path in the note above. The page is one `## <ns>: <Title>` section holding one `copy` fence: a second fence under the same heading is a syntax error. After the fence, at the left margin, comes `## Register notes`, with one line for each rule the register changed anywhere on the page, in the form `- <rule>: <what changed>, because <why>.`, or the one line `- None: the register changed no rule.` Inside the fence go the page, meta and cta keys and the hero keys in the form of step 8 of hero.md, which is not repeated here, then the header keys between the cta keys and the hero keys, then every other section in the order step 2 chose, because the check reads the order from each section's first key. This is the form of the keys hero.md does not show, with placeholders only. A line in angle brackets stands for the keys step 8 of hero.md shows.

   ````
   ## <ns>: <Title>

   ```copy
   <the page, meta and cta keys, in the form of step 8 of hero.md>
   <ns>.header.logo: <the logo>
   <ns>.header.cta: <the same label as cta.button>
   <ns>.header.phone: <a phone number, optional>
   <ns>.header.nav: <menu link labels separated by semicolons, homepage or service page only>
   <the hero keys, in the form of step 8 of hero.md>
   <ns>.pain.h2: <heading>
   <ns>.pain.body: <the section's prose>
   <ns>.pain.visual: <what it shows, then why>
   <ns>.pain.cta: <the same label as cta.button>
   <ns>.proof.h2: <heading>
   <ns>.proof.quote1: <a quote the brief clears>
   <ns>.proof.quote1.who: <who said it>
   <ns>.proof.body: <the other proof the brief clears, several kinds stacked together>
   <ns>.proof.visual: <what it shows, then why>
   <ns>.proof.cta: <the same label as cta.button>
   <ns>.value.h2: <heading>
   <ns>.value.block1: <a value block>
   <ns>.value.block8: <the last value block, four to eight in all>
   <ns>.value.visual: <what it shows, then why>
   <ns>.value.cta: <the same label as cta.button>
   <ns>.compare.h2: <heading>
   <ns>.compare.body: <the section's prose>
   <ns>.compare.visual: <what it shows, then why>
   <ns>.how.h2: <heading>
   <ns>.how.step1: <a step>
   <ns>.how.step4: <the last step, three or four in all>
   <ns>.how.visual: <what it shows, then why>
   <ns>.how.cta: <the same label as cta.button>
   <ns>.team.h2: <heading>
   <ns>.team.body: <the section's prose>
   <ns>.team.visual: <what it shows, then why>
   <ns>.team.cta: <the same label as cta.button>
   <ns>.guarantee.h2: <heading>
   <ns>.guarantee.body: <the section's prose>
   <ns>.guarantee.visual: <what it shows, then why>
   <ns>.guarantee.cta: <the same label as cta.button>
   <ns>.faq.h2: <heading>
   <ns>.faq.q1: <a real objection, as a question>
   <ns>.faq.a1: <its answer>
   <ns>.closer.h2: <a benefit headline>
   <ns>.closer.bullet1: <what the buyer gets>
   <ns>.closer.bullet5: <the last bullet, three to five in all>
   <ns>.closer.proof: <stacked proof>
   <ns>.closer.cta: <the same label as cta.button>
   <ns>.closer.visual: <what it shows, then why>
   <ns>.<section>.<slot>: [NEEDED: <what is missing>]
   ```

   ## Register notes

   - <rule>: <what changed>, because <why>.
   - None: the register changed no rule.
   ````

   A section that repeats the button carries its `cta` line and the closer always does, so add or drop the `cta` lines the skeleton shows as step 5 needs. Each further quote the brief clears adds a numbered `quote` and `who` pair after `quote1`, and the quotes and the proof `body` together stack the proof. A warm page writes the proof keys before the pain keys.
10. Run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/deck_check.py "<deck>"` and fix every FAIL. Report each WARN to the user. An open gap stays a gap and is never filled to quiet the check.
11. Route the whole deck's text through `humanizer` when it is installed, else through `${CLAUDE_PLUGIN_ROOT}/skills/copy-sweeps/references/banned-vocabulary.md`, as step 10 of hero.md does. The voice pass keeps the keys, the gaps and the form of the register lines. German copy is flagged for the user's own check. Then run step 10's check once more and fix any new FAIL.
12. Offer `/nca-conversion:cro sweep` as the edit pass.
