# Ingest pattern: `raw/inbox/` watch folder

The most flexible default — works for anything the user can drop into a folder. Recommended for almost every wiki.

## How it works

1. User drops files into `<wiki>/raw/inbox/`. Anything: `.md`, `.pdf`, `.docx`, `.html`, `.txt`, even a `.txt` containing one URL per line.
2. On the next `ingest` op (manual or scheduled), the agent runs `scripts/ingest_inbox.py <wiki-root>`.
3. The script:
   - Converts non-markdown files to `.md` (via `pandoc` if on PATH, else `markitdown`).
   - For each `.txt` file containing URLs (one per line), fetches each URL and converts to markdown.
   - Files each result into the right `raw/<articles|papers|notes>/` based on simple heuristics (PDF → papers, .md/.html → articles, paste/txt → notes; the agent can override).
   - Empties `inbox/` once everything is reconciled.
4. The agent then runs the rest of the `ingest` op against the newly-filed sources.

The agent must run `ki index <wiki-root>` after `ingest_inbox.py` finishes.

## Setup

No setup beyond having `pandoc` or `markitdown` on PATH for non-md sources:

```bash
brew install pandoc        # macOS
# or
uv tool install markitdown
```

The `inbox/` folder is created by `scripts/scaffold.py` on first wiki bootstrap.

## Scheduling (optional)

Most users will run the reconciliation manually ("hey, process my inbox"). If a user wants automation:

```bash
# crontab -e — run every hour during waking hours
0 8-22 * * *  /usr/bin/python3 ~/.claude/skills/knowledge-base-wiki/scripts/ingest_inbox.py /path/to/wiki >> /path/to/wiki/.kbw/log/cron.log 2>&1
```

⚠️ A cron'd `ingest_inbox.py` only reconciles files into `raw/`. It does **not** compile the wiki, because that needs the LLM. The next time the user opens a session in the wiki dir, the agent should detect new files in `raw/` (compare against `wiki/summaries/`) and offer to compile them.

## File-type heuristics

The script uses these defaults; the agent should sanity-check after:

| Extension / content | Lands in |
|---|---|
| `.pdf` | `raw/papers/` |
| `.md`, `.html`, `.htm` | `raw/articles/` |
| `.docx`, `.odt` | `raw/papers/` (treat long-form docs as papers) |
| `.txt` (URLs only, one per line) | each URL fetched → `raw/articles/<slug>.md` |
| `.txt` (prose) | `raw/notes/` |
| anything else | `raw/notes/` with a warning |

## What the agent should do after

After `ingest_inbox.py` reports "reconciled N files":

1. Read each new `raw/<subfolder>/<file>` in full.
2. Continue with the regular `ingest` op workflow (see `references/ops-guide.md`): summaries, concept/entity updates, index, `ki index`, log.

## Config

`<wiki>/.kbw/config.yaml` keys for this pattern:

```yaml
ingest:
  inbox:
    enabled: true
    last_reconciled: 2026-05-21T09:14:03Z   # written by the script
```
