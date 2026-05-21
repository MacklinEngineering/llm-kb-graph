# Lint recipes — what each pass checks and how to fix typical findings

`scripts/lint_wiki.py <wiki-root>` runs six passes. Each finding is one of these six types. This doc walks through what each one means and the standard fix.

## 1. Dead wikilinks

**What**: a `[[Target]]` in some wiki page where `Target.md` (or `Target/index.md`) doesn't exist anywhere under `wiki/`.

**Why it matters**: dead links rot the wiki's navigability. They're often left over from splits/renames.

**Fix path**:
- **Most common: rename**. The target page was renamed/moved; rewrite the link to match.
- **Promotion candidate**: the link was *intentional* — `[[Foo]]` was used because `Foo` should exist. If 3+ pages link to it (next pass picks this up too), promote it from "missing" to "stub" — create `wiki/concepts/Foo.md` as a 100-word stub flagged for fleshing out.
- **Drop it**: the link was a mistake. Rewrite the reference to plain text.

Confirm with the user before deletions.

## 2. Orphan pages

**What**: a wiki page with zero inbound `[[...]]` references from any other wiki page.

**Why it matters**: orphans are dead-ends in the graph. The user can't navigate to them from any other page.

**Fix path**:
- **Add inbound links** from any concept/entity/summary page that should reasonably reference the orphan.
- **Merge** if the orphan is a near-duplicate of another page.
- **Delete** if the orphan is genuinely useless (rare; ask the user before deleting wiki content).

Note: `wiki/index.md` itself is technically inbound-link-less in a chain-of-thought sense; the linter excludes it explicitly.

## 3. Missing index entries

**What**: a `.md` file under `wiki/` that doesn't appear (as a wikilink) in `wiki/index.md`. Or a wikilink in `wiki/index.md` that doesn't resolve on disk.

**Why it matters**: `wiki/index.md` is the master catalog and the LLM's first read on every session. Drift here means future agent runs miss content.

**Fix path**: regenerate `wiki/index.md` by walking `wiki/` — this is a normal sub-step of the `compile` op. Add missing pages under the right category; remove stale entries that no longer exist on disk.

## 4. Frequently-linked missing pages

**What**: a `[[X]]` referenced 3 or more times across the wiki, but `X.md` doesn't exist.

**Why it matters**: this is the wiki telling you what to write next. If 5 pages reference `[[Attention Mechanism]]` and it doesn't exist, that's a high-confidence article candidate.

**Fix path**:
- **Create a stub** with a 1-paragraph definition, links to the pages that reference it, and add it to `wiki/index.md` under the right category. Mark with a `> TODO: expand` blockquote so the next ingest knows to flesh it out.
- **Or**: add the topic to `CLAUDE.md` "Open research questions" and decide later.

This is the most valuable lint pass for wiki *growth* (vs hygiene).

## 5. Oversized pages

**What**: any `wiki/**/*.md` over ~1200 words.

**Why it matters**: large pages are hard to navigate, hard to update without conflicts, and hard for the LLM to load selectively. The Karpathy pattern wants a wiki of small, dense pages, not a few mega-pages.

**Fix path**: trigger a `compile`-style split. See `references/wiki-structure.md` "Divide and conquer" and `references/ops-guide.md` "Splitting a page — mechanics." Always confirm the split plan with the user before writing — splits are expensive to undo.

The 1200-word threshold is a heuristic, not a hard limit. A list-heavy index page might legitimately be 1500 words; a dense prose page at 1100 might still want splitting. Use judgement, but err on the side of splitting.

## 6. Stale summaries

**What**: a file in `raw/` (recursively) with no corresponding `wiki/summaries/<slug>.md`. The `<slug>` match is filename-stem-based.

**Why it matters**: every raw source should have a summary page. If `raw/articles/karpathy-llm-wiki.md` exists but `wiki/summaries/karpathy-llm-wiki.md` doesn't, that source was never integrated.

**Fix path**: this is exactly the trigger for an `ingest` op on that source. Read the raw file, write a summary, update affected concept/entity pages, update `wiki/index.md`, run `ki index`.

(`raw/refs/` pointer files are excluded — they don't need summaries.)

## After fixes

1. Run `ki index <wiki-root>` if any `wiki/` files changed.
2. Append a `lint` entry to `.kbw/log/<today>.md`: `## [HH:MM] lint | <N> issues found, <M> fixed`.
3. Optionally: re-run `lint_wiki.py` to confirm zero outstanding issues.

## What lint *doesn't* check

- **Factual accuracy.** Lint is a structural pass. If a claim is wrong, the user has to flag it or you have to check at write time.
- **Style consistency** beyond simple structural rules.
- **`raw/` quality.** Sources are immutable; lint never touches them.
- **`ki` graph integrity.** That's `ki`'s job — `ki index` is self-validating.
