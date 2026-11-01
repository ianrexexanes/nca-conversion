# Client version

This file sets the shape of the text a prospect or client reads. You write it after the internal report, from what that report found. It carries no score: the reader gets the leaks, the fixes and the facts measured on their own page.

## Format

Fill every placeholder from the audit. Keep the labels, their order and the three-leak summary. For `**Written by:**`, use the name the user gave for this report; if none was given, ask. Never take a name from the page, the conversation's context or memory.

```
**Site:** <domain>

**Checked:** <date>

**Pages read:** <paths on that domain>

**Method:** Public pages only. No logins, and no form was sent.

**Written by:** <name>

<Two or three sentences on what the page already does well.>

### <Title of the leak>

**What I saw**

<What is on the page, in plain words.>

**Why it costs leads**

<How this loses a visitor who was ready to act.>

**The fix**

<The change to make.>

**Effort**

<How long the fix takes and who does it.>

<Repeat the leak block once for each leak.>

## Summary

The three leaks that cost the most, in the order I would fix them.

1. <Title of the biggest leak>
2. <Title of the second leak>
3. <Title of the third leak>
```

## Rules

- No score and no factor table.
- No AI or tool names.
- No teacher names, Hormozi included.
- No citations.
- No industry statistics.
- Say only what was seen on the client's own page, the fix, and measured facts about that page with their date.
- Example: Google's PageSpeed Insights, run on October 13, 2026, scores the home page 55 out of 100 on a phone.

## Language

Write in the page's language. Translate the labels, the summary heading and its lead sentence into it. German text goes to Ian for his own check before it is sent. `client_check.py`'s cue words are English and German, so in any other language the writer reads the text for citations, statistics and words for AI themselves.

## Voice

Run the text through `humanizer` when it is installed, and through `ian-voice` for any covering message Ian sends himself. Without them, apply `${CLAUDE_PLUGIN_ROOT}/skills/copy-sweeps/references/banned-vocabulary.md`.

## The check

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/client_check.py <client file>
```

Run it, then fix every FAIL, read every WARN, and keep only measured facts about the client's own page. Exit code 1 means a FAIL is left. Exit code 2 means the file could not be read. Neither is a pass.
