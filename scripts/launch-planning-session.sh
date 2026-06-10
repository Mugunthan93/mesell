#!/usr/bin/env bash
#
# launch-planning-session.sh
#
# Create (or reattach to) a per-feature git worktree for a V1 feature
# planning sub-session. One worktree per feature; parallel sub-sessions get
# physically separated working directories so concurrent `git checkout`s no
# longer collide on the master tree.
#
# Owner: meesell-infra-builder
# Companion docs:
#   docs/plans/features/_WORKTREE_PROTOCOL.md   (why + how)
#   docs/plans/features/_status/README.md       (sub-session status files)
#
# Usage:
#   scripts/launch-planning-session.sh <feature-slug>
#
# Example:
#   scripts/launch-planning-session.sh auth-otp
#
# Exit codes:
#   0  worktree ready (created or already exists)
#   1  bad slug / arg error
#   2  git operation failed
#
# Idempotency:
#   - Re-running with an existing worktree is a no-op (prints status, exits 0).
#   - If you need to recreate, run:
#         git worktree remove /tmp/mesell-wt/<slug>
#     then re-run this script.
#
# This script DOES NOT:
#   - commit, push, or modify any tracked file
#   - touch the master tree's HEAD
#   - clean up `/tmp/mesell-wt/` (manual cleanup or system reboot)

set -euo pipefail

# ---------- constants ----------

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly WORKTREE_BASE="/tmp/mesell-wt"
readonly BASE_BRANCH="develop"

# Canonical list of V1 feature slugs — sourced from
# docs/plans/features/feature_planning_master.md (9 rows).
readonly VALID_SLUGS=(
  "auth-otp"
  "smart-picker"
  "catalog-form"
  "ai-autofill"
  "image-precheck"
  "live-preview"
  "price-calculator"
  "tracking-dashboard"
  "xlsx-export"
)

# ---------- helpers ----------

die() {
  echo "ERROR: $*" >&2
  exit 1
}

print_valid_slugs() {
  echo "Valid feature slugs:" >&2
  for s in "${VALID_SLUGS[@]}"; do
    echo "  - ${s}" >&2
  done
}

is_valid_slug() {
  local needle="$1"
  for s in "${VALID_SLUGS[@]}"; do
    if [ "$s" = "$needle" ]; then
      return 0
    fi
  done
  return 1
}

# Returns 0 if branch exists locally.
branch_exists_local() {
  local branch="$1"
  git show-ref --verify --quiet "refs/heads/${branch}"
}

# Returns 0 if branch exists on origin remote.
branch_exists_remote() {
  local branch="$1"
  git show-ref --verify --quiet "refs/remotes/origin/${branch}"
}

# ---------- arg parsing ----------

if [ $# -ne 1 ]; then
  echo "Usage: $0 <feature-slug>" >&2
  print_valid_slugs
  exit 1
fi

readonly SLUG="$1"

if ! is_valid_slug "${SLUG}"; then
  echo "ERROR: '${SLUG}' is not a V1 feature slug." >&2
  print_valid_slugs
  exit 1
fi

readonly WORKTREE_PATH="${WORKTREE_BASE}/${SLUG}"
readonly BRANCH="feature/${SLUG}/planning"

# ---------- pre-flight ----------

cd "${PROJECT_ROOT}"

if [ ! -d "${PROJECT_ROOT}/.git" ] && [ ! -f "${PROJECT_ROOT}/.git" ]; then
  die "${PROJECT_ROOT} is not a git working tree"
fi

# Best-effort refresh of origin/develop; offline is OK.
git fetch origin "${BASE_BRANCH}" --quiet 2>/dev/null || true

# Ensure the worktree base dir exists.
mkdir -p "${WORKTREE_BASE}"

# ---------- Case A — worktree already attached at the target path ----------

# `git worktree list --porcelain` is the canonical source of truth.
# Use a portable grep instead of relying on path equality only.
if git worktree list --porcelain | grep -F "worktree ${WORKTREE_PATH}" >/dev/null 2>&1; then
  CURRENT_BRANCH="$(git -C "${WORKTREE_PATH}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "<unknown>")"

  cat <<EOF
========================================================================
WORKTREE ALREADY EXISTS
========================================================================
Path:    ${WORKTREE_PATH}
Branch:  ${CURRENT_BRANCH} (target: ${BRANCH})

The worktree is already registered. To recreate it from scratch:
  git worktree remove ${WORKTREE_PATH}
  scripts/launch-planning-session.sh ${SLUG}

To open a planning session in the existing worktree:
  cd ${WORKTREE_PATH}
  # then open a new Claude Code session and paste:
  #   docs/plans/features/${SLUG}/PLANNING_DISPATCH.md
========================================================================
EOF
  exit 0
fi

# ---------- Case B/C — attach or create the worktree ----------

WORKTREE_MODE=""

if branch_exists_local "${BRANCH}"; then
  WORKTREE_MODE="attach-local"
  git worktree add "${WORKTREE_PATH}" "${BRANCH}" \
    || die "git worktree add failed (attach-local mode, branch=${BRANCH})"
elif branch_exists_remote "${BRANCH}"; then
  WORKTREE_MODE="attach-remote"
  # Create local branch tracking origin/<branch> at the same time.
  git worktree add -b "${BRANCH}" "${WORKTREE_PATH}" "origin/${BRANCH}" \
    || die "git worktree add failed (attach-remote mode, branch=${BRANCH})"
else
  WORKTREE_MODE="create-from-develop"
  # Create a brand-new branch from origin/develop (or local develop if no origin).
  if branch_exists_remote "${BASE_BRANCH}"; then
    git worktree add -b "${BRANCH}" "${WORKTREE_PATH}" "origin/${BASE_BRANCH}" \
      || die "git worktree add failed (create-from-develop mode, base=origin/${BASE_BRANCH})"
  elif branch_exists_local "${BASE_BRANCH}"; then
    git worktree add -b "${BRANCH}" "${WORKTREE_PATH}" "${BASE_BRANCH}" \
      || die "git worktree add failed (create-from-develop mode, base=local ${BASE_BRANCH})"
  else
    die "neither origin/${BASE_BRANCH} nor local ${BASE_BRANCH} is available — cannot create ${BRANCH}"
  fi
fi

# ---------- symlink shared resources into the worktree ----------
#
# Memory and agent specs MUST stay shared between the master tree and every
# worktree, otherwise sub-sessions would write to their own snapshots and
# context would diverge. Per dispatch §Task A item 8: only agent-memory/ and
# agents/ are symlinked; everything else (settings.json, hooks, etc.) is left
# untouched per worktree to avoid leaking workspace-level mutations.

mkdir -p "${WORKTREE_PATH}/.claude"

# .claude/agent-memory/ — replace any checked-out real dir with a symlink.
if [ -e "${WORKTREE_PATH}/.claude/agent-memory" ] || [ -L "${WORKTREE_PATH}/.claude/agent-memory" ]; then
  rm -rf "${WORKTREE_PATH}/.claude/agent-memory"
fi
ln -s "${PROJECT_ROOT}/.claude/agent-memory" "${WORKTREE_PATH}/.claude/agent-memory"

# .claude/agents/ — same treatment.
if [ -e "${WORKTREE_PATH}/.claude/agents" ] || [ -L "${WORKTREE_PATH}/.claude/agents" ]; then
  rm -rf "${WORKTREE_PATH}/.claude/agents"
fi
ln -s "${PROJECT_ROOT}/.claude/agents" "${WORKTREE_PATH}/.claude/agents"

# ---------- success banner ----------

cat <<EOF
========================================================================
WORKTREE READY
========================================================================
Feature slug: ${SLUG}
Mode:         ${WORKTREE_MODE}
Worktree:     ${WORKTREE_PATH}
Branch:       ${BRANCH}
Base:         ${BASE_BRANCH}

Symlinks created (shared with master tree):
  ${WORKTREE_PATH}/.claude/agent-memory -> ${PROJECT_ROOT}/.claude/agent-memory
  ${WORKTREE_PATH}/.claude/agents       -> ${PROJECT_ROOT}/.claude/agents

NEXT STEPS — to launch the planning sub-session:
  1. Open a new terminal / Claude Code window.
  2. cd ${WORKTREE_PATH}
  3. Open a new Claude Code session there.
  4. Paste the prompt block from:
       ${PROJECT_ROOT}/docs/plans/features/${SLUG}/PLANNING_DISPATCH.md
     (the block under "## PASTE THIS PROMPT INTO THE NEW SESSION")
  5. Sub-session writes its status to:
       ${PROJECT_ROOT}/docs/plans/features/_status/${SLUG}.yaml
     (NOT to feature_planning_master.md directly — see _status/README.md)

CLEANUP — when planning is done (FEATURE_PLAN.md merged):
  git worktree remove ${WORKTREE_PATH}
  # branch ${BRANCH} stays — delete only if PR is merged and not needed:
  #   git branch -D ${BRANCH}
  #   git push origin --delete ${BRANCH}   # if remote was pushed

Reference:
  ${PROJECT_ROOT}/docs/plans/features/_WORKTREE_PROTOCOL.md
========================================================================
EOF

exit 0
