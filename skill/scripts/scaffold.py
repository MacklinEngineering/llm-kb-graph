#!/usr/bin/env python3
"""Bootstrap a knowledge-base-wiki directory tree.

Usage:
    python3 scaffold.py <wiki-root> --topic "<topic>" --description "<one-line>"

Idempotent — re-running on an existing wiki adds missing folders/files but never
overwrites CLAUDE.md, wiki/index.md, or anything under raw/ or wiki/.

Stdlib only. No external dependencies.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

DIRS = [
    ".kbw/log",
    "raw/articles",
    "raw/papers",
    "raw/notes",
    "raw/inbox",
    "raw/refs",
    "wiki/concepts",
    "wiki/entities",
    "wiki/summaries",
    "outputs/queries",
]

CLAUDE_MD_TEMPLATE = """# {topic} — schema

> {description}

## Conventions

- **Page length target**: 400–1200 words. Past 1200, split into a subfolder.
- **Wikilinks**: `[[Page Name]]` with the human-readable name; aliases via `[[Target|Alias]]`.
- **Diagrams**: mermaid only (no ASCII art).
- **Formulas**: KaTeX (`$inline$`, `$$block$$`).
- **Large binaries**: never copy into `raw/`. Use a pointer file in `raw/refs/<slug>.md`.

## Current categories (mirrors wiki/index.md)

### Concepts
- (none yet — ingest a source to seed)

### Entities
- (none yet)

### Summaries
- (none yet)

## Recurring sources

(to be filled in by the agent based on the user's preference)

- [ ] Obsidian Web Clipper → `raw/articles/`
- [ ] `raw/inbox/` watch folder
- [ ] RSS / arXiv puller
- [ ] Gmail label → `raw/newsletters/`

## Open research questions

(ask the user to fill in 2–3 questions the wiki is trying to answer over time)

- Q1: ...

## Out of scope

(explicit list of what this wiki is NOT trying to cover)

- ...
"""

INDEX_MD_TEMPLATE = """# Index — {topic}

> {description}

## 🔖 Navigation
- [[#Concepts]] · [[#Entities]] · [[#Summaries]] · [[#Open Questions]]

## Concepts

(none yet)

## Entities

(none yet)

## Summaries (chronological)

(none yet)

## Open Questions

(mirrored from CLAUDE.md)
"""

CONFIG_YAML_TEMPLATE = """# knowledge-base-wiki — per-wiki config
# Created by scaffold.py. Hand-editable.

topic: {topic!r}
description: {description!r}

ki_notes: true   # set to false to mute ki-notes transparency messages

ingest:
  inbox:
    enabled: true
  obsidian_clipper:
    enabled: false
  rss:
    enabled: false
  gmail:
    enabled: false
"""

LOG_TEMPLATE = """# {date}

## [{time}] scaffold | created wiki for "{topic}"
"""


def ensure_dirs(root: Path) -> list[Path]:
    created = []
    for rel in DIRS:
        p = root / rel
        if not p.exists():
            p.mkdir(parents=True)
            created.append(p)
    return created


def write_if_missing(p: Path, content: str) -> bool:
    if p.exists():
        return False
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("wiki_root", type=Path, help="path to the wiki root (will be created if absent)")
    ap.add_argument("--topic", required=True, help="topic name (e.g. 'AI Research', 'Climate Policy')")
    ap.add_argument("--description", required=True, help="one-line scope description")
    args = ap.parse_args()

    root = args.wiki_root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    created_dirs = ensure_dirs(root)

    now = datetime.now(timezone.utc).astimezone()
    today = now.strftime("%Y%m%d")
    hhmm = now.strftime("%H:%M")
    date_iso = now.strftime("%Y-%m-%d")

    files_written = []
    if write_if_missing(root / "CLAUDE.md", CLAUDE_MD_TEMPLATE.format(topic=args.topic, description=args.description)):
        files_written.append("CLAUDE.md")
    if write_if_missing(root / "wiki" / "index.md", INDEX_MD_TEMPLATE.format(topic=args.topic, description=args.description)):
        files_written.append("wiki/index.md")
    if write_if_missing(root / ".kbw" / "config.yaml", CONFIG_YAML_TEMPLATE.format(topic=args.topic, description=args.description)):
        files_written.append(".kbw/config.yaml")
    if write_if_missing(root / ".kbw" / "log" / f"{today}.md", LOG_TEMPLATE.format(date=date_iso, time=hhmm, topic=args.topic)):
        files_written.append(f".kbw/log/{today}.md")

    print(f"✓ scaffolded wiki at {root}")
    print(f"  created {len(created_dirs)} dirs, {len(files_written)} files")
    for f in files_written:
        print(f"    + {f}")
    if not files_written and not created_dirs:
        print("  (everything already in place — idempotent re-run)")
    print()
    print("next:")
    print(f"  ki index {root} --description {args.description!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
