# Purpose: Variable declarations for the ci_identity module.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §9, §10, §20.3.

variable "service_account_id" {
  type        = string
  description = "Short service account ID (the part before the @). Full email is <id>@project-1f5cbf72-2820-4cdb-949.iam.gserviceaccount.com. Root default: meesell-prod-ci."
}

variable "gitlab_repository_path" {
  type        = string
  description = "GitLab repository path used in the WIF attribute condition and impersonation member string. Format: <group>/<repo> (e.g., techades/mesell). Restricts WIF token exchange to CI jobs in this specific repository only. Root default: techades/mesell — confirm with founder (Q9, non-blocking)."
}

variable "asset_bucket_name" {
  type        = string
  description = "GCS asset bucket name used to scope the CI service account's storage.objectAdmin IAM binding to the production asset bucket only. Passed from root via var.gcs_asset_bucket_name."
}

# --- GitHub Actions WIF (Phase E — 2026-06-10) ---

variable "github_repository" {
  type        = string
  description = "GitHub repository path used in the GitHub WIF attribute condition and impersonation member string. Format: <owner>/<repo> (e.g., Mugunthan93/mesell). Restricts WIF token exchange to GitHub Actions runs in this specific repository only. Root default: Mugunthan93/mesell."
}

variable "github_ci_service_account_id" {
  type        = string
  description = "Short service account ID for the GitHub Actions CI identity. Full email is <id>@project-1f5cbf72-2820-4cdb-949.iam.gserviceaccount.com. Root default: meesell-github-ci. SEPARATE from var.service_account_id (which is meesell-prod-ci, the GitLab SA) per founder decision D6 (2026-06-09)."
}

variable "vm_name_for_iap" {
  type        = string
  description = "GCP Compute instance name to bind compute.instanceAdmin.v1 to (resource-level scope, not project-level). Must match module.vm.vm_name. Used so the GitHub CI SA can SSH to ONLY this VM via IAP tunnel, not any other instance in the project."
}
