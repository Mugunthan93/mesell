#!/usr/bin/env bash
# import.sh — adopt the LIVE Fly.io + GitHub Pages estate into this root's state
# WITHOUT recreating or destroying anything.
#
# WHAT THIS DOES
#   Imports the real provider resources that already exist:
#     - google_service_account.fly                 (meesell-fly-sa)
#     - google_storage_bucket_iam_member.fly_*     (objectAdmin on 3 buckets)
#     - github_actions_secret.fly_api_token        (FLY_API_TOKEN)
#   Each import is idempotent here: if the address is already in state it is skipped.
#
# WHAT IT DOES NOT DO
#   - It does NOT import the flyctl/gh SHIMS (terraform_data.fly_app / fly_secrets /
#     pages_build_type). Those model out-of-band actions; on the first `terraform apply`
#     they "create" and run their IDEMPOTENT scripts against live infra:
#       fly_app       → detects the existing app → no-op
#       fly_secrets   → all TF_VAR_fly_secret_* empty → stages nothing
#       pages_build_type → PUTs build_type=workflow → already workflow → no-op
#     So live infra is untouched. (You may `terraform import terraform_data.fly_app
#     meesell-api` etc. if you prefer, but it buys nothing and a replace re-runs the
#     idempotent script anyway.)
#   - It does NOT import a google_service_account_key. The live key was created
#     out-of-band and its private material cannot be read back; adoption default is
#     manage_sa_key = false (no key resource exists to import).
#
# PRECONDITIONS
#   gcloud auth application-default login          # GCP ADC
#   export GITHUB_TOKEN=<PAT with repo scope>      # github provider
#   export TF_VAR_fly_github_actions_token=<same FLY_API_TOKEN value>  # for the re-set
#   terraform init                                 # local backend, downloads providers
#
# SAFETY: run `terraform plan` AFTER importing and confirm it shows NO destroy/replace
# of the imported resources before you ever `terraform apply`.
set -euo pipefail
cd "$(dirname "$0")"

PROJECT_ID="${TF_VAR_gcp_project_id:-project-1f5cbf72-2820-4cdb-949}"
SA_ID="${TF_VAR_fly_sa_account_id:-meesell-fly-sa}"
SA_EMAIL="${SA_ID}@${PROJECT_ID}.iam.gserviceaccount.com"
OWNER="${TF_VAR_github_owner:-Mugunthan93}"
REPO="${TF_VAR_github_repo:-mesell}"
BUCKETS=("meesell-dev" "meesell-images" "meesell-prod-assets")
ROLE="roles/storage.objectAdmin"

imp() { # imp <address> <id>
  if terraform state show "$1" >/dev/null 2>&1; then
    echo "[import] $1 already in state — skip."
  else
    echo "[import] $1  <=  $2"
    terraform import "$1" "$2"
  fi
}

echo "== Importing GCP service account =="
imp 'google_service_account.fly' "projects/${PROJECT_ID}/serviceAccounts/${SA_EMAIL}"

echo "== Importing bucket IAM members (objectAdmin) =="
for b in "${BUCKETS[@]}"; do
  imp "google_storage_bucket_iam_member.fly_object_admin[\"${b}\"]" \
      "b/${b} ${ROLE} serviceAccount:${SA_EMAIL}"
done

echo "== Importing GitHub Actions secret (FLY_API_TOKEN) =="
imp 'github_actions_secret.fly_api_token' "${REPO}:FLY_API_TOKEN"

cat <<DONE

Adoption imports complete. NEXT:
  1) terraform plan
     Expect: NO destroy/replace of the imported google_* + github_* resources.
     The 3 terraform_data shims will show as "to create" — that is EXPECTED and safe
     (their provisioners are idempotent no-ops against the live estate).
  2) Review, then (only when satisfied): terraform apply
DONE
