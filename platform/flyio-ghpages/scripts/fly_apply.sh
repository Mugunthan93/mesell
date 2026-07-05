#!/usr/bin/env bash
# fly_apply.sh — idempotent create-if-absent for the Fly app. NEVER destroys, NEVER
# deploys (image ships via ci.yml deploy-backend). Called by terraform_data.fly_app.
#
# Inputs (env): FLY_APP, FLY_REGION, FLY_ORG.
# Exit non-zero only on a genuine tooling failure (missing flyctl / API error on create).
set -euo pipefail

: "${FLY_APP:?FLY_APP required}"
FLY_ORG="${FLY_ORG:-personal}"

if ! command -v flyctl >/dev/null 2>&1; then
  echo "[fly_apply] flyctl not found on PATH — install it or run outside CI. NO-OP." >&2
  exit 1
fi

# Does the app already exist? (adoption path → no-op)
if flyctl apps list 2>/dev/null | awk '{print $1}' | grep -qx "${FLY_APP}"; then
  echo "[fly_apply] app '${FLY_APP}' already exists — no-op (adoption-safe; deploy via CI)."
  exit 0
fi

echo "[fly_apply] app '${FLY_APP}' absent — creating in org '${FLY_ORG}' (config from fly.toml)."
flyctl apps create "${FLY_APP}" --org "${FLY_ORG}"
echo "[fly_apply] created '${FLY_APP}'. NOTE: attach Postgres/Redis + set secrets + deploy separately (see platform/README.md)."
