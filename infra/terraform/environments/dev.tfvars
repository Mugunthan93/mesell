# Purpose: Variable values for the dev environment (Day 1 provisioning).
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §5 (environment strategy), §11 (bootstrap order).
# Note: founder_ip_ranges replaces the old per-session founder_ip /32 variable.
#       ISP CIDR ranges cover all dynamic IPs assigned by the founder's broadband/mobile ISP,
#       so K3s API access survives IP rotation without any terraform apply.
#       postgres_password and valkey_password are absent — injected at first Pass 2 apply only.
#
# ISP lookup used to derive ranges:
#   122.164.64.0/18 — Airtel TN DSL (inetnum 122.164.64.0–122.164.127.255, Bharti Airtel Chennai)
#   152.57.80.0/21  — Reliance Jio mobile hotspot (route 152.57.80.0/21, Jio Infocomm Chennai)
# If a new ISP appears: curl -s https://ipinfo.io/<ip>/json | jq .org
#                        whois <ip> | grep route  → add new CIDR to this list.

environment = "dev"
vm_name     = "meesell-dev"

# K3s API access — ISP CIDR ranges (survives dynamic IP rotation within each ISP)
founder_ip_ranges = [
  "122.164.64.0/18", # Airtel TN DSL broadband (Chennai, dynamic pool)
  "152.57.80.0/21",  # Reliance Jio mobile hotspot (Chennai, dynamic pool)
]

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
gcs_images_bucket_name    = "meesell-images" # image-precheck Feature 5 product-image bucket (1-yr lifecycle)
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
