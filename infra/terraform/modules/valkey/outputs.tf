# Purpose: Outputs for the valkey module.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §10 (outputs).

output "service_hostname" {
  value       = "valkey.${var.namespace}.svc.cluster.local"
  description = "In-cluster DNS hostname for Valkey. Use as VALKEY_URL host in backend config (redis:// protocol)."
}

output "secret_name" {
  value       = kubernetes_secret.valkey_credentials.metadata[0].name
  description = "Kubernetes Secret name containing the Valkey password."
}
