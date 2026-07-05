#!/usr/bin/env bash
# gh_pages.sh — idempotent GitHub Pages build_type setter.
#
# PUTs the Pages build_type via `gh api` (create-or-update; PUT is idempotent). Never
# deletes Pages, never touches the repo. Called by terraform_data.pages_build_type.
#
# Inputs (env): GH_OWNER, GH_REPO, GH_BUILD_TYPE (workflow|legacy).
set -euo pipefail
: "${GH_OWNER:?GH_OWNER required}"
: "${GH_REPO:?GH_REPO required}"
GH_BUILD_TYPE="${GH_BUILD_TYPE:-workflow}"

if ! command -v gh >/dev/null 2>&1; then
  echo "[gh_pages] gh CLI not found on PATH — NO-OP." >&2
  exit 1
fi

echo "[gh_pages] ensuring Pages build_type=${GH_BUILD_TYPE} on ${GH_OWNER}/${GH_REPO}."
# If Pages is not yet enabled, POST first; then PUT the build_type. Both idempotent.
if ! gh api "repos/${GH_OWNER}/${GH_REPO}/pages" >/dev/null 2>&1; then
  gh api -X POST "repos/${GH_OWNER}/${GH_REPO}/pages" -f "build_type=${GH_BUILD_TYPE}" >/dev/null 2>&1 || true
fi
gh api -X PUT "repos/${GH_OWNER}/${GH_REPO}/pages" -f "build_type=${GH_BUILD_TYPE}"
echo "[gh_pages] done."
