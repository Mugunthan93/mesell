# Purpose: Variable declarations for the asset_bucket module.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §9, §10, §20.2.

variable "bucket_name" {
  type        = string
  description = "GCS bucket name. Must be globally unique across ALL GCP accounts (not just this project). Root default: meesell-prod-assets. If that name is already taken by another GCP customer, terraform apply will fail with a 409 Conflict — override in environments/dev.tfvars with a unique suffix."
}

variable "environment" {
  type        = string
  default     = "dev"
  description = "Environment label applied as a GCS object label (dev, staging, prod). Root does not pass this variable today — the default 'dev' is used. Override when the staging/prod environment tfvars are wired."
}
