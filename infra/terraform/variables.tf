# Purpose: Root-level variable declarations for the mesell/infra/terraform/ workspace.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §10 (variables and outputs).
# Note: project_id and billing_account_id are NOT declared here — they are hardcoded
#       constants in providers.tf and modules/billing_budget/main.tf respectively
#       (Section 19, Layer A). This removes the attack surface of a misrouted apply.

# --- VM ---

variable "vm_name" {
  type        = string
  default     = "meesell-dev"
  description = "GCP Compute instance name. Must match the name in playbook §2.2. Do not change without founder approval."
}

variable "machine_type" {
  type        = string
  default     = "e2-standard-2"
  description = "GCP machine type for the K3s host VM."
}

variable "vm_disk_size_gb" {
  type        = number
  default     = 30
  description = "Boot disk size in GB. Must be >= 30 (pd-balanced, Ubuntu 22.04 LTS)."

  validation {
    condition     = var.vm_disk_size_gb >= 30
    error_message = "Boot disk must be at least 30 GB per playbook §2.2."
  }
}

# --- Networking ---

variable "founder_ip_ranges" {
  type        = list(string)
  description = "ISP CIDR ranges allowed to reach the K3s API (tcp:6443). Use ISP-level blocks (not /32) so dynamic IP rotation within the ISP requires no terraform apply. Must not include 0.0.0.0/0. Set in dev.tfvars — no CLI override needed."

  validation {
    condition     = length(var.founder_ip_ranges) > 0 && !contains(var.founder_ip_ranges, "0.0.0.0/0")
    error_message = "founder_ip_ranges must be a non-empty list and must not contain 0.0.0.0/0. Playbook §2.3 [DANGER] prohibits opening tcp:6443 to the world."
  }
}

# --- Environment ---

variable "environment" {
  type        = string
  default     = "dev"
  description = "Target environment label (dev, staging, prod). Controls resource labels and namespace routing."

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

# --- Domain / TLS ---

variable "domain" {
  type        = string
  default     = ""
  description = "Purchased domain name (e.g. meesell.in). Empty string = skip ingress and TLS wiring. Set after domain is purchased."
}

variable "acme_email" {
  type        = string
  default     = "vaishnaviramoorthy@gmail.com"
  description = "Email address for Let's Encrypt ACME registration (cert-manager ClusterIssuer)."
}

# --- Pass 2 Kubernetes workload configuration ---

variable "namespaces" {
  type        = map(string)
  default     = { dev = "dev", staging = "staging" }
  description = "Map of namespace name → env label to create. Passed to module.namespaces. prod excluded until Week 2 per playbook §15(c)."
}

variable "postgres_image_tag" {
  type        = string
  default     = "16"
  description = "PostgreSQL image tag. Must be '16' per CLAUDE.md tech stack decision. Do not change without founder approval."
}

variable "valkey_image_tag" {
  type        = string
  default     = "8"
  description = "Valkey image tag. Must be '8' per CLAUDE.md tech stack decision. Do not change without founder approval."
}

variable "supabase_studio_image_tag" {
  type        = string
  default     = "latest"
  description = "Supabase Studio image tag. 'latest' is acceptable for admin UI tooling (not a data-path service)."
}

variable "traefik_chart_version" {
  type        = string
  default     = "28.3.0"
  description = "Traefik Helm chart version pin. Passed to module.traefik_stack."
}

# --- Storage sizes (Pass 2 Kubernetes workloads) ---

variable "postgres_storage_gb" {
  type        = number
  default     = 20
  description = "Postgres PVC size in GB. Used by module.postgres in Pass 2."
}

variable "valkey_storage_gb" {
  type        = number
  default     = 5
  description = "Valkey PVC size in GB. Used by module.valkey in Pass 2."
}

# --- Secrets (Pass 2 — declared here so they can be passed at first apply) ---

variable "postgres_password" {
  type        = string
  sensitive   = true
  default     = null
  description = "Postgres password. Injected once at first Pass 2 apply via -var flag. Generated with: openssl rand -base64 32. Stored at ~/.meesell-secrets/dev-postgres-password. Never committed."
}

variable "valkey_password" {
  type        = string
  sensitive   = true
  default     = null
  description = "Valkey password. Same generation and storage pattern as postgres_password."
}

# --- Kubernetes (Pass 2) ---

variable "kubeconfig_path" {
  type        = string
  default     = "~/.kube/meesell-dev.yaml"
  description = "Absolute path to the K3s kubeconfig on the founder's laptop. Retrieved via playbook §3.3 after Pass 1. Used by kubernetes and helm providers in Pass 2."
}

variable "namespaces_to_create" {
  type        = list(string)
  default     = ["dev", "staging"]
  description = "Kubernetes namespaces to create in Pass 2. prod is excluded until Week 2 per playbook §15(c)."
}

# --- Supporting infrastructure ---

variable "gcs_asset_bucket_name" {
  type        = string
  default     = "meesell-prod-assets"
  description = "GCS asset bucket name. Must be globally unique across all GCP accounts. Default should be available; override in tfvars if collision occurs. Terraform apply will fail fast with a clear error if name is taken."
}

variable "artifact_registry_repo_id" {
  type        = string
  default     = "meesell-prod-images"
  description = "Artifact Registry repository ID for production Docker images. Isolated from the R&D registry meesell-images."
}

variable "ci_service_account_id" {
  type        = string
  default     = "meesell-prod-ci"
  description = "Short service account ID for the GitLab CI pipeline identity. Full email will be meesell-prod-ci@project-1f5cbf72-2820-4cdb-949.iam.gserviceaccount.com."
}

variable "gitlab_repository_path" {
  type        = string
  default     = "techades/mesell"
  description = "GitLab repository path for Workload Identity Federation attribute condition. Restricts WIF impersonation to CI jobs in this specific repository. Confirm with founder (Q9 — non-blocking default)."
}

variable "app_secret_ids" {
  type = list(string)
  default = [
    "gemini-api-key",
    "msg91-auth-key",
    "jwt-secret",
    "razorpay-key-id",
    "razorpay-key-secret",
  ]
  description = "Secret Manager secret IDs to create as empty containers. Maps 1:1 to backend/.env.example: GEMINI_API_KEY, MSG91_AUTH_KEY, JWT_SECRET, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET. Values populated manually by founder after Pass 1 per plan §20.4."
}

variable "gcp_api_services" {
  type = list(string)
  default = [
    "compute.googleapis.com",
    "artifactregistry.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "sts.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com",
    "billingbudgets.googleapis.com",
    # cloudbilling.googleapis.com is required as a quota-project prerequisite for
    # google_billing_budget (billingbudgets API). Without it the budget creation returns
    # 403 "Cloud Billing API has not been used in project". It is distinct from
    # billingbudgets.googleapis.com, which manages the budget resources themselves.
    "cloudbilling.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    # Phase E additions (2026-06-10):
    # - cloudbuild: required for `gcloud builds submit` from GitHub Actions. Already
    #   enabled out-of-band during Phase D (image builds); adding here adopts the API
    #   into TF state. Apply is idempotent (no-op for already-enabled APIs).
    # - iap: required for `gcloud compute start-iap-tunnel` from the deploy job.
    "cloudbuild.googleapis.com",
    "iap.googleapis.com",
  ]
  description = "GCP APIs to enable via google_project_service in apis.tf. Applied before any module. cloudresourcemanager.googleapis.com is added here to ensure the data.google_project data source in main.tf resolves cleanly. cloudbuild + iap added in Phase E to support GitHub Actions image builds and IAP-tunneled deploys."
}

# --- Billing ---

variable "budget_amount_inr" {
  type        = number
  default     = 25000
  description = "Monthly budget cap in INR for the GCP billing budget. The billing account 01620D-6785AB-0E4698 is INR-denominated (confirmed via Cloud Billing API). ₹25,000 ≈ $300 = free-credit equivalent. Alerts fire at 50%, 75%, and 90% consumed."
}

# --- GitHub Actions WIF (Phase E — 2026-06-10) ---
# Spec: docs/DEVOPS_ARCHITECTURE.md §4. Defaults are repository-specific and
# expected to be the right values for V1; override in dev.tfvars if needed.

variable "github_repository" {
  type        = string
  default     = "Mugunthan93/mesell"
  description = "GitHub repository path used in the GitHub Actions WIF attribute condition and impersonation member string. Format: <owner>/<repo>. Restricts WIF token exchange to GitHub Actions runs in this specific repository only. A workflow in any other repo cannot exchange a token for meesell-github-ci."
}

variable "github_ci_service_account_id" {
  type        = string
  default     = "meesell-github-ci"
  description = "Short service account ID for the GitHub Actions CI identity. Full email will be meesell-github-ci@project-1f5cbf72-2820-4cdb-949.iam.gserviceaccount.com. SEPARATE from var.ci_service_account_id (which is meesell-prod-ci, the GitLab SA) per founder decision D6 (2026-06-09). A compromise of either CI surface cannot affect the other."
}
