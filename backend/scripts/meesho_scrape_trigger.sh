#!/usr/bin/env bash
# Manual one-off run of the Meesho batch template scraper.
# Used for debugging and ad-hoc runs outside the launchd schedule.
set -euo pipefail

PROJECT_ROOT="/Users/mugunthansrinivasan/Project/mesell"
PYTHON_BIN="${PROJECT_ROOT}/backend/.venv/bin/python"
SCRIPT="${PROJECT_ROOT}/backend/scripts/meesho_batch_scraper.py"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Python venv interpreter missing at ${PYTHON_BIN}" >&2
  exit 1
fi

if [[ ! -f "${SCRIPT}" ]]; then
  echo "Batch scraper missing at ${SCRIPT}" >&2
  exit 1
fi

cd "${PROJECT_ROOT}"
exec "${PYTHON_BIN}" "${SCRIPT}" "$@"
