# Setup and doctor

## What `/cro setup` changes

- One folder: `${CLAUDE_PLUGIN_DATA}/venv`.
- One pip package inside it, pinned: Playwright 1.62.0.
- Nothing in `~/.claude/skills/` or `~/.claude/agents/`.
- No browser download when Chrome is installed. Only if Chrome fails to launch does it fetch Playwright's own Chromium.

It is safe to run twice; the second run changes nothing.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/setup.py --data-dir ${CLAUDE_PLUGIN_DATA}
```

## What `/cro doctor` checks

It changes nothing. One line per check, `OK`, `WARN` or `MISSING`, then the detail.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/cro/scripts/doctor.py --data-dir ${CLAUDE_PLUGIN_DATA}
```

| Check | Looks at | Sets the exit code |
| --- | --- | --- |
| `python` | Python 3.10 or later | yes |
| `venv` | the folder `/cro setup` makes | yes |
| `playwright` | the installed version | yes |
| `browser` | `chrome <major>` or `chromium (bundled)` | yes |
| `pagespeed-key` | where the key comes from, never the key | no |
| `lighthouse` | `npx` is present | no |
| `companions` | which companion plugins are on | no |

Exit 0 when the first four are `OK`, else 1.

## The PageSpeed key

Optional. The key is yours; you create and store it, and it never goes into the chat.

1. Open the Google Cloud console.
2. Select or create a project, and enable the PageSpeed Insights API for it.
3. Create an API key.
4. Restrict the key to the PageSpeed Insights API.
5. In your own terminal, type this line. It asks for the key without showing it:

```bash
umask 077 && mkdir -p ~/.config/nca-conversion && read -rs -p 'PageSpeed key: ' k && printf '%s' "$k" > ~/.config/nca-conversion/pagespeed.key && unset k && echo
```

The key file path is `~/.config/nca-conversion/pagespeed.key`. The environment variable `NCA_PAGESPEED_KEY` overrides it. Without a key, speed is measured by local Lighthouse and labelled "lab data".
