#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# install-git-guards.sh  —  one-time activation of the master-tree commit guard.
#
# Points git at the committed .githooks/ directory so .githooks/pre-commit runs.
# Run ONCE per machine clone (it sets a local git config; it applies to the master
# checkout and all its worktrees). Safe to re-run (idempotent).
#
# This is the SECONDARY guard (non-Claude paths). The PRIMARY guard —
# .claude/hooks/guard-master-tree-git.sh, wired via .claude/settings.json — needs
# no install; Claude Code loads it automatically.
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

git config core.hooksPath .githooks
chmod +x .githooks/* 2>/dev/null || true

echo "✓ git core.hooksPath → .githooks"
echo "✓ master-tree pre-commit guard active (override: MESELL_ALLOW_MASTER_GIT=1)"
