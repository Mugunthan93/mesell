# Purpose: Variable values for the dev environment (Day 1 provisioning).
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §5 (environment strategy), §11 (bootstrap order).
# Note: founder_ip is intentionally NOT set here. It must be passed at apply time via the
#       FOUNDER_IP environment variable and the Makefile wrapper:
#         make -f Makefile.tf tf-plan-pass1 FOUNDER_IP=$(curl -s ifconfig.me)
#       This ensures the IP always reflects the founder's current address, never a stale value.
#       postgres_password and valkey_password are also absent — injected at first Pass 2 apply only.

environment = "dev"
vm_name     = "meesell-dev"

# VM sizing (matches playbook §2.2 locked constants)
machine_type    = "e2-standard-2"
vm_disk_size_gb = 30

# Kubernetes storage (Pass 2 — declared here for plan completeness)
postgres_storage_gb = 20
valkey_storage_gb   = 5

# Domain — empty until domain is purchased (see plan §17 Q1 resolved)
domain     = "mesell.xyz"
acme_email = "vaishnaviramoorthy@gmail.com"

# Namespaces to create in Pass 2 (prod deferred to Week 2 per playbook §15c)
namespaces_to_create = ["dev", "staging"]

# Supporting infrastructure defaults (non-blocking per plan §17 Q9, Q10)
gcs_asset_bucket_name     = "meesell-prod-assets"
artifact_registry_repo_id = "meesell-prod-images"
ci_service_account_id     = "meesell-prod-ci"
gitlab_repository_path    = "techades/mesell"

# Secret Manager containers
app_secret_ids = [
  "gemini-api-key",
  "msg91-auth-key",
  "msg91-template-id",
  "jwt-secret",
  "razorpay-key-id",
  "razorpay-key-secret",
  "audit-pii-salt",
]

# Billing budget — billing account 01620D-6785AB-0E4698 is INR-denominated.
# ₹25,000 ≈ $300, the free-tier credit amount in USD.
budget_amount_inr = 25000
