#!/usr/bin/env python3
"""Six-pass health check on a knowledge-base-wiki.

Passes (see references/lint-recipes.md for details and fixes):
    1. dead wikilinks
    2. orphan pages
    3. missing index entries (or stale ones)
    4. frequently-linked missing pages (article candidates)
    5. oversized pages (>1200 words)
    6. stale summaries (raw/ source without wiki/summaries/ counterpart)

Usage:
    python3 lint_wiki.py <wiki-root>

Stdlib only.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

WIKILINK_RE = re.compile(r"\[\[([^\[\]|#]+)(?:\|[^\]]+)?(?:#[^\]]+)?\]\]")

OVERSIZED_WORDS = 1200
FREQ_THRESHOLD = 3


def find_md(root: Path) -> list[Path]:
    return [p for p in root.rglob("*.md") if p.is_file()]


def page_basename(path: Path, wiki_dir: Path) -> str:
    """Return the link-target form for a wiki page.

    `wiki/concepts/Foo.md`           → "concepts/Foo" and also "Foo"
    `wiki/concepts/Foo/index.md`     → "concepts/Foo/index" and also "Foo"
    """
    rel = path.relative_to(wiki_dir).with_suffix("")
    return str(rel).replace("\\", "/")


def extract_links(text: str) -> list[str]:
    return WIKILINK_RE.findall(text)


def normalize_target(t: str) -> str:
    return t.strip().replace("\\", "/")


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("wiki_root", type=Path)
    args = ap.parse_args()
    root = args.wiki_root.expanduser().resolve()
    wiki = root / "wiki"
    raw = root / "raw"
    if not wiki.is_dir():
        sys.exit(f"error: {wiki} not found — is this a scaffolded wiki?")

    md_files = find_md(wiki)
    # Build the resolve table: every possible link-target form → file.
    resolve: dict[str, Path] = {}
    for f in md_files:
        rel = f.relative_to(wiki).with_suffix("")
        rel_str = str(rel).replace("\\", "/")
        resolve[rel_str] = f
        # Also let "Foo" resolve when the file is "concepts/Foo.md" or "concepts/Foo/index.md".
        bare = rel.parts[-1]
        if rel.parts[-1] == "index" and len(rel.parts) >= 2:
            bare = rel.parts[-2]
            resolve.setdefault(bare, f)
        resolve.setdefault(bare, f)

    inbound: defaultdict[Path, set[Path]] = defaultdict(set)
    dead_links: list[tuple[Path, str]] = []
    missing_counts: Counter[str] = Counter()

    for src in md_files:
        text = src.read_text(encoding="utf-8", errors="replace")
        for raw_target in extract_links(text):
            tgt = normalize_target(raw_target)
            target_file = resolve.get(tgt)
            if target_file is not None:
                if target_file != src:
                    inbound[target_file].add(src)
            else:
                dead_links.append((src, tgt))
                missing_counts[tgt] += 1

    # --- 1. dead links
    print("== 1. dead wikilinks ==")
    if dead_links:
        for src, tgt in dead_links:
            print(f"  - {src.relative_to(root)}: [[{tgt}]]")
    else:
        print("  ok")
    print()

    # --- 2. orphans (excluding index.md)
    print("== 2. orphan pages ==")
    index_md = wiki / "index.md"
    orphans = [
        f for f in md_files
        if f != index_md and len(inbound.get(f, set())) == 0
    ]
    if orphans:
        for f in orphans:
            print(f"  - {f.relative_to(root)}")
    else:
        print("  ok")
    print()

    # --- 3. index drift
    print("== 3. missing or stale index entries ==")
    if index_md.is_file():
        index_text = index_md.read_text(encoding="utf-8", errors="replace")
        index_targets = {normalize_target(t) for t in extract_links(index_text)}
        listed_files: set[Path] = set()
        for t in index_targets:
            f = resolve.get(t)
            if f:
                listed_files.add(f)
            else:
                print(f"  - stale entry in index.md: [[{t}]] (file missing)")
        for f in md_files:
            if f == index_md:
                continue
            if f not in listed_files:
                print(f"  - missing from index.md: {f.relative_to(root)}")
        if not any(True for _ in []):
            pass
    else:
        print("  ! wiki/index.md does not exist")
    print()

    # --- 4. frequently-linked missing pages
    print(f"== 4. frequently-linked missing (≥ {FREQ_THRESHOLD}) ==")
    candidates = [(tgt, n) for tgt, n in missing_counts.items() if n >= FREQ_THRESHOLD]
    candidates.sort(key=lambda x: -x[1])
    if candidates:
        for tgt, n in candidates:
            print(f"  - [[{tgt}]] referenced {n}x")
    else:
        print("  ok")
    print()

    # --- 5. oversized pages
    print(f"== 5. oversized pages (> {OVERSIZED_WORDS} words) ==")
    oversized = []
    for f in md_files:
        n = word_count(f.read_text(encoding="utf-8", errors="replace"))
        if n > OVERSIZED_WORDS:
            oversized.append((f, n))
    oversized.sort(key=lambda x: -x[1])
    if oversized:
        for f, n in oversized:
            print(f"  - {f.relative_to(root)}: {n} words")
    else:
        print("  ok")
    print()

    # --- 6. stale summaries
    print("== 6. stale summaries (raw/ source w/o wiki/summaries/) ==")
    summaries_dir = wiki / "summaries"
    stale = []
    if raw.is_dir() and summaries_dir.is_dir():
        existing_summaries = {p.stem for p in summaries_dir.glob("*.md")}
        for src in raw.rglob("*"):
            if not src.is_file():
                continue
            if "refs" in src.relative_to(raw).parts:
                continue
            if src.suffix.lower() not in {".md", ".markdown"}:
                # Treat any other ext as raw too — the summary slug match is filename stem.
                pass
            if src.stem not in existing_summaries:
                stale.append(src)
    if stale:
        for src in stale:
            print(f"  - {src.relative_to(root)}  (no wiki/summaries/{src.stem}.md)")
    else:
        print("  ok")
    print()

    # Summary line
    n_issues = (
        len(dead_links)
        + len(orphans)
        + len(candidates)
        + len(oversized)
        + len(stale)
    )
    print(f"-- {n_issues} issues across 6 passes --")
    return 0 if n_issues == 0 else 0  # always return 0; agent decides what to act on


if __name__ == "__main__":
    raise SystemExit(main())
