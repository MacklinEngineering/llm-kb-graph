# knowledge-base-wiki

A Claude Code [agent skill](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) that builds and maintains a [Karpathy-style](https://x.com/karpathy/status/1978662038019215696) LLM knowledge wiki — a self-compiling markdown knowledge base — backed by [`ki`](https://github.com/zach-blumenfeld/knowledge-index) for graph-based search and retrieval.

Tell Claude: *"Start a knowledge wiki on transformer scaling"* or *"What do my notes say about RAG tradeoffs?"* — the agent handles writing, cross-linking, indexing, and Q&A. You provide raw material and steer direction.

## Quickstart

### 1. Install the skill

```bash
curl -fsSL https://raw.githubusercontent.com/zach-blumenfeld/llm-kb-graph/main/install.sh | bash
```

Writes the skill to `~/.claude/skills/knowledge-base-wiki/`. Update later by re-running the same command. Uninstall with `rm -rf ~/.claude/skills/knowledge-base-wiki`.

### 2. Open Claude Code in a fresh directory and ask

```
Start a knowledge wiki on <your topic>
```

The skill activates and walks you through setup. The agent will:

- Install [`ki`](https://github.com/zach-blumenfeld/knowledge-index) (the search engine) automatically if it's not on your machine.
- Ask you how to connect a Neo4j database (where `ki` stores its index). You'll pick between **Aura** (managed cloud, billable — the agent will pause for your explicit go-ahead), **Existing** (a Neo4j you already run), or **Local** (Podman, if you have it). The agent never picks Aura silently.
- Walk you through wiki-specific questions (path, topic, fresh vs. seed, recurring ingestion sources).
- Scaffold the directory tree and index it.

After that, ingestion, querying, and linting all happen inside Claude Code — you don't need to remember commands.

### Things to be aware of

- **`raw/` is immutable.** Source files are never edited — only added or referenced. Mutations live in `wiki/`.
- **One wiki per directory.** The skill works inside whatever folder you point it at. You can have multiple wikis (e.g. one per topic); `ki` searches across them.
- **The agent does the writing.** You rarely edit `wiki/` files by hand. If you disagree with something, just tell the agent — it'll fix it and the audit trail lives in `.kbw/log/`.
- **Conversion tools.** For PDFs / docx / HTML sources, install one of: `brew install pandoc` (recommended) or `uv tool install markitdown`. Markdown sources need nothing.

## Recommended companions

### Sync the wiki between devices

A wiki is just markdown files in a folder — put that folder anywhere your sync tool of choice can see it.

- **iCloud Drive** — store the wiki under `~/Documents/` (Documents is iCloud-synced by default on macOS). [Setup](https://support.apple.com/en-us/108851).
- **Google Drive** — install [Drive for Desktop](https://support.google.com/drive/answer/10838124) and put the wiki under your Drive mount.
- **Dropbox** — install [Dropbox Desktop](https://help.dropbox.com/installs/desktop-app) and put the wiki under your Dropbox folder.
- **Syncthing** — [Syncthing](https://syncthing.net/) for peer-to-peer sync if you'd rather not use a cloud provider.

The wiki itself is git-friendly (`raw/refs/` keeps large binaries outside the tree), so plain `git push` works too — but cloud sync is usually less friction.

### View the wiki nicely

The wiki is just `.md` — any markdown reader works. The recommended pick:

- **[Obsidian](https://obsidian.md/)** *(recommended)* — free, opens any folder as a "vault", renders wikilinks + mermaid + KaTeX, has a graph view that shows the wiki's structure. [Getting started](https://help.obsidian.md/Getting+started/Download+and+install+Obsidian). Point it at your wiki root.
- **[VS Code](https://code.visualstudio.com/)** + [Markdown All in One](https://marketplace.visualstudio.com/items?itemName=yzhang.markdown-all-in-one) — if you live in VS Code, this works too (no graph view, but otherwise solid).
- **[Logseq](https://logseq.com/)** — alternative to Obsidian with a similar markdown-based model.
- **[Foam](https://foambubble.github.io/foam/)** (VS Code extension) — Obsidian-like wikilinks, graph view, and backlinks inside VS Code.

For sharing a wiki on the web: [Quartz](https://quartz.jzhao.xyz/) or [Obsidian Publish](https://obsidian.md/publish).

## `ki` — the search engine under the hood

This skill delegates all search and indexing to [`ki` (knowledge-index)](https://github.com/zach-blumenfeld/knowledge-index), a graph-based search engine for markdown collections. It indexes your wiki into Neo4j and lets the agent retrieve **section-level** chunks (typically 3–8 hits, ~100–500 tokens each) instead of reading the whole wiki on every question.

The skill runs `ki index` automatically after every write, and uses `ki search` / `ki tree` for retrieval. The agent occasionally surfaces a one-line note when `ki` saved a meaningful number of tokens; type `optout ki notes` to mute those messages.

`ki` is a separate project — see its [README](https://github.com/zach-blumenfeld/knowledge-index) for what's in it, what's on the roadmap (vector search, backlinks, MCP server), and known limitations.

## What's in this repo

```
llm-kb-graph/
├── install.sh                   # the one-liner installer
├── README.md                    # this file
└── skill/                       # what gets installed into ~/.claude/skills/knowledge-base-wiki/
    ├── SKILL.md                 # main skill instructions
    ├── references/              # detail docs (loaded on demand)
    └── scripts/                 # scaffold.py, ingest_inbox.py, lint_wiki.py
```

## License

MIT.
