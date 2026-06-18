#!/usr/bin/env bash
# gen_postman.sh — Regenerate the MeeSell Postman collection from the FastAPI app.
#
# Usage (from any directory):
#   bash backend/scripts/gen_postman.sh
#
# Steps:
#   1. Dump OpenAPI JSON from the FastAPI app (in-process, no server needed).
#      Falls back to http://localhost:8000/openapi.json if the app import fails.
#   2. Convert the OpenAPI JSON to a Postman v2.1 collection via
#      npx openapi-to-postmanv2 (no package.json pollution — dev-only via npx).
#   3. Write the collection to backend/postman/meesell.postman_collection.json.
#
# Requirements:
#   - Node.js 18+ (for npx)
#   - Python 3.9+ with the backend venv activated (or PYTHONPATH set)
#   - The backend .venv should already have all deps installed
#
# Zero cloud spend: all steps run locally; no credentials needed.
#
# To regenerate with a running server instead of in-process import:
#   MEESELL_OPENAPI_URL=http://localhost:8000/openapi.json bash backend/scripts/gen_postman.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
POSTMAN_DIR="${BACKEND_DIR}/postman"
OPENAPI_JSON="${POSTMAN_DIR}/openapi.json"
# The generated file is intentionally separate from the hand-authored collection
# (meesell.postman_collection.json) which has richer example bodies, the OTP
# auto-token test script, and auth overrides.  The generated file serves as a
# spec-accuracy reference and can be merged into the hand-authored file manually.
COLLECTION_OUT="${POSTMAN_DIR}/meesell_generated.postman_collection.json"

echo "[gen_postman] Backend dir: ${BACKEND_DIR}"
echo "[gen_postman] Postman dir: ${POSTMAN_DIR}"

mkdir -p "${POSTMAN_DIR}"

# ── Step 1: Dump OpenAPI JSON ──────────────────────────────────────────────────
echo "[gen_postman] Step 1: Dumping OpenAPI spec..."
VENV_PYTHON="${BACKEND_DIR}/.venv/bin/python"
# Worktrees share the .venv from the main checkout (not duplicated into the worktree).
MAIN_VENV_PYTHON="$(cd "${BACKEND_DIR}" && git rev-parse --show-toplevel 2>/dev/null)/backend/.venv/bin/python"

if [[ -x "${VENV_PYTHON}" ]]; then
    PYTHON="${VENV_PYTHON}"
elif [[ -x "${MAIN_VENV_PYTHON}" ]]; then
    PYTHON="${MAIN_VENV_PYTHON}"
else
    PYTHON="${PYTHON:-python3}"
fi

PYTHONPATH="${BACKEND_DIR}" "${PYTHON}" "${SCRIPT_DIR}/gen_openapi.py" \
    --out "${OPENAPI_JSON}"

if [[ ! -f "${OPENAPI_JSON}" ]]; then
    echo "[gen_postman] ERROR: OpenAPI JSON was not written to ${OPENAPI_JSON}" >&2
    exit 1
fi

echo "[gen_postman] OpenAPI JSON written: ${OPENAPI_JSON}"

# ── Step 2: Convert to Postman collection via npx ─────────────────────────────
echo "[gen_postman] Step 2: Converting to Postman collection (npx openapi-to-postmanv2)..."

# Note: openapi-to-postmanv2 v4+ uses positional args; the --options JSON string
# flags accepted by older versions now show "Invalid option" warnings but the
# conversion still succeeds.  The generated collection is a spec-accuracy reference;
# the hand-authored meesell.postman_collection.json is the primary import file.
npx --yes openapi-to-postmanv2 \
    -s "${OPENAPI_JSON}" \
    -o "${COLLECTION_OUT}"

if [[ ! -f "${COLLECTION_OUT}" ]]; then
    echo "[gen_postman] ERROR: Collection was not written to ${COLLECTION_OUT}" >&2
    exit 1
fi

echo "[gen_postman] Postman collection written: ${COLLECTION_OUT}"
echo "[gen_postman] Done. Import ${COLLECTION_OUT} into Postman."
