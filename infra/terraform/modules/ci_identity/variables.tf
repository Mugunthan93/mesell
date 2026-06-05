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
