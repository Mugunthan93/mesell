# Purpose: Variable declarations for the app_secrets module.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §9, §10, §20.4.

variable "secret_ids" {
  type        = list(string)
  description = "List of Secret Manager secret IDs to create as empty containers. Values are populated manually by the founder via `gcloud secrets versions add` after terraform apply. See module main.tf for the exact gcloud command pattern. Root default includes all five app secrets."
}

variable "environment" {
  type        = string
  description = "Environment label applied to each secret's labels map (dev, staging, prod). Passed from root var.environment."
}
