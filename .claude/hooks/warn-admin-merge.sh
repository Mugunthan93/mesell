#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# warn-admin-merge.sh  —  PreToolUse(Bash) WARN-ONLY hook
#
# Adoption Step 2B (docs/dev/LIFECYCLE_HOOKS.md / CLAUDE_FEATURE_ADOPTION.md
# §"Lifecycle hooks"). The pipeline has 0 required reviews and 8 PRs landed via
# `gh pr merge --admin` unreviewed. This hook is a MECHANICAL SPEED BUMP: it
# reminds the actor that --admin bypasses CI + review before the merge fires.
#
# Contract (Claude Code PreToolUse hook):
#   - stdin  : JSON with .tool_input.command and .cwd
#   - stderr : human-readable reminder (advisory only)
#   - stdout : {"decision":"allow"}   ALWAYS
#
# SAFETY: WARN-ONLY + FAIL-OPEN. Any parse error, missing tool, or unexpected
# input → still emit allow / exit 0. This hook MUST NEVER block, deny, or wedge a
# session.
# ──────────────────────────────────────────────────────────────────────────────

allow() { printf '{"decision":"allow"}\n'; exit 0; }

input="$(cat 2>/dev/null)" || allow
if command -v jq >/dev/null 2>&1; then
  cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // ""' 2>/dev/null)" || cmd=""
else
  cmd=""
fi
[ -n "$cmd" ] || allow

# --- match `gh pr merge ... --admin` ------------------------------------------
# Require both the `gh pr merge` verb and an `--admin` flag, in any order.
if printf '%s' "$cmd" | grep -Eq 'gh[[:space:]]+pr[[:space:]]+merge' \
   && printf '%s' "$cmd" | grep -Eq '(^|[[:space:]])--admin([[:space:]]|=|$)'; then
  printf '⚠️  warn-admin-merge: `gh pr merge --admin` bypasses CI gates and required review. Confirm this merge is founder-authorized AND that the /meesell-code-review gate was run on the diff. See docs/dev/REVIEW_GATES.md.\n' >&2
fi

allow
