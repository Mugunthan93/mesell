# Purpose: Variable values for the staging environment.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §5 (environment strategy), §15(b).
# Day 7 deployment — see Plan §15(b).
# Staging runs on the same VM and K3s cluster as dev (single-node per MVP scope).
# The staging namespace is created on Day 1 alongside dev (namespaces_to_create includes both).
# Staging workloads (StatefulSets, Deployments) are deployed in Pass 2 of Day 7.
# Prerequisites: dev has been running cleanly for the full development period.

environment = "staging"
vm_name     = "meesell-dev"

# Same VM — staging shares the single-node K3s cluster
machine_type    = "e2-standard-2"
vm_disk_size_gb = 30

# Kubernetes storage mirrors dev for staging parity
postgres_storage_gb = 20
valkey_storage_gb   = 5

# Domain — empty until domain is purchased; will be updated when cert-manager is wired
domain     = ""
acme_email = "vaishnaviramoorthy@gmail.com"

# Both namespaces included so Terraform detects dev as a no-op and creates staging workloads
namespaces_to_create = ["dev", "staging"]

# Supporting infrastructure — same production resources (single registry, single bucket)
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
