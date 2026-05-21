#!/usr/bin/env python3
"""Reconcile <wiki>/raw/inbox/ into raw/<articles|papers|notes>/.

Converts non-markdown via pandoc or markitdown (whichever is on PATH).
Routes files based on extension heuristics. The agent should sanity-check
the routing after — these are defaults, not authoritative classifications.

Usage:
    python3 ingest_inbox.py <wiki-root>

Stdlib only.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

EXT_ROUTING = {
    # destination subdir : list of extensions
    "papers": [".pdf", ".docx", ".odt"],
    "articles": [".md", ".markdown", ".html", ".htm", ".mhtml"],
    "notes": [".txt"],  # also: anything unrecognized
}

# Files (any depth under inbox/) with these names are ignored.
IGNORED_NAMES = {".DS_Store", "Thumbs.db", ".gitkeep"}

SLUG_RE = re.compile(r"[^a-z0-9\-_]+")


def slugify(stem: str, max_len: int = 60) -> str:
    s = SLUG_RE.sub("-", stem.lower()).strip("-")
    return s[:max_len].strip("-") or "untitled"


def routing_for(path: Path) -> str:
    ext = path.suffix.lower()
    for subdir, exts in EXT_ROUTING.items():
        if ext in exts:
            return subdir
    return "notes"


def have(binary: str) -> bool:
    return shutil.which(binary) is not None


def convert_to_md(src: Path, dest: Path) -> bool:
    """Convert src → dest (.md). Returns True on success."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() in {".md", ".markdown"}:
        shutil.copy2(src, dest)
        return True
    if have("markitdown"):
        try:
            out = subprocess.run(
                ["markitdown", str(src)], check=True, capture_output=True, text=True
            )
            dest.write_text(out.stdout, encoding="utf-8")
            return True
        except subprocess.CalledProcessError as e:
            print(f"  ! markitdown failed on {src.name}: {e.stderr.strip()[:200]}", file=sys.stderr)
    if have("pandoc"):
        try:
            subprocess.run(
                ["pandoc", "-s", "-t", "gfm", "-o", str(dest), str(src)],
                check=True, capture_output=True, text=True,
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"  ! pandoc failed on {src.name}: {e.stderr.strip()[:200]}", file=sys.stderr)
    # No converter available, or both failed.
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("wiki_root", type=Path)
    args = ap.parse_args()
    root = args.wiki_root.expanduser().resolve()
    inbox = root / "raw" / "inbox"
    if not inbox.is_dir():
        sys.exit(f"error: {inbox} not found — is this a scaffolded wiki?")

    files = [
        p for p in inbox.rglob("*")
        if p.is_file() and p.name not in IGNORED_NAMES
    ]
    if not files:
        print(f"  (no files in {inbox})")
        return 0

    if not (have("pandoc") or have("markitdown")):
        print("  warning: neither pandoc nor markitdown on PATH.", file=sys.stderr)
        print("           Only .md files will be reconciled; everything else will be left in inbox/.", file=sys.stderr)

    moved = 0
    skipped = 0
    failed = 0
    for src in files:
        sub = routing_for(src)
        slug = slugify(src.stem)
        dest = root / "raw" / sub / f"{slug}.md"
        # Avoid clobbering existing destinations — append a short ts disambiguator.
        if dest.exists():
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            dest = dest.with_stem(f"{dest.stem}-{ts}")

        if src.suffix.lower() in {".md", ".markdown"}:
            shutil.move(str(src), str(dest))
            print(f"  + raw/{sub}/{dest.name}  (moved)")
            moved += 1
        elif have("pandoc") or have("markitdown"):
            if convert_to_md(src, dest):
                src.unlink()
                print(f"  + raw/{sub}/{dest.name}  (converted from {src.suffix})")
                moved += 1
            else:
                print(f"  ! left {src.relative_to(root)} in place — conversion failed")
                failed += 1
        else:
            print(f"  ~ skipped {src.relative_to(root)} — no converter and not markdown")
            skipped += 1

    # Empty out any leftover empty subdirs under inbox/.
    for sub in sorted(inbox.rglob("*"), key=lambda p: -len(p.parts)):
        if sub.is_dir() and not any(sub.iterdir()):
            sub.rmdir()

    print()
    print(f"reconciled: {moved} moved, {skipped} skipped, {failed} failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
