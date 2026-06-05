# Purpose: Outputs for the artifact_registry module.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §10, §20.1.

output "repository_id" {
  description = "The Artifact Registry repository ID. Used by CI to construct the image push URL."
  value       = google_artifact_registry_repository.meesell_prod_images.repository_id
}

output "repository_url" {
  description = "Full Docker push/pull URL for the repository. Format: <location>-docker.pkg.dev/<project>/<repository_id>. Use this as the image base URL in .gitlab-ci.yml and K8s manifests."
  value       = "asia-south1-docker.pkg.dev/project-1f5cbf72-2820-4cdb-949/${google_artifact_registry_repository.meesell_prod_images.repository_id}"
}
