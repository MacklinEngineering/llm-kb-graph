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

## What `ki` actually gives you (vs. file-ops + grep)

`ki search` is a fulltext index. Lucene gives you that for free; it's not the reason to use `ki`. **The reason to use `ki` is `ki tree` and the graph-shape primitives it exposes.**

Concrete: `ki tree --at "<doc-uri>" --depth 3` returns, in one call:

- Every section heading of the doc (the per-doc table of contents)
- Every outbound `LINKS_TO` edge — both internal wikilinks AND external URLs — *organized by which section authored each link*
- The doc's place in the containment hierarchy (Vault → Folder → Document → Section)

To get the same picture from file-ops you'd need: `Read` the file, scan for headings, grep for `[[X]]` wikilinks, grep for `[label](url)` external links, then mentally organize who-cites-what. That's three or four tool calls collapsed into one, with the structural relationships preserved.

**This is the value-prop. `ki search` is a nice-to-have on top of it.**

### Default-to-`ki` substitution table

When working inside a ki-indexed wiki, default to the **right** column. Reach for the left only if you have a specific reason.

| Instead of...                          | Do this                                          | Why                                                                  |
|----------------------------------------|--------------------------------------------------|----------------------------------------------------------------------|
| `ls wiki/concepts/`                    | `ki tree --at "<vault>/wiki/concepts" --depth 2` | One call: folder + child docs + their top sections                   |
| `Read wiki/concepts/foo.md` (full)     | `ki tree --at "<vault>/wiki/concepts/foo.md" --depth 3` | Section outline + outbound `LINKS_TO` without reading the body |
| `Read wiki/concepts/foo.md` (one part) | `ki get "<section-uri>" --type content`          | Returns the specific section, not the whole doc                      |
| `grep -r "X" wiki/`                    | `ki search "X" --types section --json`           | Section-granular, ranked, ~15–25% of content tokens vs reading whole |
| `find wiki/ -name "*foo*"`             | `ki search "foo" --types document --json`        | Doc-level fulltext (titles + aliases) instead of filename guessing   |

**The default is the right column. The exception requires a reason.** Reasonable reasons: the wiki is tiny (<10 pages, reading is cheaper); the file was just written this turn and isn't in the index yet; the user explicitly asked for a raw filesystem view.

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
│   ├── summaries/            # one summary page per source in raw/
│   └── themes/               # cross-cutting patterns the agent surfaces proactively (see "Surfacing themes" below)
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

## First moves in any wiki session

**Default opening sequence** — run these before reaching for `find`, `grep`, `ls`, or `Read` of arbitrary wiki files. The index already knows the structure; use it.

```bash
ki vault list                                # 1. which wikis are indexed?
ki tree --depth 2                            # 2. shape of every vault (folders + docs, no sections)
ki tree --at "<vault-or-doc-uri>" --depth 4  # 3. structure of one subtree (folders + docs + sections + LINKS_TO)
ki search "<question>" --json --k 8          # 4. find relevant sections (most retrieval)
```

`ki tree --at <doc>` is the move people miss. It shows a document's **section hierarchy + outbound links** without reading the file. Use it before editing any existing concept page, before re-reading any long source, and before restructuring any subtree.

Sample (truncated) of `ki tree --at "transformers-wiki/claude.md" --depth 3`:

```
Key:  V Vault   F Folder   D Document   S Section   L Links-to

NAME                                             T   URI
CLAUDE.md ...................................... D   transformers-wiki/claude.md
  HuggingFace Transformers — schema ............ S   transformers-wiki/claude.md#huggingface-transformers-schema
    Conventions ................................ S   transformers-wiki/claude.md#...conventions
    Current categories ......................... S   transformers-wiki/claude.md#...current-categories
      Concepts ................................. S   transformers-wiki/claude.md#...concepts
        → attention.md ......................... L   transformers-wiki/raw/articles/attention.md
        → overview.md .......................... L   transformers-wiki/wiki/concepts/overview.md
      Entities ................................. S   transformers-wiki/claude.md#...entities
    Open research questions .................... S   transformers-wiki/claude.md#...open-research-questions
```

You can copy any URI from the output and feed it straight back into `ki tree --at <uri>` to expand a subtree, or trim the URI to walk *up* the hierarchy (see `~/.claude/skills/ki/SKILL.md` "Walking the URI schema").

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
- [ ] 4. **First**: `ki tree --at "<source-uri>" --depth 3` to see the section skeleton AND outbound `LINKS_TO` (internal + external) in one call. **Then**: `ki get "<section-uri>" --type content` for the sections you need, or `Read` the file if you genuinely need the whole body. Skipping the tree pass is the wrong default — it's cheap, and it tells you what to ignore. Exception: a source that hasn't been indexed yet (just dropped into `raw/inbox/`) — read it directly, since the index doesn't know about it until the next `ki index` settles.
- [ ] 5. Write wiki/summaries/<slug>.md (200–400 words; key takeaways, not a rewrite)
- [ ] 6. For each existing wiki/concepts/<X>.md or wiki/entities/<X>.md you're about to update:
       run `ki tree --at "<X-uri>" --depth 3` first. Shows its current sections + outbound `LINKS_TO` in one round-trip — faster than re-reading the file and integrates cleanly with what's already there.
- [ ] 7. Update or create relevant wiki/concepts/ and wiki/entities/ pages
- [ ] 8. **Scan for cross-cutting themes** — does this ingest reveal a pattern that connects ≥2 existing concepts/drafts (the same argument at different layers; the same opposition recurring; a recurring stylistic move)? If yes, write or update `wiki/themes/<slug>.md`. **Don't bury the observation as an open-question bullet** — themes are a first-class category. See "Surfacing themes proactively" below.
- [ ] 9. Update wiki/index.md (every wiki page appears exactly once)
- [ ] 10. Log: "## [HH:MM] ingest | <slug> — <one-line> (touched N pages)"
- [ ] 11. Kick off `ki index <wiki-root>` in background (run_in_background: true). Surface completion notice when it lands.
```

Details: `references/ops-guide.md` (article length, wikilink conventions, large-binary refs).

### `compile` — restructure existing wiki without new sources

Use when an existing page has outgrown ~1200 words, when `wiki/index.md` no longer reflects reality, when near-duplicates need merging, or when the user says "clean up the wiki."

Workflow:

```
Compile progress:
- [ ] 1. **First**: `ki tree --at "<target-uri>" --depth 4` to see the subtree's actual structure (folders/docs/sections) + every outbound `LINKS_TO`. *Then* — and only then — read `CLAUDE.md`, `wiki/index.md`, and any target files you still need. The tree pass is non-skippable: it's how you spot the orphans, the over-deep nesting, the cross-cutting links you'd otherwise miss. Reading the files first burns context on stuff the tree would have told you to skip.
- [ ] 2. Plan splits (any page > 1200 words → subfolder + index page + sub-pages)
- [ ] 3. Plan merges (any near-duplicate pairs)
- [ ] 4. Confirm the plan with the user before writing
- [ ] 5. Apply the rewrite
- [ ] 6. **Scan for cross-cutting themes** — a compile pass is a natural moment to surface (or refine) themes; restructured content often makes patterns visible that were buried before. Write or update `wiki/themes/<slug>.md` as needed. See "Surfacing themes proactively" below.
- [ ] 7. Regenerate wiki/index.md
- [ ] 8. Log: "## [HH:MM] compile | <what changed>"
- [ ] 9. Kick off `ki index <wiki-root>` in background. Surface completion when it lands.
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

## Surfacing themes proactively

A **theme** is a cross-cutting pattern that recurs across multiple concept pages, drafts, or summaries — the same argument repeated at different layers, the same opposition surfacing in unrelated posts, a recurring stylistic move that turns out to be the author's signature. Themes are a **first-class category** alongside Concepts / Entities / Summaries. They live at `wiki/themes/<slug>.md`.

**Why themes matter:** the most valuable observations an agent can make during ingest aren't *more concepts* — they're the connective tissue between concepts. Authors developing a body of work often don't see their own patterns until something names them. The agent is in a uniquely good position to notice (it's reading everything fresh, every session).

**The mistake to avoid:** when you spot a cross-cutting pattern mid-draft, **don't bury it as a one-line bullet under "Open questions"** on whichever concept page noticed it. That makes it un-findable, un-developable, and signals to the user that the observation is provisional. It's not. Promote it to a theme page immediately.

### When to write a theme

Default: at step 8 of `ingest` and step 6 of `compile`, ask yourself — *does this observation connect ≥2 existing concepts/drafts? Does it feel like the user's stance, not just a generic industry observation?* If yes on both, write a stub. Five minutes of stub-writing during ingest is worth more than thirty minutes of archaeological rediscovery three months later.

Concrete triggers:

- You catch yourself writing "this connects to [[X]] and [[Y]]" in two separate concept pages → theme.
- You notice the same opposition (e.g., *"don't own the substrate"*) phrased differently in three drafts → theme.
- A user comment lands twice in different conversations on the same observation → theme.
- A voice signature (a recurring stylistic move) is doing strategic work in multiple posts → theme.

### What a theme page contains

Minimum viable shape:

```markdown
# Theme — <Pattern Name>

**Pattern**: One-paragraph statement of the cross-cutting pattern in the author's voice.

**First noticed**: <date>, while <doing what>.

## Instances
- [[concept-or-draft-A]] — how this exemplifies the pattern
- [[concept-or-draft-B]] — how this exemplifies the pattern
- [[concept-or-draft-C]] — ...

## Why this is the author's stance, not generic industry observation
What makes the cross-layer / cross-instance consistency a *unique-author signal*, not just a common framing.

## Potential meta-post
- Working titles
- Why it might / might not work as its own essay
- Status (idea / researching / drafting / shelved / un-meta)

## Tracking new instances
Watch-list for future drafts that may add rows to the Instances list. Don't fork into a second theme — extend this one.

## Related
- [[sibling-theme-1]]
- [[parent-theme]] (if this is a sub-pattern of a larger theme)
```

### Theme vs. Concept vs. Open Question

| Surface | Use when | Lifetime |
|---|---|---|
| `wiki/concepts/<slug>.md` | One specific post idea | Days to weeks (until published/shelved) |
| `wiki/themes/<slug>.md` | A pattern across ≥2 concepts | Months to years (compounds as instances accumulate) |
| Open Question bullet | A question whose *answer* hasn't surfaced yet | Until answered, then promote or delete |

If an observation has named instances, it's a theme. If it's a question without instances, it's an open question. If it's a single specific post idea, it's a concept.

### Don't over-stub

A theme worth a page is one that:
- Connects ≥2 drafts/concepts (not a one-off observation).
- Feels like *the user's stance*, not a general industry framing they happened to use once.
- Has at least a working title or named pattern (don't write themes about vague vibes).

When in doubt: write the stub. A two-row theme with three bullets beats an unwritten observation by a wide margin.

---

## `ki` integration rules

These are non-negotiable. Violating them silently degrades search.

1. **Indexing is always background — never block on it.** After any op that wrote to `raw/` or `wiki/`, kick off `ki index <wiki-root>` with `run_in_background: true`. The agent moves on immediately — no awaiting, no progress reporting mid-conversation. When the harness signals completion, surface a single short line: `✓ ki index done — N docs synced.`

   **While a `ki index` is running for a vault, treat `ki` itself as unavailable for that vault — no `ki search`, no `ki tree`, no second `ki index`.** This is correctness-critical, not a perf nicety: `ki index` is **wipe-then-rebuild** (it `DETACH DELETE`s the vault subtree before re-ingesting from disk — see "Why" below). During that window the graph is mid-mutation; reads return stale/empty, and a second concurrent indexer corrupts the final state.

   **What the agent CAN still do while ki is busy** (this is the whole point of keeping it background):
   - Write to `raw/` and `wiki/` directly. File ops don't touch the graph.
   - Read files with the `Read` tool. Filesystem is unaffected.
   - Talk to the user, plan the next op, draft summaries.
   - Use `ki` on *other* vaults — only the busy vault is off-limits.

   **Coalescing — multiple writes during one index ≠ multiple follow-up indexes.** If the agent writes to the wiki while a background index is in flight, remember that the vault has un-indexed changes. When the in-flight index completes, check: are there pending changes? If yes, kick off **one** more `ki index` in the background and stop. Never queue more than one. A burst of N writes during one index run produces exactly one follow-up index.

   **If the user requests a `ki`-dependent op (`query`, `lint`, `ki tree` browse) while indexing for that vault is running** — acknowledge and wait. Phrase it: "Indexing from the last op is still finishing — I'll answer as soon as it's caught up (usually <30s for small wikis)." Then await completion and proceed. Don't substitute a hand-rolled grep; the wait is short and the graph answer is the right one.

   **Why this is wipe-then-rebuild, not incremental.** `ki index <vault>` removes the vault's existing docs/sections/folders/`LINKS_TO` from Neo4j, then re-writes them from the current disk state. That's how `ki` handles renames, deletes, and structural moves cleanly. The consequence is the serialization + read-gating rules above.

   **Implementation.** When you fire the bg `ki index`, save the bash shell ID for that vault. Before any `ki` call on that vault, check whether that shell is still running. Two simple guard points; no queue infrastructure needed.
2. **For "what did I write about X" / "find me Y in my notes" — use `ki search`, not grep-then-read.** Section-level fulltext returns 3–8 highly relevant chunks at ~100–500 tokens each, vs. reading the wiki/index.md and following links (often 10k–50k tokens). Be honest: when the wiki is tiny (<10 pages), reading `index.md` and the few pages may actually be cheaper — use judgement.
3. **Browse before you read — use `ki tree`, not `ls`/`find`/`Read` on directories.** Two patterns to internalize:
   - **Before opening a source file** (especially anything large or already indexed): `ki tree --at "<source-uri>" --depth 3` shows the section skeleton + outbound links. Cheap; tells you whether you need to read the whole thing.
   - **Before editing or restructuring an existing wiki page** (concept, entity, summary): `ki tree --at "<page-uri>" --depth 3` shows what's there *and* what it already links to. Faster than re-reading and ensures you integrate with the existing structure.
4. **For "what does this doc link to" — that's what `ki tree --at "<doc-uri>" --depth 1` is for** (the `L` rows in the output are outbound `LINKS_TO`). Backlinks ("what links *to* this") are not wired in `ki` yet (issue #35); fall back to `grep -r '\[\[<Page>' <wiki-root>/wiki/`.
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
- **Don't run `ki` (any subcommand) against a vault that's mid-index.** While a `ki index` for that vault is in flight: no `ki search`, no `ki tree`, no second `ki index`. The vault is wipe-then-rebuilding in Neo4j; reads return stale/empty and a second indexer corrupts the final state. Keep writing files / drafting / talking to the user — just don't shell out to `ki` for that vault. See "ki integration rules" §1.
- **Don't queue multiple follow-up indexes.** If the agent writes during an in-flight `ki index`, set a "pending re-index" flag in memory and let the in-flight one finish — *then* fire one (and only one) more. N writes during one index run → exactly one follow-up index, not N.
- **Don't await the `ki index` just to feel safe.** The only times to wait are: (a) the user requests a `ki`-dependent op and an index is still running for that vault. There's no other reason to block.
- **Don't introduce symlinks anywhere inside the wiki tree.** Not in `raw/`, not in `wiki/`, not in `outputs/`. Symlinks break in three predictable ways: (a) cloud-sync providers (Drive, Dropbox, iCloud) handle them inconsistently and often de-link them, (b) `ki index` may follow them and ingest out-of-tree content with confusing URIs, (c) moving the wiki to another machine breaks the link silently. **For large external binaries**, use a `raw/refs/<slug>.md` pointer file (YAML front matter with `external_path`) — see `references/wiki-structure.md`. **For sharing content between wikis**, copy it; don't link it.
- **Don't answer wiki questions from training data.** If `ki search` returns nothing useful, say so and suggest an ingest — don't smuggle in general knowledge as if it came from the wiki.
- **Don't cram everything into one concept page.** Past ~1200 words, split into a subfolder with an `index.md`. See `references/wiki-structure.md` "Divide and conquer."
- **Don't default to `Read` / `ls` / `find` / `grep` over `wiki/` when an indexed `ki tree` or `ki search` would do.** This is the single biggest agent-behavior trap. The "Default-to-`ki` substitution table" near the top of this file is the canonical list; consult it before reaching for file-ops. Cross-over to direct reads is around 10–20 pages of wiki, when reading the whole thing is cheaper than two tool calls.
- **Don't bury cross-cutting observations as open-question bullets.** If you notice a pattern that connects ≥2 concepts/drafts, it's a theme — write `wiki/themes/<slug>.md`. See "Surfacing themes proactively."
- **Don't `ls`, `find`, or `os.listdir` on `raw/` or `wiki/` to figure out what's there.** The index already has the structure. Use `ki tree --depth 2` from the vault root to see the shape, or `ki tree --at "<doc-uri>" --depth 3` to look inside a single document (you get its section hierarchy *and* its outbound `LINKS_TO` for free). Filename heuristics miss both.
