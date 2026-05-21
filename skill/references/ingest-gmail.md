# Ingest pattern: Gmail label → `raw/newsletters/`

For users who get a lot of substantive content via newsletters and want it in the wiki.

## How it works

1. User creates a Gmail label (e.g. `wiki/feed`) and applies it to anything they want ingested. They can do this manually or via a Gmail filter.
2. On `ingest`, the agent uses the Gmail MCP tools (already available in the Claude Code environment) to pull messages with that label.
3. Each message body becomes `<wiki>/raw/newsletters/<date>-<from>-<subject-slug>.md`.
4. The agent (optionally) applies a different Gmail label (e.g. `wiki/feed-done`) to keep the source label clean. The original label can be left or removed — `.kbw/config.yaml` records the preference.

The agent then runs the rest of the `ingest` op (summaries, concepts, `ki index`).

## Auth

The Gmail MCP uses Anthropic's connector OAuth — the user authenticates once via `mcp__claude_ai_Gmail__authenticate` when the skill first hits an unauthorized call. The skill doesn't manage credentials directly.

## Setup

When the user picks this pattern at scaffold time:

1. Ask for the label name (e.g. `wiki/feed`).
2. Ask if processed messages should be re-labeled (default `wiki/feed-done`) or left alone.
3. Write the config:

   ```yaml
   ingest:
     gmail:
       enabled: true
       source_label: "wiki/feed"
       done_label: "wiki/feed-done"   # null to skip relabeling
       output: raw/newsletters/
       last_fetched_at: null   # written by the agent on each run
   ```

## Agent workflow on `ingest` from Gmail

1. Read `<wiki>/.kbw/config.yaml` → get `source_label` and `last_fetched_at`.
2. Use the Gmail MCP to search for messages with that label, after `last_fetched_at` if set.
3. For each message:
   - Decode body (prefer text/plain; fall back to text/html → strip via the agent's own conversion).
   - Slug: `<date>-<from-domain>-<subject>` (e.g. `2026-05-21-substack-com-on-rag.md`).
   - Write `<wiki>/raw/newsletters/<slug>.md` with YAML front matter:
     ```yaml
     ---
     from: "Substack <noreply@substack.com>"
     date: 2026-05-21T08:14:00Z
     subject: "On RAG"
     gmail_id: <message-id>
     ---
     ```
4. If `done_label` is set, apply it to the message and remove `source_label`.
5. Update `last_fetched_at` to now.
6. Continue with the regular `ingest` op for the newly-written files.

## Tools the agent will use

- `mcp__claude_ai_Gmail__authenticate` (one-time)
- Gmail search / list messages / modify labels (whichever the Gmail MCP exposes — check the tool list)

## Config

`<wiki>/.kbw/config.yaml`:

```yaml
ingest:
  gmail:
    enabled: true
    source_label: "wiki/feed"
    done_label: "wiki/feed-done"
    output: raw/newsletters/
    last_fetched_at: 2026-05-21T08:14:03Z
```
