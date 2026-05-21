# Ops guide — `ingest`, `compile`, `query`, `lint`

Detailed walkthroughs for each operation. The high-level checklists are in `SKILL.md`; this file is what to read when you're actually executing one.

## `ingest`

### Detecting source type

| Input the user gives you | Where it goes |
|---|---|
| A URL | Fetch via `WebFetch`; save as `raw/articles/<slug>.md` |
| A PDF path | Convert via pandoc/markitdown to `raw/papers/<slug>.md` |
| An `.md` file path | Copy verbatim into `raw/<articles\|papers\|notes>/<slug>.md` |
| Pasted text | Save to `raw/notes/<slug>.md` with a small `# Source: user paste, <date>` header |
| A folder | Treat each file individually |
| Large binary (>10 MB) | Don't copy. Create `raw/refs/<slug>.md` pointer (see `references/wiki-structure.md`) |
| `raw/inbox/` has files | Run `scripts/ingest_inbox.py <wiki-root>`, which reconciles automatically |

### Slug naming

Lowercase, hyphenated, ≤ 60 chars, derived from the source title. Examples:

- "Karpathy's LLM Knowledge Bases post" → `karpathy-llm-knowledge-bases`
- "Attention Is All You Need (Vaswani et al. 2017)" → `vaswani-attention-is-all-you-need`

Drop punctuation, accents, "the/a/an", and dates unless they're load-bearing (e.g. for blog posts where multiple posts share titles).

### Writing the summary

`wiki/summaries/<slug>.md` — 200–400 words. Not a rewrite of the source. Structure:

```markdown
# <Source title>

**Source**: [[raw/articles/<slug>]] · <author> · <year> · <one-line provenance>

## Key takeaways

- <bullet 1 — load-bearing claim, not a paraphrase>
- <bullet 2>
- <bullet 3>

## Notable details

<1–2 paragraphs on anything that doesn't fit "key takeaways" but is worth remembering>

## Connections

- See also: [[concepts/<related>]], [[entities/<author>]]
```

Summary pages are link hubs — every concept and entity referenced should have a wikilink. The agent reads summaries to triangulate before writing concept pages.

### Creating/updating concept pages

For each major concept the source introduces or extends:

1. Check if `wiki/concepts/<concept>.md` (or `wiki/concepts/<concept>/index.md`) exists.
2. If yes: open it, integrate the new material. Add a line under "## Sources" linking back to `[[summaries/<slug>]]`.
3. If no: create it. Use the article template (see "Article structure" below). Add to `wiki/index.md` under the right category.
4. If the new content pushes the page past 1200 words: trigger a folder-split (see `references/wiki-structure.md` "Divide and conquer"). Confirm with the user before doing the rewrite — splits are expensive to undo.

### Creating/updating entity pages

For every person, tool, paper, or organization named in the source:

- Quick stub if new (under 200 words): name, one-line description, why it's relevant to this wiki, links to the summaries / concepts that reference it.
- Update if existing: add the new reference, expand the description if there's substantive new info.

### Article structure (concept pages)

```markdown
# <Concept name>

> One-sentence definition that would make sense to someone new to the wiki.

## tl;dr

<2–4 bullets — the load-bearing claims about this concept>

## <Section 1>

<body, with [[wikilinks]] to related concepts and entities>

## <Section 2>

<...>

## Sources

- [[summaries/<source-1>]] — what it contributed
- [[summaries/<source-2>]] — what it contributed
```

### After every ingest

1. Update `wiki/index.md` so every new/changed page is listed.
2. Run `ki index <wiki-root>`.
3. Append a log entry to `<wiki>/.kbw/log/<today>.md`.

## `compile`

Use when no new sources are involved but the existing wiki needs restructuring. Common triggers:

- The user says "clean up the wiki" / "the index looks stale" / "this page is too long."
- A concept page has crossed 1200 words.
- Two pages cover near-identical material and should be merged.
- A subfolder's index doesn't reflect its actual contents.

### Workflow

1. Read `CLAUDE.md`, `wiki/index.md`, and the target subtree in full.
2. Catalog issues:
   - Oversized pages (run `lint_wiki.py` to surface these).
   - Near-duplicate page pairs.
   - Pages not listed in `wiki/index.md`.
   - Pages whose location no longer matches their category.
3. Propose a written plan to the user **before writing**. Splits and merges are not cheap. Example:

   > Plan:
   > 1. Split `concepts/transformers.md` (1840 words) into `concepts/transformers/{index, attention, positional-encoding, scaling-laws}.md`.
   > 2. Merge `concepts/attention.md` (orphan, 240 words) into the new `concepts/transformers/attention.md`.
   > 3. Rebuild `wiki/index.md` to reflect the new hierarchy.
   > OK to proceed?

4. Apply, page by page.
5. Regenerate `wiki/index.md` from scratch (re-walk `wiki/`).
6. `ki index <wiki-root>`.
7. Log.

### Splitting a page — mechanics

If `wiki/concepts/transformers.md` is being split:

1. Create `wiki/concepts/transformers/index.md` with the original page's intro section + a bulleted list of the new sub-pages.
2. Move each section of the original into `wiki/concepts/transformers/<aspect>.md`. Each sub-page gets its own h1.
3. Rewrite wikilinks **inbound** to the original to point at the right sub-page where possible (e.g. `[[transformers]]` → `[[transformers/scaling-laws]]` if context is about scaling). For ambiguous references, keep `[[transformers]]` → `[[transformers/index|Transformers]]`.
4. Delete the original `wiki/concepts/transformers.md`.

`ki` will pick up the new structure on the next `ki index`. Existing inbound links will either resolve (rewritten) or fail the next `lint_wiki.py` pass (flagged for fix).

## `query`

### When ki search is the right tool

- "What do my notes say about X?" → `ki search "X"` (default section-level)
- "Find the doc where I wrote about Y" → `ki search "Y" --type document`
- "What's related to Z?" → look up the doc's URI via `ki search --type document`, then `ki tree --at "<uri>" --depth 1`
- "Which of my wikis covers W?" → `ki search "W" --type vault` (only if multi-vault)
- "Summarize what's in this wiki" → `ki tree --at "<vault-uri>" --depth 4`

### When to skim instead

- Wiki is tiny (<10 pages): reading `wiki/index.md` and 2–3 pages directly is often cheaper than a ki round-trip.
- User asks a meta-question about wiki *organization* (not content): read `CLAUDE.md` + `wiki/index.md`.

### Answering — order of operations

1. Resolve the right vault if multi-vault.
2. `ki search` for relevant sections (typically `--k 8 --json`).
3. If results are weak (<3 hits or low scores), retry with query expansion — see `~/.claude/skills/ki/SKILL.md` "Query expansion for semantic equivalence."
4. Read the returned sections in full. Follow one level of wikilinks if the answer requires it.
5. **If the wiki genuinely doesn't cover the question, say so.** Suggest 1–3 specific sources to ingest. Do not invent an answer from training data and dress it up as wiki-derived.
6. Synthesize the answer. Cite wiki pages inline as `[[Page]]`. Be specific about which page contributed what.
7. Write the answer to `outputs/queries/<YYYY-MM-DD>-<slug>.md`.
8. **Decide if it's durable.** "What does Karpathy think about RAG?" → not durable, lives in outputs/. "How do Karpathy's wiki pattern and RAG compare?" → durable, promote to `wiki/concepts/wiki-vs-rag.md`.
9. If promoted: update `wiki/index.md`, `ki index <wiki-root>`, log both `query` and `promote`.

### Output formats

Markdown is the default. For visual answers:

- **Slides**: write Marp markdown (`---marp: true---`) into `outputs/queries/<slug>/slides.md`. Render with `npx -y @marp-team/marp-cli@latest outputs/queries/<slug>/slides.md`.
- **Diagrams**: mermaid blocks inside the answer markdown. They render in Obsidian.
- **Charts**: a small `matplotlib` script writes a PNG to `outputs/queries/<slug>/<name>.png`, referenced from the markdown.

File any visual output alongside the markdown answer in the query's slug folder.

## `lint`

Run `scripts/lint_wiki.py <wiki-root>`. The script reports six categories — see `references/lint-recipes.md` for what each one means and how to fix it.

### Enhancement pass

After the scripted checks, do a short LLM-side enhancement pass:

1. **New article candidates**: from the "frequently-linked missing" list. Pick 1–3 most-linked. Propose creating them; if the user agrees, write stubs and put them in the `Open Questions` queue.
2. **Thin coverage**: any concept page with fewer than 3 inbound links AND fewer than 200 words is probably either an orphan-in-disguise or needs more material. Ask the user if it should be expanded, merged, or removed.
3. **Cross-link suggestions**: scan for places where `[[X]]` *could* be added but isn't. Be conservative — only suggest links that the source content actually warrants. Don't link-bomb.
4. **WebSearch for missing data** — only with the user's go-ahead, and only when a wiki page has a specific factual gap (e.g. "year of publication unknown"). Don't broadly research; that's an `ingest`, not a `lint`.

### After lint

1. Apply fixes per the user's go-aheads.
2. `ki index <wiki-root>` if anything in `wiki/` changed.
3. Log: count of issues found and fixed.
