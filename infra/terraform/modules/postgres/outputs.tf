# Purpose: Outputs for the postgres module.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §10 (outputs).

output "service_hostname" {
  value       = "postgres.${var.namespace}.svc.cluster.local"
  description = "In-cluster DNS hostname for PostgreSQL. Use as DATABASE_URL host in backend config."
}

output "secret_name" {
  value       = kubernetes_secret.postgres_credentials.metadata[0].name
  description = "Kubernetes Secret name containing postgres credentials (username, password, database)."
}
