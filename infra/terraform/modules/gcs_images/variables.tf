# Purpose: Variable declarations for the gcs_images module (image-precheck feature).
# Plan reference: docs/plans/features/image-precheck/FEATURE_PLAN.md §Code surfaces / Infra.

variable "bucket_name" {
  type        = string
  description = "GCS bucket name for product images. Must be globally unique across ALL GCP accounts. Feature default: meesell-images. If taken by another GCP customer, terraform apply fails with a 409 Conflict — override in environments/dev.tfvars with a unique suffix."
}

variable "workload_service_account_email" {
  type        = string
  description = "Email of the service account the api/worker pods run as (via GCE metadata ADC). In this K3s-on-GCE cluster that is the Compute Engine default SA 888244156264-compute@developer.gserviceaccount.com. Receives bucket-scoped roles/storage.objectAdmin on meesell-images."
}

variable "environment" {
  type        = string
  default     = "dev"
  description = "Environment label applied as a GCS bucket label (dev, staging, prod). Root passes var.environment so the label tracks the active env."
}
