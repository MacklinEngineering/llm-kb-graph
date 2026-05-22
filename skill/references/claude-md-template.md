# `CLAUDE.md` template for a wiki root

This is the file every session reads first when working inside a wiki directory. It's the **schema** — wiki scope, naming conventions, current state, open questions.

Keep it short (under 200 lines). Anything longer belongs in `wiki/` or in another `references/` file. The agent rereads this every time it enters the wiki dir; bloat costs tokens on every session.

## Template

```markdown
# <Wiki Topic> — schema

> One-sentence scope: <what's in here, what's not>.

## Conventions

- **Page length target**: 400–1200 words. Past 1200, split into a subfolder.
- **Wikilinks**: `[[Page Name]]` with the human-readable name; aliases via `[[Target|Alias]]`.
- **Diagrams**: mermaid only (no ASCII art).
- **Formulas**: KaTeX (`$inline$`, `$$block$$`).
- **Large binaries**: never copy into `raw/`. Use a pointer file in `raw/refs/<slug>.md`.
- **Citations**: every claim in a wiki page should cite either a `raw/` source or another `wiki/` page.

## Current categories (mirrors wiki/index.md)

### Concepts
- <category A>
- <category B>

### Entities
- people, tools, papers, organizations

### Summaries
- one per raw/ source

### Themes
- cross-cutting patterns across ≥2 concepts/drafts (agent surfaces these proactively during ingest/compile; see references/wiki-structure.md "Themes")

## Recurring sources

<filled in by the agent based on the user's step-5 choices in first-run flow>

- [ ] Obsidian Web Clipper → `raw/articles/` — <enabled? config notes>
- [ ] `raw/inbox/` watch folder — <enabled? cron schedule if any>
- [ ] RSS / arXiv puller — <enabled? feed list at .kbw/feeds.txt>
- [ ] Gmail label → `raw/newsletters/` — <enabled? label name>

## Open research questions

<the user's actual questions; this is the queue the wiki is trying to answer over time>

- Q1: ...
- Q2: ...
- Q3: ...

## Out of scope

<explicit list of things this wiki is NOT trying to cover — helps the agent reject off-topic ingest requests>

- ...
```

## Filling it in

On first scaffold, `scripts/scaffold.py` writes a stub with the topic + description filled in and the rest as placeholders. The agent should:

1. After scaffolding, ask the user 2–3 questions to fill out **Open research questions** and **Out of scope**. These two sections do the most work — they're how future ingests get filtered for relevance.
2. As the wiki grows, **update Conventions** when the user makes a stylistic choice ("always use Title Case for page filenames", "always include a tl;dr at the top of concept pages"). That's how those choices stick across sessions.
3. **Current categories** is regenerated on every `compile` op.

## Why not just put this in SKILL.md?

`SKILL.md` is for the *skill*, loaded into context any time the user is doing wiki work anywhere. `CLAUDE.md` is for *this specific wiki*, loaded only when the user is inside this wiki's dir. They serve different layers.
