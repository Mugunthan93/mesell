# Purpose: Outputs for the supabase_studio module.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §10 (outputs).

output "service_name" {
  value       = kubernetes_service.supabase_studio.metadata[0].name
  description = "Kubernetes Service name for Supabase Studio."
}

output "service_port" {
  value       = 3000
  description = "Port exposed by the Supabase Studio Service."
}
