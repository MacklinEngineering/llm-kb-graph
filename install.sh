#!/usr/bin/env bash
# Install the knowledge-base-wiki skill into a Claude-Code-style skills directory.
#
# Usage (one-liner):
#   curl -fsSL https://raw.githubusercontent.com/zach-blumenfeld/llm-kb-graph/main/install.sh | bash
#
# Env overrides:
#   BRANCH=dev          install from a specific branch (default: main)
#   TARGET_BASE=...     parent directory of <skill-name>/ (default: ~/.claude/skills)
#   SKILL_NAME=...      directory name to install under (default: knowledge-base-wiki)
#
# Idempotent: re-running upgrades in place. Removes the existing skill dir and replaces it.
# No git, no dependencies beyond curl + tar.

set -euo pipefail

REPO="zach-blumenfeld/llm-kb-graph"
BRANCH="${BRANCH:-main}"
SKILL_NAME="${SKILL_NAME:-knowledge-base-wiki}"
TARGET_BASE="${TARGET_BASE:-$HOME/.claude/skills}"
TARGET="$TARGET_BASE/$SKILL_NAME"

for bin in curl tar; do
  command -v "$bin" >/dev/null 2>&1 || { echo "error: '$bin' not found on PATH" >&2; exit 1; }
done

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "→ downloading $REPO @ $BRANCH"
curl -fsSL "https://codeload.github.com/$REPO/tar.gz/refs/heads/$BRANCH" \
  | tar -xz -C "$tmp"

src="$tmp/llm-kb-graph-$BRANCH/skill"
[ -d "$src" ] || { echo "error: 'skill/' not found in archive ($src)" >&2; exit 1; }

mkdir -p "$TARGET_BASE"
rm -rf "$TARGET"
cp -R "$src" "$TARGET"

echo "✓ installed $SKILL_NAME → $TARGET"
echo
echo "  next steps:"
echo "    1. install ki:        uv tool install knowledge-index   (https://github.com/zach-blumenfeld/knowledge-index)"
echo "    2. configure neo4j:   ki configure"
echo "    3. start a wiki:      open Claude Code in a new dir, say 'start a knowledge wiki on <topic>'"
echo
echo "  update later: re-run the same curl one-liner."
echo "  uninstall:    rm -rf '$TARGET'"
