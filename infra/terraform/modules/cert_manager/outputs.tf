output "namespace" {
  description = "cert-manager namespace name."
  value       = kubernetes_namespace.cert_manager.metadata[0].name
}

output "ready_trigger" {
  description = "Sentinel for downstream depends_on (waits for CRDs to settle)."
  value       = time_sleep.cert_manager_settle.id
}
