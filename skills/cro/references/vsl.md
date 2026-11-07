# The /cro vsl procedure

This is the procedure `/cro vsl` follows. It writes the plugin's folder as `${CLAUDE_PLUGIN_ROOT}` and its data folder as `${CLAUDE_PLUGIN_DATA}`. The shell sets neither one, so put the full paths the `cro` skill gave you in their place in every command you run and every file you read. Any argument that can hold a space, such as the deck's or the script's file name, goes in double quotes. Work through the nine steps in order. It reads the page's copy deck and writes the hero video's script, `<project folder>/<Page> — Hero Video Script — <YYYY-MM-DD>.md`, in the project folder, else wherever the project keeps copy.

1. Read the page's copy deck, in the form `${CLAUDE_PLUGIN_ROOT}/skills/cro/references/hero.md` writes it in its step 8, which `/cro page` writes the same way: the page keys (its language and register among them), `<ns>.cta.button`, `<ns>.cta.hook.<v>`, `<ns>.cta.fud`, and the hero's `prooftop`, `<v>.h1`, `sub`, `strip` and `visual`. A lettered slot wins over the shared one. Then read the Conversion Brief, where `audience-research` saves it: its Proof available and Visual inventory sections. The script follows one hero variant: the one the user names, else variant a. It is written in the deck's language and register. Three cases change the output. With no deck holding a hero, write no script and say that `/cro hero` writes one. With no video possible (nothing real to film yet, or nobody to film it), a graphic of the deliverable takes its place: say so, describe what that graphic shows (the deliverable step 3 names) for the hero's visual brief, write no script, and leave the deck as it is. With no Conversion Brief, the Proof part's rows are gaps (step 4), and say that `/cro research` writes one.
2. Name the script's parts first, in this order: the hook, the deliverable on screen, proof and the ask, then the shot list. Each of the four parts is a table of time, voice-over, on screen and caption, with one row per beat. The hook restates the headline's promise: the chosen variant's `h1`, said at the start.
3. The deliverable on screen is the exact deliverable the buyer receives: the real one, recorded from the product or the finished work, never stock. Take it from the brief's Visual inventory and the deck's hero visual brief. The voice-over says what the buyer gets while the screen shows it.
4. Write the proof from the brief only: the items its Proof available table clears in the May be shown cell, as step 4 of `hero.md` reads them, and a quote word for word, with who said it. Never invent proof: no rating, count, name, logo or quote the brief does not hold. A part with nothing cleared holds `[NEEDED: <what the brief must supply>]` and is reported to the user. In the script every gap is written that way, and the script never uses the marker the brief carries for an unconfirmed claim.
5. The ask is the page's one action: the chosen variant's label word for word (`cta.hook.<v>`, else `cta.button`), with the doubt reducers from `cta.fud`, pointing at the button beside the video, which leads where every button on the page leads. The video asks for nothing else.
6. The shot list names every capture to record: every thing an on-screen cell shows, numbered, with what it shows and the part that uses it. Each on-screen cell points at its shot by that number. A capture nobody can supply yet stays on the list as `[NEEDED: <the shot>]` and is reported to the user.
7. Playback is for whoever builds the page. The video plays on a click, never autoplay with sound, and carries captions, so a visitor with the sound off still follows it. A hero video shows the exact deliverable the buyer receives, plays on a click, and is only as strong as its script.
8. Write the script at the path in the note above. This is the form, with placeholders only:

   ````
   # <Page> — Hero Video Script

   Variant: <a, b or c>, under the headline <that variant's h1>
   Playback: plays on a click, never autoplay with sound, captions on.

   ## Hook

   | Time | Voice-over | On screen | Caption |
   | --- | --- | --- | --- |
   | <start>–<end> | <the voice-over> | <the shot, by its number> | <the caption> |

   ## The deliverable on screen

   | Time | Voice-over | On screen | Caption |
   | --- | --- | --- | --- |
   | <start>–<end> | <the voice-over> | <the shot, by its number> | <the caption> |

   ## Proof

   | Time | Voice-over | On screen | Caption |
   | --- | --- | --- | --- |
   | <start>–<end> | <the voice-over> | <the shot, by its number> | <the caption> |
   | <start>–<end> | [NEEDED: <what the brief must supply>] | [NEEDED: <the shot>] | [NEEDED: <the caption>] |

   ## The ask

   | Time | Voice-over | On screen | Caption |
   | --- | --- | --- | --- |
   | <start>–<end> | <the voice-over> | <the button beside the video> | <the button's label> |

   ## Shot list

   1. <the capture>: <what it shows>, used in <the part>.
   2. [NEEDED: <the shot>]: <what it would show>, used in <the part>.
   ````

   Rules for the form. The four parts and the shot list are the only `## ` lines, at the left margin, in this order. Each of the four parts holds one table whose header row is exactly the one above, with at least one row. In the script you write, each cell of a row holds real content: the time cell the beat's start and end, the voice-over cell the words spoken, the on-screen cell the shot by the shot list's number, and the caption cell the caption shown. A cell the brief cannot fill holds a `[NEEDED: <what is missing>]` gap, and the gap is reported to the user.
9. Route the script's voice-over and captions through `humanizer` when it is installed, else through `${CLAUDE_PLUGIN_ROOT}/skills/copy-sweeps/references/banned-vocabulary.md`. The voice pass keeps the headings, the tables, the gaps and the button's label word for word. German copy is flagged for the user's own check.
