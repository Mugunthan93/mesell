#!/usr/bin/env bash
# fly_secrets.sh — idempotent, non-destructive Fly secret STAGING.
#
# Reads secret VALUES from the environment (TF_VAR_<NAME>) and stages only the ones
# that are non-empty via `flyctl secrets set --stage` (STAGE = no machine restart; a
# later deploy applies them). Values are NEVER echoed. Absent/empty vars are skipped,
# so an adoption run (all vars unset) stages nothing and leaves the ~40 live secrets
# untouched. Called by terraform_data.fly_secrets and (for the key) fly_gcs_key_push.
#
# Inputs (env): FLY_APP, TF_VAR_<KEY>=<value> for each managed key.
#   Optional MEESELL_SHIM_KEYS_ONLY="KEY1 KEY2" restricts to a subset (space-separated).
set -euo pipefail
: "${FLY_APP:?FLY_APP required}"

if ! command -v flyctl >/dev/null 2>&1; then
  echo "[fly_secrets] flyctl not found on PATH — NO-OP." >&2
  exit 1
fi

# The full set of Fly secret keys this shim knows how to stage. Each maps to TF_VAR_<KEY>.
ALL_KEYS="JWT_SECRET REFRESH_TOKEN_PEPPER GEMINI_API_KEY MSG91_AUTH_KEY RAZORPAY_KEY_ID RAZORPAY_KEY_SECRET GCS_SA_KEY_B64"
KEYS="${MEESELL_SHIM_KEYS_ONLY:-$ALL_KEYS}"

# Build the `KEY=value` arg list WITHOUT printing any value.
args=()
staged_names=()
for key in $KEYS; do
  var="TF_VAR_${key}"
  val="${!var:-}"
  if [ -n "${val}" ]; then
    args+=("${key}=${val}")
    staged_names+=("${key}")
  fi
done

if [ "${#args[@]}" -eq 0 ]; then
  echo "[fly_secrets] no non-empty secret vars supplied — nothing to stage (adoption-safe no-op)."
  exit 0
fi

echo "[fly_secrets] staging ${#args[@]} secret(s) on '${FLY_APP}': ${staged_names[*]} (values redacted; --stage = no restart)."
flyctl secrets set "${args[@]}" --app "${FLY_APP}" --stage
echo "[fly_secrets] staged. Run 'flyctl deploy' (or the next CI deploy-backend) to apply."
