resource "google_service_account" "workload" {
  account_id   = local.workload_sa_id
  display_name = "MeeSell workload service account"
  description  = "Attached to the VM; backend + workers + backup CronJob inherit it via the metadata server."

  depends_on = [google_project_service.enabled]
}

# Allow the workload SA to read from Artifact Registry. The VM uses the
# metadata server's access token to authenticate `docker pull` via containerd
# (see scripts/setup-vm.sh).
resource "google_project_iam_member" "workload_ar_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.workload.email}"
}

# Logs + traces.
resource "google_project_iam_member" "workload_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.workload.email}"
}

resource "google_project_iam_member" "workload_metric_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.workload.email}"
}
