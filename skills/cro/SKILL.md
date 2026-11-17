---
name: cro
description: "Use when the user types /nca-conversion:cro, asks to audit or score a landing page or homepage, says 'audit this page', 'review my landing page', 'CRO audit', 'conversion audit' or 'why isn't this converting', or starts a landing page or site project and wants the conversion process: research, page copy, a hero or a hero video script."
license: MIT
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/setup.py *) Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/doctor.py *) Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/conversion-page-audit/scripts/page_facts.py *) Bash(${CLAUDE_PLUGIN_DATA}/venv/bin/python ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/render_check.py *) Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/speed_check.py *) Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/score.py *) Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/search_check.py *) Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/client_check.py *) Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/deck_check.py *) Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/wire_check.py *) Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/design_check.py *) Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/site_check.py *) Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/asset_text_check.py *) Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/redirect_check.py *) Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/clarity_export.py *) Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/compare.py *) Bash(${CLAUDE_PLUGIN_DATA}/venv/bin/python ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/launch_render.py *) Bash(${CLAUDE_PLUGIN_DATA}/venv/bin/python ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/form_check.py *)
metadata:
  version: 0.4.1
---

# cro

The command word is `$0`. It is empty when nothing follows `/nca-conversion:cro`. The whole argument line is `$ARGUMENTS`, command word included.

## Route

- No argument: read `references/kickoff.md` and follow it.
- A word in the table: go where its row says. A reference file is read and followed. A skill row invokes that skill of this plugin with the remaining arguments. A row that names a reference file and a skill: read and follow the reference file; its steps say when to use the skill.
- Any other word: show the table.

| Command | Goes to | Status |
| --- | --- | --- |
| (none) | `references/kickoff.md` | ready |
| `audit <url>` | `references/audit.md` | ready |
| `setup` | `references/setup.md` | ready |
| `doctor` | `references/setup.md` | ready |
| `offer` | the `offer-architect` skill | ready (v1 skill) |
| `sweep` | the `copy-sweeps` skill | ready (v1 skill) |
| `research` | `references/research.md`, with the `audience-research` skill | ready |
| `page <brief>` | `references/page.md`, with the `conversion-page-build` skill | ready |
| `hero` | `references/hero.md`, with the `hook-lab` skill | ready |
| `wireframe` | `references/wireframe.md`, with the `design-handoff` skill | ready |
| `vsl` | `references/vsl.md` | ready |
| `design` | `references/design.md` | ready |
| `check` | `references/check.md` | ready |
| `form` | `references/form.md` | ready |
| `data` | `references/data.md` | ready |
| `compare` | `references/compare.md` | ready |
| `diagnose` | `references/diagnose.md` | ready |

Run setup and the health check with these two commands:

`python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/setup.py --data-dir ${CLAUDE_PLUGIN_DATA}`

`python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/doctor.py --data-dir ${CLAUDE_PLUGIN_DATA}`

Reference files write this plugin's folder as CLAUDE_PLUGIN_ROOT and its data folder as CLAUDE_PLUGIN_DATA, each inside a dollar sign and braces. The shell does not know those names: in every command you run and every file you read, put `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_DATA}` in their place.

## Rules

- Start no subagents. This skill only routes.
- Run `setup.py` only when the user typed `setup`. In any other command, report that the runtime is missing, say to run `/cro setup`, and stop.
- Rendered evidence comes only from the plugin's guarded routes, which share the analytics guard in `cro_runtime.py`.
- Client-facing text follows `references/client-version.md`.
