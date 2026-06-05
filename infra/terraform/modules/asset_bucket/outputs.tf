# Purpose: Outputs for the asset_bucket module.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §10, §20.2.

output "bucket_name" {
  description = "The GCS bucket name. Pass this to the backend as the GCS_BUCKET environment variable (see backend/.env.example)."
  value       = google_storage_bucket.meesell_prod_assets.name
}

output "bucket_url" {
  description = "The GCS bucket URL in gs:// form (e.g. gs://meesell-prod-assets). Use for gsutil / gcloud storage commands and for storage.py signed-URL generation."
  value       = google_storage_bucket.meesell_prod_assets.url
}
