#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# warn-infra-dryrun.sh  —  PreToolUse(Bash) WARN-ONLY hook
#
# Adoption Step 2B (docs/dev/LIFECYCLE_HOOKS.md / CLAUDE_FEATURE_ADOPTION.md
# §"Lifecycle hooks"). Infra mutations are blast-radius-heavy; the playbook
# requires a dry-run / kubectl diff before every apply. This hook is a MECHANICAL
# REMINDER: it warns when a cluster/IaC mutation is about to run WITHOUT a
# --dry-run flag.
#
# Contract (Claude Code PreToolUse hook):
#   - stdin  : JSON with .tool_input.command and .cwd
#   - stderr : human-readable warning (advisory only)
#   - stdout : {"decision":"allow"}   ALWAYS
#
# SAFETY: WARN-ONLY + FAIL-OPEN. Any parse error, missing tool, or unexpected
# input → still emit allow / exit 0. This hook MUST NEVER block, deny, or wedge a
# session. It is a nudge, not a gate — the playbook (not this hook) is the gate.
# ──────────────────────────────────────────────────────────────────────────────

allow() { printf '{"decision":"allow"}\n'; exit 0; }

input="$(cat 2>/dev/null)" || allow
if command -v jq >/dev/null 2>&1; then
  cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // ""' 2>/dev/null)" || cmd=""
else
  cmd=""
fi
[ -n "$cmd" ] || allow

# --- match a mutating infra command -------------------------------------------
is_mutation=0
if printf '%s' "$cmd" | grep -Eq 'kubectl[[:space:]]+(.*[[:space:]])?apply([[:space:]]|$)'; then
  is_mutation=1
elif printf '%s' "$cmd" | grep -Eq 'terraform[[:space:]]+(.*[[:space:]])?apply([[:space:]]|$)'; then
  is_mutation=1
elif printf '%s' "$cmd" | grep -Eq 'helm[[:space:]]+(upgrade|install)([[:space:]]|$)'; then
  is_mutation=1
fi

[ "$is_mutation" -eq 1 ] || allow

# --- already a dry-run? (kubectl --dry-run=server|client, helm --dry-run) ------
if printf '%s' "$cmd" | grep -Eq -- '--dry-run'; then
  allow
fi

printf '⚠️  warn-infra-dryrun: infra mutation without --dry-run detected. Per INFRASTRUCTURE_PLAYBOOK, run a dry-run first: kubectl apply --dry-run=server (or kubectl diff) / terraform plan / helm upgrade --dry-run. Verify the diff before mutating the cluster.\n' >&2

allow
