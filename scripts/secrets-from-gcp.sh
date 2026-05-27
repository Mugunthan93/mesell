#!/usr/bin/env bash
# Materialise k8s/secrets.yaml from Secret Manager, ready for kubectl apply.
#
# Reads project / name_prefix from /etc/meesell.env (written by the Terraform
# startup script). Pulls every meesell-* secret and substitutes it into the
# template at k8s/secrets.yaml.example.
#
# Run this once after `terraform apply` and before `setup-vm.sh`, then again
# any time a secret is rotated.
set -euo pipefail

if [ ! -f /etc/meesell.env ]; then
  echo "ERROR: /etc/meesell.env not found. This script is meant to run on the VM provisioned by terraform." >&2
  exit 1
fi
# shellcheck disable=SC1091
. /etc/meesell.env

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUT="${REPO_DIR}/k8s/secrets.yaml"

fetch() {
  local key="$1"
  local secret_id="${NAME_PREFIX}-$(echo "$key" | tr '[:upper:]_' '[:lower:]-')"
  gcloud secrets versions access latest --secret="$secret_id" --project="$PROJECT_ID"
}

JWT_SECRET=$(fetch JWT_SECRET)
POSTGRES_PASSWORD=$(fetch POSTGRES_PASSWORD)
GEMINI_API_KEY=$(fetch GEMINI_API_KEY)
MSG91_AUTH_KEY=$(fetch MSG91_AUTH_KEY)
MSG91_TEMPLATE_ID=$(fetch MSG91_TEMPLATE_ID)
RAZORPAY_KEY_ID=$(fetch RAZORPAY_KEY_ID)
RAZORPAY_KEY_SECRET=$(fetch RAZORPAY_KEY_SECRET)

DATABASE_URL="postgresql+asyncpg://meesell:${POSTGRES_PASSWORD}@postgres:5432/meesell"

umask 077
cat > "$OUT" <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: meesell-secrets
  namespace: meesell
type: Opaque
stringData:
  POSTGRES_PASSWORD: "${POSTGRES_PASSWORD}"
  DATABASE_URL: "${DATABASE_URL}"
  VALKEY_URL: "redis://valkey:6379/0"
  CELERY_BROKER_URL: "redis://valkey:6379/1"
  CELERY_RESULT_BACKEND: "redis://valkey:6379/2"
  GEMINI_API_KEY: "${GEMINI_API_KEY}"
  GCS_BUCKET: "${BUCKET}"
  GCS_PROJECT_ID: "${PROJECT_ID}"
  MSG91_AUTH_KEY: "${MSG91_AUTH_KEY}"
  MSG91_TEMPLATE_ID: "${MSG91_TEMPLATE_ID}"
  JWT_SECRET: "${JWT_SECRET}"
  RAZORPAY_KEY_ID: "${RAZORPAY_KEY_ID}"
  RAZORPAY_KEY_SECRET: "${RAZORPAY_KEY_SECRET}"
EOF

chmod 0600 "$OUT"
echo "Wrote ${OUT} (gitignored). Apply with: kubectl apply -f k8s/secrets.yaml"
