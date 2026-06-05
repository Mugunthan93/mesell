# Purpose: Variable values for the production environment.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §5 (environment strategy), §15(c).
# DO NOT APPLY before staging passes one full week of acceptance per Plan §15(c) and Playbook §0.
# Prerequisites:
#   - Staging namespace has been running for >= 7 days.
#   - Section 14 acceptance checklist (adapted for staging) is fully ticked.
#   - Founder has explicitly approved prod namespace creation in the current session.
#   - Fresh passwords generated: openssl rand -base64 32 > ~/.meesell-secrets/prod-postgres-password
#     DO NOT reuse dev or staging passwords.

environment = "prod"
vm_name     = "meesell-dev"

# Same VM — prod shares the single-node K3s cluster for MVP
machine_type    = "e2-standard-2"
vm_disk_size_gb = 30

# Kubernetes storage — same as dev/staging for MVP single-node cluster
postgres_storage_gb = 20
valkey_storage_gb   = 5

# Domain — must be set before prod apply; prod without TLS is not acceptable
domain     = ""
acme_email = "vaishnaviramoorthy@gmail.com"

# All three namespaces included; Terraform detects dev and staging as no-ops
namespaces_to_create = ["dev", "staging", "prod"]

# Supporting infrastructure — same production resources
gcs_asset_bucket_name     = "meesell-prod-assets"
artifact_registry_repo_id = "meesell-prod-images"
ci_service_account_id     = "meesell-prod-ci"
gitlab_repository_path    = "techades/mesell"

app_secret_ids = [
  "gemini-api-key",
  "msg91-auth-key",
  "jwt-secret",
  "razorpay-key-id",
  "razorpay-key-secret",
]

budget_amount_usd = 300
