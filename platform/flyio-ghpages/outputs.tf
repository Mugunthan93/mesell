# outputs.tf — the SYMMETRIC OUTPUT CONTRACT.
#
# Both platform roots expose the same four named outputs so a caller can switch
# platforms by pointing at a different root and reading identical keys:
#   platform · api_base_url · frontend_url · deploy_notes
#
# The GCP root (/terraform) predates this contract and is NOT modified (hard
# constraint). platform/README.md documents the GCP-side equivalents:
#   api_base_url ← https://api.mesell.xyz (Traefik ingress) ; frontend_url ←
#   https://dev.mesell.xyz ; both derived from /terraform output vm_external_ip.

output "platform" {
  description = "Which platform this root provisions."
  value       = "flyio-ghpages"
}

output "api_base_url" {
  description = "Public API base URL (Fly.io). Matches frontend environment.prod.ts apiBase."
  value       = var.api_base_url
}

output "frontend_url" {
  description = "Public frontend URL (GitHub Pages shell)."
  value       = var.frontend_url
}

output "deploy_notes" {
  description = "How code actually ships on this platform + the app-layer switch surface."
  value       = <<-EOT
    Backend  : Fly.io app "${var.fly_app_name}" (region ${var.fly_region}), deployed by
               .github/workflows/ci.yml deploy-backend (flyctl deploy --dockerfile
               Dockerfile.fly). DB = Fly Postgres meesell-db; cache = Upstash meesell-cache.
    Frontend : GitHub Pages (build_type=${var.github_pages_build_type}) via
               .github/workflows/deploy-frontend.yml → https://mugunthan93.github.io/mesell/
    GCS auth : Fly reads GCS via the base64 SA key in the Fly secret GCS_SA_KEY_B64
               (backend/app/adapters/gcs.py falls back to ADC on GCE/K3s).
    Switch   : see platform/README.md → "SWITCH CHECKLIST" for the full coupling surface
               (apiBase, federation.manifest.json, CORS/cookie secrets, CI job toggles).
  EOT
}

# ── Non-contract, operationally useful ──────────────────────────────────────
output "gcp_fly_sa_email" {
  description = "Email of the Fly workload SA whose key is base64'd into GCS_SA_KEY_B64."
  value       = google_service_account.fly.email
}

output "gcs_buckets_granted" {
  description = "Buckets on which the Fly SA holds roles/storage.objectAdmin."
  value       = var.gcs_buckets
}

output "gcp_fly_sa_key_b64" {
  description = "Base64 SA key — ONLY populated when manage_sa_key = true (rotation). Feed to `fly secrets set GCS_SA_KEY_B64=...`."
  value       = var.manage_sa_key ? google_service_account_key.fly[0].private_key : null
  sensitive   = true
}
