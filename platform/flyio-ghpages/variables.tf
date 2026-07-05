# variables.tf — inputs for the Fly.io + GitHub Pages platform root.
#
# Secrets are NEVER given defaults and NEVER hardcoded. Sensitive values are read
# from the environment as TF_VAR_<name> (e.g. TF_VAR_fly_github_actions_token).
# terraform.tfvars.example lists placeholder NAMES only.

# ── GCP (real google-provider resources) ────────────────────────────────────
variable "gcp_project_id" {
  description = "GCP project that owns meesell-fly-sa + the asset buckets. Same project as /terraform."
  type        = string
  default     = "project-1f5cbf72-2820-4cdb-949"
}

variable "gcp_region" {
  description = "GCP region (provider default; the SA + IAM are global/multi-region)."
  type        = string
  default     = "asia-south1"
}

variable "fly_sa_account_id" {
  description = "Account ID (local part) of the SA whose key is base64'd into the Fly GCS_SA_KEY_B64 secret."
  type        = string
  default     = "meesell-fly-sa"
}

variable "fly_sa_display_name" {
  description = "Display name for the Fly SA."
  type        = string
  default     = "MeeSell Fly.io workload SA"
}

variable "gcs_buckets" {
  description = "Buckets on which the Fly SA holds roles/storage.objectAdmin (backend/app/adapters/gcs.py)."
  type        = list(string)
  default     = ["meesell-dev", "meesell-images", "meesell-prod-assets"]
}

variable "manage_sa_key" {
  description = <<-EOT
    When false (DEFAULT, adoption-safe): Terraform manages ONLY the SA + bucket IAM.
    The live SA key already exists (created out-of-band, already base64'd into the Fly
    secret GCS_SA_KEY_B64) and is left untouched — adoption creates NO second key.
    When true: Terraform creates a NEW key and (if push_sa_key_to_fly) stages it into
    the Fly GCS_SA_KEY_B64 secret. Use ONLY for a deliberate key ROTATION. The key
    material then lives in local state → keep state encrypted at rest.
  EOT
  type        = bool
  default     = false
}

variable "push_sa_key_to_fly" {
  description = "When manage_sa_key = true, also stage the new key into the Fly GCS_SA_KEY_B64 secret via the flyctl shim."
  type        = bool
  default     = false
}

# ── Fly.io (flyctl shim — no provider) ──────────────────────────────────────
variable "fly_app_name" {
  description = "Fly.io app name (LIVE). The shim create-if-absent target."
  type        = string
  default     = "meesell-api"
}

variable "fly_region" {
  description = "Fly.io primary region."
  type        = string
  default     = "bom"
}

variable "fly_org" {
  description = "Fly.io org that owns the app."
  type        = string
  default     = "personal"
}

variable "secrets_revision" {
  description = <<-EOT
    Monotonic integer. Bump it to force the fly_secrets shim to re-stage secrets on
    the next apply (terraform_data replace trigger). No secret VALUES live in state —
    only this counter does; values are passed to flyctl from the environment.
  EOT
  type        = number
  default     = 1
}

# Fly secrets to (re)stage from the environment. Only NON-EMPTY vars are set; leave a
# var unset/"" and the shim skips it (so an adoption run stages nothing new). These map
# 1:1 to `flyctl secrets set <KEY>=...`. Values come from TF_VAR_fly_secret_* env vars.
variable "fly_secret_jwt_secret" {
  type      = string
  default   = ""
  sensitive = true
}
variable "fly_secret_refresh_token_pepper" {
  type      = string
  default   = ""
  sensitive = true
}
variable "fly_secret_gemini_api_key" {
  type      = string
  default   = ""
  sensitive = true
}
variable "fly_secret_msg91_auth_key" {
  type      = string
  default   = ""
  sensitive = true
}
variable "fly_secret_razorpay_key_id" {
  type      = string
  default   = ""
  sensitive = true
}
variable "fly_secret_razorpay_key_secret" {
  type      = string
  default   = ""
  sensitive = true
}

# ── GitHub (integrations/github provider) ───────────────────────────────────
variable "github_owner" {
  description = "GitHub account/org that owns the repo."
  type        = string
  default     = "Mugunthan93"
}

variable "github_repo" {
  description = "Repository name (data source only — Terraform never manages/deletes the repo)."
  type        = string
  default     = "mesell"
}

variable "github_pages_build_type" {
  description = "GitHub Pages build type. 'workflow' = actions/deploy-pages (the LIVE config); 'legacy' = branch."
  type        = string
  default     = "workflow"
}

variable "manage_pages_shim" {
  description = "When true, the terraform_data shim PUTs the Pages build_type via `gh api`. When false, Pages is left as-is."
  type        = bool
  default     = true
}

variable "fly_github_actions_token" {
  description = <<-EOT
    Value of the FLY_API_TOKEN GitHub Actions secret (used by ci.yml deploy-backend).
    Read from TF_VAR_fly_github_actions_token. On adoption you import the existing
    secret, then set this to the SAME token so the first apply is an idempotent re-set.
    NEVER commit the value.
  EOT
  type        = string
  default     = ""
  sensitive   = true
}

variable "frontend_url" {
  description = "Public GitHub Pages URL of the shell (output contract: frontend_url)."
  type        = string
  default     = "https://mugunthan93.github.io/mesell/"
}

variable "api_base_url" {
  description = "Public Fly.io API base URL (output contract: api_base_url; matches environment.prod.ts apiBase)."
  type        = string
  default     = "https://meesell-api.fly.dev"
}
