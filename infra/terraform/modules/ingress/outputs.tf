output "ingress_host" {
  description = "Studio Ingress public hostname."
  value       = "studio.${var.domain}"
}

output "cluster_issuer_name" {
  description = "Let's Encrypt ClusterIssuer name."
  value       = kubernetes_manifest.cluster_issuer_letsencrypt_prod.manifest.metadata.name
}

output "api_host" {
  description = "API Ingress public hostname."
  value       = "api.${var.domain}"
}

output "dev_frontend_host" {
  description = "Dev frontend Ingress public hostname."
  value       = "dev.${var.domain}"
}

output "testing_frontend_host" {
  description = "Testing frontend Ingress public hostname."
  value       = "testing.${var.domain}"
}

output "staging_frontend_host" {
  description = "Staging frontend Ingress public hostname."
  value       = "staging.${var.domain}"
}
