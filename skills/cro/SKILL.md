---
name: cro
description: "Use when the user types /nca-conversion:cro, asks to audit or score a landing page or homepage, says 'audit this page', 'CRO audit' or 'conversion audit', or starts a landing page or site project and wants the conversion process."
license: MIT
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/setup.py *) Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/doctor.py *) Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/conversion-page-audit/scripts/page_facts.py *) Bash(${CLAUDE_PLUGIN_DATA}/venv/bin/python ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/render_check.py *) Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/speed_check.py *) Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/score.py *) Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/search_check.py *) Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/client_check.py *)
metadata:
  version: 0.2.1
---

# cro

The command word is `$0`. It is empty when nothing follows `/nca-conversion:cro`. The whole argument line is `$ARGUMENTS`, command word included.

## Route

- No argument: read `references/kickoff.md` and follow it.
- A word in the table: go where its row says. A reference file is read and followed. A skill row invokes that skill of this plugin with the remaining arguments.
- A "not built yet" row: say so and name its slice.
- A "Later list" row: say it is on the Later list.
- Any other word: show the table.

| Command | Goes to | Status |
| --- | --- | --- |
| (none) | `references/kickoff.md` | ready |
| `audit <url>` | `references/audit.md` | ready |
| `setup` | `references/setup.md` | ready |
| `doctor` | `references/setup.md` | ready |
| `offer` | the `offer-architect` skill | ready (v1 skill) |
| `sweep` | the `copy-sweeps` skill | ready (v1 skill) |
| `research` | the `audience-research` skill | v1 engine until slice 2 |
| `page <brief>` | the `conversion-page-build` skill | v1 engine until slice 2 |
| `hero` | the `hook-lab` skill | v1 engine until slice 2 |
| `wireframe` | the `design-handoff` skill | v1 engine until slice 3 |
| `vsl` | nothing yet | not built yet, slice 2 |
| `design` | nothing yet | not built yet, slice 3 |
| `check` | nothing yet | not built yet, slice 3 |
| `form` | nothing yet | on the Later list |
| `data` | nothing yet | on the Later list |
| `compare` | nothing yet | on the Later list |
| `diagnose` | nothing yet | on the Later list |

Run setup and the health check with these two commands:

`python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/setup.py --data-dir ${CLAUDE_PLUGIN_DATA}`

`python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/doctor.py --data-dir ${CLAUDE_PLUGIN_DATA}`

Reference files write this plugin's folder as CLAUDE_PLUGIN_ROOT and its data folder as CLAUDE_PLUGIN_DATA, each inside a dollar sign and braces. The shell does not know those names: in every command you run and every file you read, put `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_DATA}` in their place.

## Rules

- Start no subagents. This skill only routes.
- Rendered evidence comes only from `render_check.py`, the one route that blocks analytics.
- Client-facing text follows `references/client-version.md`.
