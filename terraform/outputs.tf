output "vm_name" {
  description = "GCE instance name."
  value       = google_compute_instance.vm.name
}

output "vm_external_ip" {
  description = "Static external IP attached to the VM. Point your DNS A records here if manage_dns = false."
  value       = google_compute_address.static.address
}

output "ssh_command" {
  description = "Copy/paste SSH command."
  value       = "ssh ${var.ssh_user}@${google_compute_address.static.address}"
}

output "bucket_name" {
  description = "GCS bucket for image originals, processed images, exports, and backups."
  value       = google_storage_bucket.assets.name
}

output "artifact_registry_url" {
  description = "Docker image prefix. Tag api/frontend images here before pushing."
  value       = local.registry_url
}

output "workload_service_account" {
  description = "Service account attached to the VM. All workloads inherit it via the metadata server."
  value       = google_service_account.workload.email
}

output "secret_ids" {
  description = "Secret Manager secret IDs the workload SA can read."
  value = {
    for k, s in google_secret_manager_secret.secret : k => s.secret_id
  }
}

output "dns_name_servers" {
  description = "NS records for the Cloud DNS zone — set these at your registrar. Empty list when manage_dns = false."
  value       = var.manage_dns ? google_dns_managed_zone.primary[0].name_servers : []
}

output "registry_docker_login_hint" {
  description = "Run this on your laptop to authenticate `docker push` against Artifact Registry."
  value       = "gcloud auth configure-docker ${var.region}-docker.pkg.dev"
}

output "ci_workload_identity_provider" {
  description = "Full WIF provider resource name. Set as GitHub Actions variable GCP_WIF_PROVIDER."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "ci_service_account_email" {
  description = "Set as GitHub Actions variable GCP_CI_SA_EMAIL."
  value       = google_service_account.ci.email
}

output "cloud_build_service_account_email" {
  description = "Default Cloud Build SA. Audit only — CI does not need this value."
  value       = "${data.google_project.this.number}-compute@developer.gserviceaccount.com"
}

output "next_steps" {
  description = "Post-apply checklist."
  value       = <<-EOT
    1) Point your registrar's NS records at:
       ${join(", ", var.manage_dns ? google_dns_managed_zone.primary[0].name_servers : ["(manage_dns disabled)"])}
    2) Build + push images from your workstation:
         gcloud auth configure-docker ${var.region}-docker.pkg.dev
         export PROJECT_ID=${var.project_id}
         make build deploy   (or push manually)
    3) SSH in and bring up the cluster:
         ssh ${var.ssh_user}@${google_compute_address.static.address}
         git clone https://github.com/Mugunthan93/mesell.git ~/mesell
         cd ~/mesell
         scripts/secrets-from-gcp.sh          # materialises k8s/secrets.yaml
         sudo bash scripts/setup-vm.sh        # installs K3s + applies manifests
    4) Once api pods are Ready, run the DB migration:
         kubectl -n meesell exec deploy/api -- alembic upgrade head
  EOT
}
