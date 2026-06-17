# Purpose: GCS bucket for the image-precheck feature (Feature 5).
# Plan reference: docs/plans/features/image-precheck/FEATURE_PLAN.md §Code surfaces / Infra
#                 (rows 1-2). Founder-gate dispatch 2026-06-12.
#
# This is a SEPARATE bucket from meesell-prod-assets (module.asset_bucket). The
# feature plan (§Infra row 1) explicitly names the product-image bucket
# `meesell-images` with a 1-year DELETE lifecycle for the uploaded source images.
#
# NAMING NOTE — do NOT confuse with the Artifact Registry repo:
#   - variables.tf:158 describes the AR repo `meesell-prod-images` as "Isolated from
#     the R&D registry meesell-images." That `meesell-images` is an ARTIFACT REGISTRY
#     repository ID (a different GCP resource namespace).
#   - THIS resource is a GCS BUCKET named `meesell-images`. GCS bucket names and AR
#     repository IDs do not collide (separate namespaces). Verified 2026-06-12:
#     `gcloud storage buckets describe gs://meesell-images` -> 404 (name free).
#
# Choices (mirror module.asset_bucket conventions, with feature-specific lifecycle):
#   - location = "ASIA-SOUTH1": account-lock region constant (uppercased per GCS API).
#   - uniform_bucket_level_access = true: disables per-object ACLs. Required for
#     public_access_prevention = "enforced" and simplifies IAM reasoning.
#   - public_access_prevention = "enforced": no object can ever be made public.
#     Product images are served via the FastAPI backend (signed URLs), never directly
#     from GCS. Hard tenant-safety control — the D2-Gate-3 tenant-isolation check
#     (FEATURE_PLAN §D2) relies on this plus the {user_id}/ path prefix.
#   - versioning: enabled. Uploaded product images are user data; accidental
#     deletes/overwrites are recoverable.
#   - lifecycle_rule: DELETE objects after 365 days (1-year retention per FEATURE_PLAN
#     §Infra row 1). Applies bucket-wide (no prefix filter) — every uploaded source
#     image ages out after a year.
#   - force_destroy = false: `terraform destroy` will not delete a non-empty bucket.
#   - lifecycle.prevent_destroy = true: blocks accidental terraform destroy of the
#     bucket resource without a deliberate code change. Protects user image data.

resource "google_storage_bucket" "meesell_images" {
  name                        = var.bucket_name
  location                    = "ASIA-SOUTH1"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  versioning {
    enabled = true
  }

  # 1-year retention per FEATURE_PLAN §Infra row 1. Bucket-wide (no prefix filter).
  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    env     = var.environment
    project = "meesell"
    feature = "image-precheck"
  }

  lifecycle {
    prevent_destroy = true
  }
}

# Workload identity / runtime access binding.
#
# AS-BUILT REALITY (record this — the plan says "Workload Identity binding for the
# API/worker service accounts"; this cluster is K3s-on-GCE, NOT GKE Workload Identity):
#   - The api + worker pods authenticate to GCS via ADC through the GCE metadata
#     server. They therefore run AS the VM's attached service account, the Compute
#     Engine default SA `888244156264-compute@developer.gserviceaccount.com`.
#     (See k8s/worker.yaml lines 43-46: "GOOGLE_APPLICATION_CREDENTIALS absent — ADC
#     via GCE metadata server".)
#   - There is no GKE Workload Identity federation here, so the correct binding is a
#     bucket-scoped objectAdmin grant to that compute SA — exactly mirroring how
#     module.asset_bucket access is granted (verified live 2026-06-12: the compute SA
#     holds roles/storage.objectAdmin on gs://meesell-prod-assets).
#   - objectAdmin is OBJECT-scoped (read/write/delete objects), NOT bucket-admin
#     (cannot change bucket IAM/config). This satisfies FEATURE_PLAN §Infra row 2's
#     intent: "scoped to meesell-images/* (NOT bucket-level admin)".
#   - google_storage_bucket_iam_member is ADDITIVE (not _iam_binding) — it never
#     displaces the project-level legacy bindings GCS auto-creates.
resource "google_storage_bucket_iam_member" "workload_object_admin" {
  bucket = google_storage_bucket.meesell_images.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.workload_service_account_email}"
}
