---
name: knowledge-base-wiki
description: Builds, queries, and maintains a Karpathy-style LLM knowledge wiki — a self-compiling markdown knowledge base where the agent ingests raw sources (articles, papers, notes, PDFs) into `raw/`, compiles cross-linked wiki articles into `wiki/`, runs Q&A grounded in the wiki rather than general knowledge, and uses the `ki` (knowledge-index) CLI for graph-based search and retrieval. Use when the user asks to (1) start, scaffold, or "build a wiki / knowledge base / second brain" on a topic; (2) ingest articles, papers, PDFs, web pages, or notes into an existing wiki; (3) ask questions grounded in their wiki ("what do my notes say about X"); (4) compile, restructure, split, or lint an existing wiki; (5) set up recurring source ingestion (Obsidian Web Clipper, watch folder, RSS/arXiv, Gmail label); or (6) view the wiki in Obsidian or another markdown reader. Not for ephemeral note-taking, daily journals, or non-wiki document collections.
---

# Knowledge-Base Wiki — Karpathy pattern, `ki`-powered

> Inspired by Andrej Karpathy's [LLM Knowledge Bases](https://x.com/karpathy/status/1978662038019215696) post. Search/retrieval is delegated to `ki` ([knowledge-index](https://github.com/zach-blumenfeld/knowledge-index)).

## Core idea

Don't do ad-hoc RAG. **Compile** raw sources into a persistent, cross-linked markdown wiki. Every ingest, query, and lint pass enriches the wiki; knowledge compounds.

- **You** (the user) own: sourcing raw material, asking good questions, steering direction.
- **You** (the agent) own: all writing, cross-referencing, filing, bookkeeping, index maintenance — *and* keeping `ki`'s index in sync so search stays fast as the wiki grows.

Four operations: **`ingest`**, **`compile`**, **`query`**, **`lint`**. Each appends an entry to `<wiki>/.kbw/log/YYYYMMDD.md`.

## Required tools — install them yourself

The user only ran the curl one-liner to get this skill. They did **not** install `ki` separately. The agent owns getting `ki` and its Neo4j connection in place — don't make the user do it.

Before any wiki operation, run this preflight. Run it on every first-run flow; subsequent sessions can skip if `ki --version` already succeeds and `ki vault list` returns without error.

```bash
# 1. ki — install via uv if missing. Reversible + per-user: safe to auto-fire.
if ! command -v ki >/dev/null 2>&1; then
  command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
  uv tool install knowledge-index
fi
ki --version

# 2. Neo4j connection — see "Neo4j choice" below. Do NOT pick Aura silently.
ki vault list >/dev/null 2>&1 || configure_neo4j_with_user_consent

# 3. Markdown conversion (only blocks non-md ingest). Install on demand, not at preflight.
command -v pandoc >/dev/null 2>&1 || command -v markitdown >/dev/null 2>&1 \
  || echo "tip: brew install pandoc  # or: uv tool install markitdown — install before next non-md ingest"
```

### Neo4j choice — the consent gate

`ki configure` asks for a Neo4j (Local / Aura / Existing). Auto-mode policy (mirrors `~/.claude/skills/ki/SKILL.md`):

1. **Try to detect an existing reachable Neo4j first.** If `ki vault list` already succeeds, there's a profile — done. Otherwise check `$NEO4J_URI` / `$NEO4J_PASSWORD` env vars, and `docker ps` / `podman ps` for a container exposing `:7687`. If found, run `ki configure → Existing` and report what you wired up.
2. **Otherwise, ask the user before doing anything.** Phrase it like:
   > I need a Neo4j to point `ki` at. Three options:
   > **(a) Aura** — Neo4j's managed cloud. Easiest setup but billable. I won't create one without your explicit go-ahead.
   > **(b) Existing** — if you already run Neo4j somewhere (Docker, a managed instance, etc.), give me the Bolt URI + credentials.
   > **(c) Local** — Podman container. Free and offline. Needs `podman` on your machine (see ki's docs/neo4j-podman.md).
   > Which would you like?
3. **Aura is billable. Never pick it silently.** The user saying "start a wiki" is consent for the wiki goal, not for creating cloud resources.
4. **`Local` requires `podman` on PATH.** If not present, suggest `brew install podman && podman machine init && podman machine start` (macOS) or distro-specific instructions, then re-run.

Once `ki vault list` returns cleanly, move on. Report one line: "✓ `ki` ready (profile: `<name>`)." Don't dwell.

### Honor `ki`'s skill rules

The agent-facing `ki` rules at `~/.claude/skills/ki/SKILL.md` are non-negotiable. This skill calls `ki search`, `ki tree`, `ki index`, `ki vault list`, and never bypasses them.

## Directory layout

Every wiki is one folder on disk. The skill works with this exact layout:

```
<wiki-root>/                  # whatever the user picked; e.g. ~/Documents/ai-wiki/
├── CLAUDE.md                 # schema/scope/conventions; reread at every session start
├── .kbw/
│   ├── config.yaml           # skill-local config (ingest sources, opt-outs)
│   └── log/
│       └── YYYYMMDD.md       # one file per day, one h2 per op
├── raw/                      # immutable sources (agent reads, never edits)
│   ├── articles/
│   ├── papers/
│   ├── notes/
│   ├── inbox/                # drop zone — reconciled into the above on next ingest
│   └── refs/                 # pointer files for large binaries (see references/wiki-structure.md)
├── wiki/                     # agent-generated; user reads, agent writes
│   ├── index.md              # master catalog — every page listed exactly once
│   ├── concepts/             # topic pages (split into subfolders past ~1200 words)
│   ├── entities/             # people, tools, papers, organizations
│   └── summaries/            # one summary page per source in raw/
└── outputs/
    └── queries/              # Q&A answers; durable ones get promoted into wiki/
```

`CLAUDE.md` is the **schema file** — wiki scope, naming conventions, open questions. Read it (and `wiki/index.md`) at the start of every session in a wiki dir. Template lives at `references/claude-md-template.md`.

## First-run flow

When the user is in an empty dir (or asks to "start a knowledge base"), walk this checklist. Don't skip steps; each gates the next.

```
Setup progress:
- [ ] 1. Pick the wiki root path
- [ ] 2. Pick the topic + 1-line description
- [ ] 3. Fresh start, or seed from existing docs?
- [ ] 4. Preflight ki: install if missing, configure Neo4j if no profile (ask before Aura)
- [ ] 5. Decide on recurring ingestion (none / inbox / clipper / RSS / Gmail)
- [ ] 6. Scaffold: run scripts/scaffold.py
- [ ] 7. Initial ki index
- [ ] 8. (if seeding) run an `ingest` op on the seed material
```

### Step 1–3 — Ask the user

1. *Where should the wiki live?* — absolute path; recommend `~/Documents/<topic>-wiki/`.
2. *What's the topic, in one sentence?* — used as the wiki description (flows into `Vault.description` and the description heading on `wiki/index.md`).
3. *Fresh or seed?* — *fresh* = empty `raw/`, `wiki/index.md` shows just the topic and open questions. *seed* = the user already has docs (folder of `.md` / PDFs / a vault / a Drive sync). If seeding, copy the source files into `raw/inbox/` for the first ingest; do not modify originals.

### Step 4 — preflight `ki`

Run the preflight from "Required tools — install them yourself" above:

1. If `ki` isn't on PATH, install it via `uv tool install knowledge-index`. Auto-fire (reversible + per-user).
2. If no Neo4j profile exists (`ki vault list` errors), walk the user through the **Neo4j choice** consent gate above. Don't pick Aura silently.
3. End with one line: "✓ `ki` ready (profile: `<name>`)." or, if you had to ask: "Set up `ki` with Neo4j (`<choice>`)."

### Step 5 — Recurring ingestion

Ask the user (offer all four; multi-select is fine; "skip for now" is also fine):

- **`inbox/` watch folder** *(most universal)*. User drops anything into `raw/inbox/`; next `ingest` op reconciles (converts non-md via pandoc/markitdown, files into the right `raw/<subfolder>`). See `references/ingest-watch-folder.md`.
- **Obsidian Web Clipper → `raw/articles/`** *(Karpathy's preferred path for web content)*. Configure the Clipper extension to save to `<wiki>/raw/articles/`. See `references/ingest-obsidian-clipper.md`.
- **RSS / arXiv puller** *(for research wikis tracking new papers)*. A cron'd `scripts/rss_pull.py` reads `<wiki>/.kbw/feeds.txt` and writes new items to `raw/feeds/`. See `references/ingest-rss.md`.
- **Gmail label → `raw/newsletters/`**. Pulls a labelled Gmail folder via the Gmail MCP. See `references/ingest-gmail.md`.

Whichever the user picks, record it in `<wiki>/.kbw/config.yaml` so future sessions know what to do. Templates for each pattern live in the corresponding `references/ingest-*.md`.

### Step 6–8 — Scaffold + initial index

```bash
python3 ~/.claude/skills/knowledge-base-wiki/scripts/scaffold.py "<wiki-root>" --topic "<topic>" --description "<one-line description>"
ki index "<wiki-root>" --description "<one-line description>"
# if seeding from existing docs: now run the `ingest` op against raw/inbox/
```

`scaffold.py` is idempotent and won't overwrite a pre-existing `CLAUDE.md` or `wiki/index.md`.

---

## The four operations

Every wiki action is one of these. Each ends with a log entry and (if it changed `raw/` or `wiki/`) an **asynchronous** `ki index <wiki-root>` to keep the graph in sync. The agent kicks indexing off with `run_in_background: true` and surfaces a one-line "✓ ki index done (N docs synced)" when the harness signals completion. See the "Async indexing" rule under `ki integration rules` below for the gating logic.

### `ingest` — add a new source

Use when the user wants to add articles, papers, PDFs, notes, transcripts, or anything else to the wiki.

Workflow:

```
Ingest progress:
- [ ] 1. Identify source(s): inbox/, a path the user gave, a URL, a paste
- [ ] 2. Convert to markdown if needed (pandoc / markitdown / WebFetch)
- [ ] 3. File into raw/<articles|papers|notes|refs>/
- [ ] 4. Read each source in full
- [ ] 5. Write wiki/summaries/<slug>.md (200–400 words; key takeaways, not a rewrite)
- [ ] 6. Update or create relevant wiki/concepts/ and wiki/entities/ pages
- [ ] 7. Update wiki/index.md (every wiki page appears exactly once)
- [ ] 8. Log: "## [HH:MM] ingest | <slug> — <one-line> (touched N pages)"
- [ ] 9. Kick off `ki index <wiki-root>` in background (run_in_background: true). Surface completion notice when it lands.
```

Details: `references/ops-guide.md` (article length, wikilink conventions, large-binary refs).

### `compile` — restructure existing wiki without new sources

Use when an existing page has outgrown ~1200 words, when `wiki/index.md` no longer reflects reality, when near-duplicates need merging, or when the user says "clean up the wiki."

Workflow:

```
Compile progress:
- [ ] 1. Read CLAUDE.md, wiki/index.md, and the target subtree
- [ ] 2. Plan splits (any page > 1200 words → subfolder + index page + sub-pages)
- [ ] 3. Plan merges (any near-duplicate pairs)
- [ ] 4. Confirm the plan with the user before writing
- [ ] 5. Apply the rewrite
- [ ] 6. Regenerate wiki/index.md
- [ ] 7. Log: "## [HH:MM] compile | <what changed>"
- [ ] 8. Kick off `ki index <wiki-root>` in background. Surface completion when it lands.
```

### `query` — answer questions grounded in the wiki

Use when the user asks a question that should be answered from *their* wiki, not from your training data.

**Retrieval order — use `ki` first, fall back to grep.**

```bash
# 1. Cross-vault routing (only if multiple wikis indexed).
ki vault list                                          # or: ki search "<topic>" --type vault --k 5

# 2. Structure browse — when you want a table of contents (toc) view of what exists across and within multiple documents without opening and scanning all of them.
ki tree  --depth 3 #start at root of all indexed wikis
ki tree --at "<vault|folder|document|section-uri>" --depth 3 #start toc outline at any specific level

# 3. Section-level retrieval — default; answers most questions in one query.
ki search "<user-question-keywords>" --json --k 8      # B.2 — section fulltext

# 4. Document-level — "find the doc about X" / "the note where I…".
ki search "<term>" --type document --k 5

# 5. Back to structured browse — when search is weak or you need to see what exists.
ki tree --at "<vault|folder|document|section-uri>" --depth 4
```

If `ki` returns ≤2 weak hits, retry with query expansion (`ki search 'X OR "Y" OR Z' --json`) — see `~/.claude/skills/ki/SKILL.md` "Query expansion."

Then:

```
Query progress:
- [ ] 1. ki search returns top sections (typically 3–8 hits)
- [ ] 2. Read those sections in full; follow one level of wikilinks if needed
- [ ] 3. If the wiki doesn't have enough material: say so, and suggest what to ingest. Do not make up the answer.
- [ ] 4. Synthesize the answer, citing wiki pages inline as [[Page Name]]
- [ ] 5. Write to outputs/queries/<YYYY-MM-DD>-<question-slug>.md
- [ ] 6. If durable (new synthesis, comparison, analysis): promote a cleaned version into wiki/concepts/ and update wiki/index.md
- [ ] 7. Log: "## [HH:MM] query | <question-slug>"  (+ "## [HH:MM] promote | ..." if promoted)
- [ ] 8. If you promoted: kick off `ki index <wiki-root>` in background. Surface completion when it lands.
```

Output formats beyond markdown — Marp slides, mermaid diagrams, matplotlib charts — are encouraged when the question warrants visual answers. File them under `outputs/<query-slug>/` and link from the query answer.

### `lint` — health + enhancement pass

Use when the user says "lint", "audit", "check the wiki", "find gaps", or periodically (after ~10 ingests).

```bash
python3 ~/.claude/skills/knowledge-base-wiki/scripts/lint_wiki.py "<wiki-root>"
```

The script reports:

- **Dead wikilinks** — `[[Target]]` where `Target.md` doesn't exist.
- **Orphan pages** — pages with zero inbound wikilinks.
- **Missing index entries** — wiki pages not listed in `wiki/index.md` (or listed but missing on disk).
- **Frequently-linked missing pages** — `[[X]]` referenced 3+ times but no page yet (great candidates for new articles).
- **Oversized pages** — `wiki/**/*.md` past ~1200 words (compile candidates).
- **Stale summaries** — files in `raw/` with no `wiki/summaries/<slug>.md`.

Enhancement (LLM-side, not script-side): after the script's report,

- Suggest a small batch of new article candidates from the "frequently-linked missing" list.
- For 1–2 thinly-covered concepts, optionally `WebSearch` to impute missing data — but only with the user's go-ahead.
- Note interesting cross-links the user might want.

```
Lint progress:
- [ ] 1. Run lint_wiki.py
- [ ] 2. Group findings into: must-fix (dead links, malformed index), should-fix (oversized, stale summaries), enhancement (new article candidates)
- [ ] 3. Propose fixes per group; confirm with the user before applying
- [ ] 4. Apply
- [ ] 5. Log: "## [HH:MM] lint | <N> issues, <M> fixed"
- [ ] 6. If anything in `wiki/` changed: kick off `ki index <wiki-root>` in background. Surface completion when it lands.
```

---

## `ki` integration rules

These are non-negotiable. Violating them silently degrades search.

1. **Async indexing — never block the user.** After any op that wrote to `raw/` or `wiki/`, kick off `ki index <wiki-root>` with `run_in_background: true`. Don't wait for it. Continue with whatever the user wants next. When the harness signals completion, surface a single short line: `✓ ki index done — N docs synced.` Phrase the wait-aware version as the op is wrapping up: "Indexing in the background; I'll let you know when it's caught up."

   **Gating rule — the one time you must wait.** If the user's next action is a `query` op (or anything else that depends on the *fresh* index — e.g. a `lint` looking for stale summaries) **and** there's a still-running background `ki index` from the prior op, await it before running the search. Phrase it: "Indexing from the last op is still finishing — one sec." This is the only scenario where you block; everything else stays async.
2. **For "what did I write about X" / "find me Y in my notes" — use `ki search`, not grep-then-read.** Section-level fulltext returns 3–8 highly relevant chunks at ~100–500 tokens each, vs. reading the wiki/index.md and following links (often 10k–50k tokens). Be honest: when the wiki is tiny (<10 pages), reading `index.md` and the few pages may actually be cheaper — use judgement.
3. **For structure / "what's in the vault" — use `ki tree`**, not `find` or `ls -R`.
4. **For "what does this doc link to" — `ki tree --at "<doc-uri>" --depth 1`.** Backlinks ("what links *to* this") are not wired in `ki` yet (issue #35); fall back to `grep -r '\[\[<Page>' <wiki-root>/wiki/`.
5. **Never claim a `ki` capability that isn't listed in `~/.claude/skills/ki/SKILL.md` "Capabilities not yet wired."** If the user asks for vector search, backlinks, subtree-scoped search, etc., tell them it's on the roadmap and offer the closest wired alternative.

## `ki` notes — short, honest, opt-out-able

Brief comments on what `ki` with neo4j saved you. The point is **truthful transparency**, not promotion. Rules:

- **One short line max**, appended after the substantive answer. Not before it. Not in headlines.
- **Only when there's a concrete, defensible gain.** E.g. "ki returned 4 sections (~600 tokens) — would've needed to read ~12 pages otherwise." If you can't quantify or it'd be marginal, say nothing.
- **Estimate conservatively.** If you're guessing token counts, prefix with "~". Don't fabricate latency numbers.
- **Skip on every routine op.** A `ki index` finishing in 200ms isn't worth a note. A multi-step retrieval that obviously saved a lot of reading is.
- **Honor opt-out.** If `<wiki>/.kbw/config.yaml` contains `ki_notes: false`, never emit one. If the user says "stop the ki notes" / "optout ki notes" / similar, set that flag and confirm.
- **First-time hint.** The *first* ki note in a wiki ends with: `(type "optout ki notes" to mute these)`. After that, no hint.

Examples of good notes:

> neo4j via ki returned 3 matching sections (~420 tokens). Reading the full wiki/index.md + the 8 pages it points at would've been ~9k tokens.

> neo4j via ki tree gave the section URI directly — no need to grep through 47 files.

> neo4j via ki search on "transformer scaling" found the right doc on the first try across both wikis; no manual vault routing needed.

Examples of notes to **not** write:

> neo4j via ki is faster than grep!  *(no — only sometimes, and that's not the point)*

> Saved 47.3% latency.  *(don't fabricate)*

> ki note: ki indexed the file in 180ms.  *(routine; not worth a line)*

See `references/ki-notes.md` for the full guidance + more examples.

---

## Scripts (run, don't read)

All three are pure-Python, stdlib-only, idempotent. Always run from `~/.claude/skills/knowledge-base-wiki/scripts/`.

| Script | Purpose | Invocation |
|---|---|---|
| `scaffold.py` | Bootstrap a new wiki directory tree + initial `CLAUDE.md` + `wiki/index.md`. | `python3 scaffold.py <wiki-root> --topic "<...>" --description "<...>"` |
| `ingest_inbox.py` | Reconcile `<wiki>/raw/inbox/` into `raw/<articles\|papers\|notes>/`, converting non-md via pandoc or markitdown (whichever is on PATH). | `python3 ingest_inbox.py <wiki-root>` |
| `lint_wiki.py` | Six-pass health check (dead links, orphans, index drift, frequently-linked missing, oversized pages, stale summaries). | `python3 lint_wiki.py <wiki-root>` |

`scripts/rss_pull.py` is created on first use of the RSS ingest pattern (see `references/ingest-rss.md`) — not bundled by default to keep the skill stdlib-pure.

## Reference docs (read on demand)

- `references/claude-md-template.md` — what to put in `CLAUDE.md` (scope, conventions, open questions).
- `references/wiki-structure.md` — directory conventions, naming, divide-and-conquer, mermaid/KaTeX, large-binary refs.
- `references/ops-guide.md` — detailed walkthrough of each of the four ops.
- `references/ki-notes.md` — full guidance on the ki-notes transparency layer.
- `references/ingest-watch-folder.md` — inbox/ pattern + `ingest_inbox.py` usage.
- `references/ingest-obsidian-clipper.md` — Web Clipper config to dump into `raw/articles/`.
- `references/ingest-rss.md` — feed puller template + cron setup.
- `references/ingest-gmail.md` — Gmail-MCP-based label → `raw/newsletters/` flow.
- `references/lint-recipes.md` — what each lint pass checks and how to fix typical findings.

## Anti-patterns — don't do these

- **Don't edit `raw/`.** It's immutable. Source files only get added, never rewritten. Mutations belong in `wiki/`.
- **Don't write to `wiki/` without updating `wiki/index.md`.** `lint_wiki.py` will flag it; better not to introduce the drift in the first place.
- **Don't skip the background `ki index` after a write.** Async is the default, *not* "optional". Stale graph = wrong retrieval next time.
- **Don't block the user on `ki index`.** Kick it off with `run_in_background: true` and move on. The only time to wait is when the *immediate* next op needs the fresh index (see "Async indexing" gating rule above).
- **Don't introduce symlinks anywhere inside the wiki tree.** Not in `raw/`, not in `wiki/`, not in `outputs/`. Symlinks break in three predictable ways: (a) cloud-sync providers (Drive, Dropbox, iCloud) handle them inconsistently and often de-link them, (b) `ki index` may follow them and ingest out-of-tree content with confusing URIs, (c) moving the wiki to another machine breaks the link silently. **For large external binaries**, use a `raw/refs/<slug>.md` pointer file (YAML front matter with `external_path`) — see `references/wiki-structure.md`. **For sharing content between wikis**, copy it; don't link it.
- **Don't answer wiki questions from training data.** If `ki search` returns nothing useful, say so and suggest an ingest — don't smuggle in general knowledge as if it came from the wiki.
- **Don't cram everything into one concept page.** Past ~1200 words, split into a subfolder with an `index.md`. See `references/wiki-structure.md` "Divide and conquer."
- **Don't read `wiki/**/*.md` exhaustively when `ki search` would do.** Pay attention to wiki size — the cross-over point is somewhere around 10–20 pages.
