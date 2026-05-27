resource "google_artifact_registry_repository" "images" {
  location      = var.region
  repository_id = local.registry_id
  format        = "DOCKER"
  description   = "MeeSell container images (api + frontend)."
  labels        = var.labels

  cleanup_policies {
    id     = "keep-last-10-prod"
    action = "KEEP"
    most_recent_versions {
      keep_count = 10
    }
  }

  cleanup_policies {
    id     = "delete-untagged"
    action = "DELETE"
    condition {
      tag_state  = "UNTAGGED"
      older_than = "604800s" # 7 days
    }
  }

  depends_on = [google_project_service.enabled]
}
