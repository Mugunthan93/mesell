# Purpose: Outputs for the cloudbuild_permissions module.
# These outputs let callers (root + CI/CD) reference the bound role in error messages
# and CI verification scripts without re-typing the values.

output "cloudbuild_bucket_iam_member_etag" {
  description = "Etag of the storage.admin IAM binding on the Cloud Build source bucket. Used for drift detection in CI."
  value       = google_storage_bucket_iam_member.cloudbuild_bucket_compute_sa_admin.etag
}

output "artifact_registry_iam_member_etag" {
  description = "Etag of the artifactregistry.writer IAM binding on meesell-prod-images. Used for drift detection in CI."
  value       = google_artifact_registry_repository_iam_member.meesell_prod_images_compute_sa_writer.etag
}
