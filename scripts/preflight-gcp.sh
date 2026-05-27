#!/usr/bin/env bash
# Run before `terraform apply` to confirm gcloud is pointed at
# vaishnaviramoorthy@gmail.com (the account with the free GCP credit).
#
# Exits non-zero if anything's off so you can chain it as:
#
#     scripts/preflight-gcp.sh && cd terraform && terraform apply
set -euo pipefail

EXPECTED_ACCOUNT="${EXPECTED_GCP_ACCOUNT:-vaishnaviramoorthy@gmail.com}"
PROJECT_ID="${PROJECT_ID:-}"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "FAIL: gcloud CLI not found. Install: https://cloud.google.com/sdk/docs/install" >&2
  exit 1
fi

ACTIVE_ACCOUNT="$(gcloud config list account --format='value(core.account)' 2>/dev/null || true)"
if [ -z "$ACTIVE_ACCOUNT" ]; then
  echo "FAIL: no active gcloud account. Run: gcloud auth login $EXPECTED_ACCOUNT" >&2
  exit 1
fi
if [ "$ACTIVE_ACCOUNT" != "$EXPECTED_ACCOUNT" ]; then
  echo "FAIL: active gcloud account is '$ACTIVE_ACCOUNT', expected '$EXPECTED_ACCOUNT'." >&2
  echo "  Fix: gcloud config set account $EXPECTED_ACCOUNT" >&2
  exit 1
fi
echo "OK: active gcloud account = $ACTIVE_ACCOUNT"

# Application Default Credentials — what Terraform actually uses.
if ! gcloud auth application-default print-access-token --quiet >/dev/null 2>&1; then
  echo "FAIL: no application-default credentials. Run: gcloud auth application-default login" >&2
  exit 1
fi
echo "OK: application-default credentials present"

ACTIVE_PROJECT="$(gcloud config list project --format='value(core.project)' 2>/dev/null || true)"
if [ -z "$PROJECT_ID" ]; then
  PROJECT_ID="$ACTIVE_PROJECT"
fi
if [ -z "$PROJECT_ID" ]; then
  echo "FAIL: no project set. Run: gcloud config set project <ID>" >&2
  echo "      (or export PROJECT_ID=<ID> before re-running this script)" >&2
  exit 1
fi
echo "OK: project = $PROJECT_ID"

# Verify the project actually belongs to this account.
if ! gcloud projects describe "$PROJECT_ID" >/dev/null 2>&1; then
  echo "FAIL: project '$PROJECT_ID' is not accessible to $ACTIVE_ACCOUNT." >&2
  echo "  Available projects:" >&2
  gcloud projects list --format='value(projectId)' | sed 's/^/    /' >&2
  exit 1
fi

# Verify billing is enabled (free credit binds to a billing account).
BILLING_STATUS="$(gcloud billing projects describe "$PROJECT_ID" \
  --format='value(billingEnabled)' 2>/dev/null || true)"
case "$BILLING_STATUS" in
  True|true)
    BILLING_ACCOUNT="$(gcloud billing projects describe "$PROJECT_ID" \
      --format='value(billingAccountName)' 2>/dev/null || true)"
    echo "OK: billing enabled ($BILLING_ACCOUNT)"
    ;;
  *)
    echo "FAIL: project '$PROJECT_ID' has no billing account linked." >&2
    echo "  Free credit lives on a billing account, not a project. Link it with:" >&2
    echo "    gcloud billing accounts list" >&2
    echo "    gcloud billing projects link $PROJECT_ID --billing-account=<BILLING_ACCOUNT_ID>" >&2
    exit 1
    ;;
esac

# Quota project on ADC.
ADC_QUOTA_PROJECT="$(gcloud auth application-default print-access-token \
  --quiet >/dev/null 2>&1 && \
  gcloud config list billing/quota_project --format='value(billing.quota_project)' \
  2>/dev/null || true)"
if [ -n "$ADC_QUOTA_PROJECT" ] && [ "$ADC_QUOTA_PROJECT" != "$PROJECT_ID" ]; then
  echo "WARN: ADC quota project ('$ADC_QUOTA_PROJECT') != target project. Fix with:" >&2
  echo "    gcloud auth application-default set-quota-project $PROJECT_ID" >&2
fi

cat <<EOF

All checks passed. Ready to:
    cd terraform
    terraform init
    terraform plan -var="project_id=$PROJECT_ID"
    terraform apply -var="project_id=$PROJECT_ID"
EOF
