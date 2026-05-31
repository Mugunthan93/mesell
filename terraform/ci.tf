# ---------------------------------------------------------------------------
# CI/CD identity plane — GitHub Actions → Workload Identity Federation → GCP
#
# GitHub Actions emits a signed OIDC JWT per job. We register a WIF pool +
# GitHub OIDC provider, create a dedicated meesell-ci SA, and bind it so
# only jobs from github.com/Mugunthan93/mesell can impersonate it.
# No SA key files are created (org policy enforced).
# ---------------------------------------------------------------------------

data "google_project" "this" {
  project_id = var.project_id
}

# WIF pool — container for GitHub federation
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-pool"
  display_name              = "GitHub Actions Pool"
  description               = "Federated identity for GitHub Actions CI jobs."
  depends_on                = [google_project_service.enabled]
}

# WIF provider — trusts tokens from github.com, scoped to this repo
resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-oidc"
  display_name                       = "GitHub Actions OIDC"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }

  # Only jobs from THIS GitHub repo can exchange tokens
  attribute_condition = "attribute.repository == \"${var.github_repository}\""

  oidc {
    issuer_uri = var.github_issuer_uri
  }
}

# Dedicated CI service account — minimum permissions only
resource "google_service_account" "ci" {
  account_id   = "${var.name_prefix}-ci"
  display_name = "MeeSell CI service account"
  description  = "Impersonated by GitHub Actions via Workload Identity Federation. Push images + deploy via IAP SSH."
  depends_on   = [google_project_service.enabled]
}

# Allow tokens from our GitHub repo to impersonate the CI SA
resource "google_service_account_iam_member" "ci_wif_binding" {
  service_account_id = google_service_account.ci.name
  role               = "roles/iam.workloadIdentityUser"
  member = format(
    "principalSet://iam.googleapis.com/%s/attribute.repository/%s",
    google_iam_workload_identity_pool.github.name,
    var.github_repository,
  )
}

# Push images to Artifact Registry — scoped to meesell-images repo only
resource "google_artifact_registry_repository_iam_member" "ci_ar_writer" {
  project    = var.project_id
  location   = google_artifact_registry_repository.images.location
  repository = google_artifact_registry_repository.images.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.ci.email}"
}

# Cloud Build default SA needs to push to Artifact Registry
resource "google_artifact_registry_repository_iam_member" "cloudbuild_ar_writer" {
  project    = var.project_id
  location   = google_artifact_registry_repository.images.location
  repository = google_artifact_registry_repository.images.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${data.google_project.this.number}-compute@developer.gserviceaccount.com"
}

# CI SA can submit + poll Cloud Build jobs
resource "google_project_iam_member" "ci_cloudbuild_editor" {
  project = var.project_id
  role    = "roles/cloudbuild.builds.editor"
  member  = "serviceAccount:${google_service_account.ci.email}"
}

# Cloud Build runs jobs under the default Compute SA. The CI SA must be able
# to "act as" that SA (serviceAccountUser) to submit builds.
resource "google_service_account_iam_member" "ci_act_as_cloudbuild" {
  service_account_id = "projects/${var.project_id}/serviceAccounts/${data.google_project.this.number}-compute@developer.gserviceaccount.com"
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.ci.email}"
}

# IAP TCP tunnel for SSH — CI SSHes to VM without storing a private key
resource "google_project_iam_member" "ci_iap_tunnel" {
  project = var.project_id
  role    = "roles/iap.tunnelResourceAccessor"
  member  = "serviceAccount:${google_service_account.ci.email}"
}

# OS Login — CI SA gets a POSIX identity on the VM without metadata ssh-keys
resource "google_project_iam_member" "ci_os_login" {
  project = var.project_id
  role    = "roles/compute.osLogin"
  member  = "serviceAccount:${google_service_account.ci.email}"
}

# Enable OS Login at project level
resource "google_compute_project_metadata_item" "enable_oslogin" {
  key   = "enable-oslogin"
  value = "TRUE"
}

# IAP forwarder source range — allows IAP TCP forwarding to port 22
resource "google_compute_firewall" "allow_ssh_iap" {
  name          = "${var.name_prefix}-allow-ssh-iap"
  network       = "default"
  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["meesell-public"]
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
  depends_on = [google_project_service.enabled]
}
