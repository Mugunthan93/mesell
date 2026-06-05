# Purpose: Outputs for the namespaces module.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §10 (outputs).

output "namespace_names" {
  value       = [for ns in kubernetes_namespace.ns : ns.metadata[0].name]
  description = "List of Kubernetes namespace names created by this module."
}
