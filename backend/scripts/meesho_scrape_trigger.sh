#!/usr/bin/env bash
# Monthly Meesho data refresh — single entry-point for all three stages:
#   Stage A: category tree + XLSX templates (meesho_batch_scraper.py)
#   Stage B: getTransferPrice census (meesho_transfer_price_census.py)
#   Stage C: transform + drift gate (build_pricing_lookup.py + diff_pricing_lookup.py)
#
# Exit codes:
#   0   All stages OK; drift verdict PASS or REVIEW_REQUIRED (candidate staged)
#   1   Stage A failed (batch scraper)
#   2   Stage B failed (census / OTP required / gate failure)
#   3   Stage C build gate failed
#   4   Stage C drift gate BLOCK (live file untouched; see STATUS_DATA.md)
#   130 Interrupted
#
# To run Stage A (batch scraper) standalone without the full monthly refresh:
#   bash backend/scripts/meesho_scrape_trigger.sh --stage-a-only
#   OR directly: backend/.venv/bin/python backend/scripts/meesho_batch_scraper.py
#
# IMPORTANT: rotate .meesho_creds.env credentials before the next live run.
# See W6_REFRESH_SPEC.md §7 and the orchestrator runbook at the top of
# backend/scripts/meesho_monthly_refresh.py.
set -euo pipefail

PROJECT_ROOT="/Users/mugunthansrinivasan/Project/mesell"
PYTHON_BIN="${PROJECT_ROOT}/backend/.venv/bin/python"
ORCHESTRATOR="${PROJECT_ROOT}/backend/scripts/meesho_monthly_refresh.py"
BATCH_SCRAPER="${PROJECT_ROOT}/backend/scripts/meesho_batch_scraper.py"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Python venv interpreter missing at ${PYTHON_BIN}" >&2
  exit 1
fi

# --stage-a-only: run just the batch scraper (tree + templates) without census/diff
if [[ "${1:-}" == "--stage-a-only" ]]; then
  if [[ ! -f "${BATCH_SCRAPER}" ]]; then
    echo "Batch scraper missing at ${BATCH_SCRAPER}" >&2
    exit 1
  fi
  echo "Running Stage A only (meesho_batch_scraper.py)..." >&2
  cd "${PROJECT_ROOT}"
  exec "${PYTHON_BIN}" "${BATCH_SCRAPER}" "${@:2}"
fi

if [[ ! -f "${ORCHESTRATOR}" ]]; then
  echo "Monthly refresh orchestrator missing at ${ORCHESTRATOR}" >&2
  exit 1
fi

cd "${PROJECT_ROOT}"
exec "${PYTHON_BIN}" "${ORCHESTRATOR}" "$@"
