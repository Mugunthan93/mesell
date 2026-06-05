# Purpose: Outputs for the app_secrets module.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §10, §20.4.

output "secret_resource_names" {
  description = "Map of secret ID → full GCP resource name (projects/<number>/secrets/<id>). Use these names in IAM bindings that grant the backend service account access to read secret versions."
  value       = { for id, s in google_secret_manager_secret.app_secrets : id => s.name }
}
