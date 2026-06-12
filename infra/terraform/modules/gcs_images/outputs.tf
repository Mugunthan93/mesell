# Purpose: Outputs for the gcs_images module.
# Plan reference: docs/plans/features/image-precheck/FEATURE_PLAN.md §Code surfaces / Infra.

output "bucket_name" {
  description = "The product-image GCS bucket name. Pass to the backend as GCS_BUCKET_IMAGES (see k8s/config.yaml + backend/app/shared/config.py)."
  value       = google_storage_bucket.meesell_images.name
}

output "bucket_url" {
  description = "The product-image GCS bucket URL in gs:// form (gs://meesell-images). Use for gsutil / gcloud storage commands and for the D2-Gate-3 tenant-isolation verification (FEATURE_PLAN §D2)."
  value       = google_storage_bucket.meesell_images.url
}
