#!/usr/bin/env bash
d="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}/.claude/agent-memory"
[ -d "$d" ] || exit 0
chmod -R g+w "$d" 2>/dev/null || true
find "$d" -type d -exec chmod g+s {} + 2>/dev/null || true
exit 0
