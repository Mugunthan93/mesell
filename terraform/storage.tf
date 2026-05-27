resource "google_storage_bucket" "assets" {
  name                        = local.bucket_name
  location                    = var.bucket_location
  force_destroy               = var.bucket_force_destroy
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  labels                      = var.labels

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age        = 90
      with_state = "ARCHIVED"
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.enabled]
}

# Workload SA reads + writes its own objects (originals, processed, exports, backups).
resource "google_storage_bucket_iam_member" "workload_object_admin" {
  bucket = google_storage_bucket.assets.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.workload.email}"
}
