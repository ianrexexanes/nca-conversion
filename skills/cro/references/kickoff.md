# Kickoff: start a landing page or site project

This is what `/nca-conversion:cro` does when it gets no command. It asks the questions below in one message, records the answers, and points the project at the next command. It starts no subagents.

## The first questions

Ask all of these in one message. Skip any the user has already answered.

1. **Own site or client.** Is this the user's own site, or a client's?
2. **Page type.** A home page, a service page, a landing page, a full site?
3. **Mode.** Each page has one mode, Search or Direct. Read `${CLAUDE_PLUGIN_ROOT}/skills/cro/references/modes.md` before asking.
   - Search: visitors arrive from organic search for a researched keyword.
   - Direct: visitors the owner sends, such as paid ads, outreach or email. This is not GA4's Direct channel.

   Take the mode per page. A group of pages, such as all the service pages, may share one answer.
4. **Keyword research.** For a Search page: the keyword, its variants, its monthly volume, its difficulty, the tool used and the date it was checked, once per language.
5. **Offer state.** Is there an offer already, or does it still have to be built?
6. **Traffic source.** Cold outreach, ads or search?
7. **Language.** Which languages does the page need? Each is written natively, never translated.
8. **Deadline.** When does the page have to be live?
9. **Material on hand.** Existing copy, proof, testimonials, brand files, analytics.

For an existing site, also ask the one action the page must win, how visitors arrive, how the page performs in leads, and what happens next for visitors who are not ready.

**Keyword research comes before copy.** A Search project goes to keyword research before any copy is written. When claude-seo is installed, the route is its `seo-dataforseo` skill (the DataForSEO route), which gives keyword ideas, volume and difficulty. Otherwise the user brings their own research result. The plugin never picks a keyword.

The user decides whether a keyword can be won, from the volume, difficulty and current results the plugin presents. The plugin never decides.

Name the research step and the command to run, then wait for the result. The kickoff waits and starts no subagents. A page whose research is not done is recorded as "mode pending: keyword research", and no copy is written for it until its keyword is set.

## The build phases

If your project has its own build SOP, follow its phases. The plugin does not depend on any one SOP file. These are the plugin's own phases and the command each one maps to.

| Phase | Command | Slice 1 status |
| --- | --- | --- |
| 0. Decide | `/cro` with no command (this kickoff) | ready |
| 1. Research | `/cro research` | v1 engine until slice 2; a Search project opens it with keyword research |
| 2. Brief and offer | `/cro offer` | ready (v1 skill) |
| 3. Copy | `/cro page`, `/cro hero` | v1 engines until slice 2 |
| 4. Wireframe | `/cro wireframe` | v1 engine until slice 3 |
| 5. Style guide | `/cro design` | not built yet, slice 3 |
| 6. Design | `/cro design` | not built yet, slice 3 |
| 7. Build | none | outside the plugin |
| 8. Pre-launch | `/cro check` | not built yet, slice 3 |
| 9. Launch | none | outside the plugin |
| 10. After launch | `/cro audit` again | ready: quote both score lines for before and after |
