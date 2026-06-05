#!/usr/bin/env bash
# Purpose: Identity, billing, ADC, and toolchain gate for MeeSell production Terraform.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §19 Layer E.
#
# This script is run by Makefile.tf before every state-changing terraform target.
# It is DIFFERENT from scripts/preflight-gcp.sh (the R&D workspace preflight):
#   - preflight-gcp.sh: uses `gcloud config list` (reads global gcloud config).
#                       Appropriate for the R&D workspace where global config is set.
#   - tf-preflight.sh:  uses `--account=` and `--project=` flags everywhere.
#                       Never reads or mutates global gcloud config. Safe to run
#                       while a different account is active in the terminal.
#
# Exits 0 if all checks pass (or only WARNs triggered).
# Exits 1 if any FAIL check is triggered.

set -euo pipefail

# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'   # no color

pass()  { echo -e "${GREEN}PASS${NC}  $*"; }
fail()  { echo -e "${RED}FAIL${NC}  $*" >&2; }
warn()  { echo -e "${YELLOW}WARN${NC}  $*" >&2; }

FAILURES=0

# ---------------------------------------------------------------------------
# Constants (must match providers.tf, main.tf locals, and Makefile.tf exactly)
# ---------------------------------------------------------------------------
EXPECTED_ACCOUNT="vaishnaviramoorthy@gmail.com"
EXPECTED_PROJECT="project-1f5cbf72-2820-4cdb-949"
EXPECTED_BILLING="billingAccounts/01620D-6785AB-0E4698"
MIN_TF_MAJOR=1
MIN_TF_MINOR=8

echo "--- MeeSell tf-preflight ---"
echo ""

# ---------------------------------------------------------------------------
# Check 1: gcloud auth — expected account must be ACTIVE
# Uses --account= flag, NOT global config.
# ---------------------------------------------------------------------------
echo "[1/5] Checking gcloud auth for $EXPECTED_ACCOUNT ..."
AUTH_STATUS="$(gcloud auth list \
  --filter="account:${EXPECTED_ACCOUNT}" \
  --format="value(status)" 2>/dev/null || true)"

if [ "$AUTH_STATUS" = "ACTIVE" ] || [ "$AUTH_STATUS" = "*" ]; then
  pass "gcloud auth: $EXPECTED_ACCOUNT is ACTIVE"
else
  fail "gcloud auth: $EXPECTED_ACCOUNT is not ACTIVE (observed status: '${AUTH_STATUS:-not found}')."
  fail "  Expected ACTIVE or * (asterisk indicates the active account in value() format)."
  fail "  Fix: gcloud auth login $EXPECTED_ACCOUNT"
  FAILURES=$((FAILURES + 1))
fi

# ---------------------------------------------------------------------------
# Check 2: billing account linked to the expected project
# Uses --account= flag to ensure the query runs as the locked account.
# ---------------------------------------------------------------------------
echo "[2/5] Checking billing account for project $EXPECTED_PROJECT ..."
OBSERVED_BILLING="$(gcloud --account="$EXPECTED_ACCOUNT" billing projects describe "$EXPECTED_PROJECT" \
  --format="value(billingAccountName)" 2>/dev/null || true)"

if [ "$OBSERVED_BILLING" = "$EXPECTED_BILLING" ]; then
  pass "Billing account: $OBSERVED_BILLING"
else
  fail "Billing account mismatch."
  fail "  Expected: $EXPECTED_BILLING"
  fail "  Observed: ${OBSERVED_BILLING:-not found or no access}"
  fail "  Fix: confirm project $EXPECTED_PROJECT is linked to billing account 01620D-6785AB-0E4698"
  fail "       in GCP Console → Billing, or: gcloud billing projects link $EXPECTED_PROJECT \\"
  fail "         --billing-account=01620D-6785AB-0E4698 --account=$EXPECTED_ACCOUNT"
  FAILURES=$((FAILURES + 1))
fi

# ---------------------------------------------------------------------------
# Check 3: Application Default Credentials file present
# WARN only — Terraform may fail later, but the ADC file is not strictly required
# if the user has another valid ADC path (e.g., a service account key on GOOGLE_APPLICATION_CREDENTIALS).
# Print the bootstrap command so the fix is obvious.
# ---------------------------------------------------------------------------
echo "[3/5] Checking Application Default Credentials ..."
ADC_FILE="$HOME/.config/gcloud/application_default_credentials.json"
if [ -f "$ADC_FILE" ]; then
  pass "ADC file found: $ADC_FILE"
else
  warn "ADC file not found at $ADC_FILE"
  warn "  Terraform uses ADC to authenticate GCP API calls. If GOOGLE_APPLICATION_CREDENTIALS"
  warn "  is set to a valid key file, this warning can be ignored. Otherwise run:"
  warn "    gcloud auth application-default login --account=$EXPECTED_ACCOUNT"
fi

# ---------------------------------------------------------------------------
# Check 4: Terraform version >= 1.8.0
# Uses terraform version -json; parses major and minor from the version string.
# WARN on older minor (e.g., 1.7.x), FAIL on older major (e.g., 0.x).
# ---------------------------------------------------------------------------
echo "[4/5] Checking terraform version (>= ${MIN_TF_MAJOR}.${MIN_TF_MINOR}.0) ..."
if ! command -v terraform >/dev/null 2>&1; then
  fail "terraform not found in PATH. Install via tfenv: https://github.com/tfutils/tfenv"
  FAILURES=$((FAILURES + 1))
else
  TF_VERSION_JSON="$(terraform version -json 2>/dev/null || echo '{}')"
  TF_VERSION_STRING="$(echo "$TF_VERSION_JSON" | grep '"terraform_version"' | sed 's/.*: *"\([^"]*\)".*/\1/' || true)"

  if [ -z "$TF_VERSION_STRING" ]; then
    # Fallback: parse `terraform version` plain output
    TF_VERSION_STRING="$(terraform version 2>/dev/null | head -1 | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' || true)"
  fi

  TF_MAJOR="$(echo "$TF_VERSION_STRING" | cut -d. -f1)"
  TF_MINOR="$(echo "$TF_VERSION_STRING" | cut -d. -f2)"

  if [ -z "$TF_MAJOR" ] || [ -z "$TF_MINOR" ]; then
    warn "Could not parse terraform version from: '$TF_VERSION_STRING'. Skipping version check."
  elif [ "$TF_MAJOR" -lt "$MIN_TF_MAJOR" ]; then
    fail "Terraform major version too old: $TF_VERSION_STRING (required >= ${MIN_TF_MAJOR}.${MIN_TF_MINOR}.0)"
    fail "  Install a newer version via tfenv: tfenv install ${MIN_TF_MAJOR}.${MIN_TF_MINOR}.5 && tfenv use ${MIN_TF_MAJOR}.${MIN_TF_MINOR}.5"
    FAILURES=$((FAILURES + 1))
  elif [ "$TF_MAJOR" -eq "$MIN_TF_MAJOR" ] && [ "$TF_MINOR" -lt "$MIN_TF_MINOR" ]; then
    warn "Terraform minor version below recommended: $TF_VERSION_STRING (recommended >= ${MIN_TF_MAJOR}.${MIN_TF_MINOR}.0)"
    warn "  Upgrade: tfenv install ${MIN_TF_MAJOR}.${MIN_TF_MINOR}.5 && tfenv use ${MIN_TF_MAJOR}.${MIN_TF_MINOR}.5"
  else
    pass "Terraform version: $TF_VERSION_STRING"
  fi
fi

# ---------------------------------------------------------------------------
# Check 5: FOUNDER_IP validation (only if the env var is set)
# If set, must match IPv4 pattern and must not be 0.0.0.0.
# The firewall module uses this to restrict K3s API access (tcp:6443) to the
# founder's IP only — 0.0.0.0 would open K3s API to the world ([DANGER]).
# ---------------------------------------------------------------------------
echo "[5/5] Checking FOUNDER_IP ..."
if [ -z "${FOUNDER_IP:-}" ]; then
  warn "FOUNDER_IP is not set. Targets that touch the firewall module require it."
  warn "  Set with: export FOUNDER_IP=\$(curl -s ifconfig.me)"
  warn "  Skipping IPv4 validation."
else
  IPV4_RE='^([0-9]{1,3}\.){3}[0-9]{1,3}$'
  if ! echo "$FOUNDER_IP" | grep -qE "$IPV4_RE"; then
    fail "FOUNDER_IP='$FOUNDER_IP' does not look like a valid IPv4 address."
    FAILURES=$((FAILURES + 1))
  elif [ "$FOUNDER_IP" = "0.0.0.0" ]; then
    fail "FOUNDER_IP must not be 0.0.0.0 — this would open K3s API (tcp:6443) to the world."
    fail "  [DANGER] per docs/INFRASTRUCTURE_PLAYBOOK.md §2.3 and plan §19."
    fail "  Fix: export FOUNDER_IP=\$(curl -s ifconfig.me)"
    FAILURES=$((FAILURES + 1))
  else
    pass "FOUNDER_IP: $FOUNDER_IP (valid IPv4, not 0.0.0.0)"
  fi
fi

# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------
echo ""
if [ "$FAILURES" -gt 0 ]; then
  fail "tf-preflight: $FAILURES check(s) failed. Fix the issues above and re-run."
  exit 1
else
  pass "tf-preflight: all checks passed. Ready for terraform."
  exit 0
fi
