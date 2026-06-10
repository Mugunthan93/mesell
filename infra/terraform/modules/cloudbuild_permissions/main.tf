# Purpose: Codify the IAM bindings Cloud Build needs to run builds in this project.
# Plan reference: STATUS_INFRA.md Phase D D-API-5; PHASE D DEPLOYMENT 2026-06-09.
#
# Why this module exists:
#   During Phase D (V1 backend deployment), `gcloud builds submit` failed with 403
#   "could not resolve source: ... 888244156264-compute@developer.gserviceaccount.com
#    does not have storage.objects.get access" — surprising because the documented
#   default Cloud Build service account is "888244156264@cloudbuild.gserviceaccount.com".
#   Investigation showed this project's Cloud Build runs as the Compute Engine default SA,
#   NOT the conventional Cloud Build SA. We granted the necessary roles directly via
#   `gcloud iam ...` to unblock Phase D. This module codifies those bindings into
#   Terraform state so they survive re-provision and don't drift silently.
#
# Bindings codified here:
#   - `gs://project-1f5cbf72-2820-4cdb-949_cloudbuild` (the auto-created Cloud Build source bucket)
#     → roles/storage.admin → 888244156264-compute@developer.gserviceaccount.com
#   - `meesell-prod-images` Artifact Registry repo
#     → roles/artifactregistry.writer → 888244156264-compute@developer.gserviceaccount.com
#
# What is NOT in this module (intentional — out of brief scope):
#   - VM SA `roles/artifactregistry.reader` on `meesell-prod-images` (Phase A A1, image pull)
#   - VM SA `roles/storage.objectAdmin` on `gs://meesell-prod-assets` (Phase A A2, GCS uploads)
#     Those are VM-runtime bindings, not Cloud Build bindings. A separate `vm_sa_permissions`
#     module is the right home for them when codified (track as a Phase E follow-up).
#   - The conventional Cloud Build SA (`888244156264@cloudbuild.gserviceaccount.com`) bindings
#     that we also granted during the Phase D Cloud Build SA quirk debugging session. Those
#     bindings exist live but are unused — Cloud Build does NOT run as that SA in this project.
#     Leaving them out of TF lets them be cleaned up later via `gcloud iam policy-binding`
#     without touching this module. Tracked in STATUS_INFRA.md.
#
# Resource type rationale (google_*_iam_member, NOT google_*_iam_binding):
#   - `google_storage_bucket_iam_member` is additive — it grants the role to the named member
#     without touching other bindings on the same role. This is the safe choice when other
#     entities (project owners, project editors, other SAs) may already hold the same role.
#   - `google_*_iam_binding` is AUTHORITATIVE — it would REPLACE all members for the role,
#     potentially deleting unrelated bindings. NEVER use binding here.

resource "google_storage_bucket_iam_member" "cloudbuild_bucket_compute_sa_admin" {
  bucket = "project-1f5cbf72-2820-4cdb-949_cloudbuild"
  role   = "roles/storage.admin"
  member = "serviceAccount:888244156264-compute@developer.gserviceaccount.com"
}

resource "google_artifact_registry_repository_iam_member" "meesell_prod_images_compute_sa_writer" {
  location   = "asia-south1"
  repository = "meesell-prod-images"
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:888244156264-compute@developer.gserviceaccount.com"
}
