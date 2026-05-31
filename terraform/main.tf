provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# APIs to enable. Each is idempotent and free.
locals {
  required_services = [
    "compute.googleapis.com",
    "storage.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "dns.googleapis.com",
    "cloudbuild.googleapis.com",
    "iap.googleapis.com",
  ]
}

resource "google_project_service" "enabled" {
  for_each                   = toset(local.required_services)
  project                    = var.project_id
  service                    = each.value
  disable_dependent_services = false
  disable_on_destroy         = false
}
