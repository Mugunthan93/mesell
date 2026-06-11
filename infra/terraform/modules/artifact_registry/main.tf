# Purpose: Production Artifact Registry repository for MeeSell Docker images.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §20.1, §6 (PLAN-ADD rows).
# Choices:
#   - location = "asia-south1" hardcoded (account lock zone constant) — not a variable.
#   - format = "DOCKER" is the only format needed. No Maven/npm/Python repos at MVP.
#   - cleanup_policies: three rules (GCP API requires each policy use EITHER a condition
#     block OR a most_recent_versions block — never both in the same policy):
#       1. "keep-tagged-versions": KEEP all tagged images unconditionally.
#          Releases are tagged; never auto-delete them.
#       2. "delete-untagged": DELETE untagged images older than 30 days.
#          CI push of `latest` and feature-branch builds accumulate untagged blobs fast.
#       3. "keep-recent-untagged": KEEP the 10 most recent untagged images regardless
#          of age. Protects the latest CI builds from the 30-day DELETE rule above.
#   - This is the PRODUCTION registry (meesell-prod-images). The R&D registry (meesell-images)
#     lives in mesell/terraform/ and is out of scope per §2 R&D scope note.
#   - No prevent_destroy here: images can be rebuilt from source. Losing the registry
#     is operationally disruptive but not a data-loss event.

resource "google_artifact_registry_repository" "meesell_prod_images" {
  repository_id = var.repository_id
  location      = "asia-south1"
  format        = "DOCKER"
  description   = "MeeSell production Docker images. Managed by Terraform per docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §20.1. R&D registry is meesell-images and lives in a separate workspace."

  # Policy 1: KEEP — all tagged versions (releases). Condition-based, no most_recent_versions.
  cleanup_policies {
    id     = "keep-tagged-versions"
    action = "KEEP"

    condition {
      tag_state = "TAGGED"
    }
  }

  # Policy 2: DELETE — untagged images older than 30 days. Condition-based, no most_recent_versions.
  cleanup_policies {
    id     = "delete-untagged"
    action = "DELETE"

    condition {
      tag_state  = "UNTAGGED"
      older_than = "2592000s" # 30 days
    }
  }

  # Policy 3: KEEP — the 10 most recent untagged images (protects latest CI builds from Policy 2).
  # most_recent_versions-based; NO condition block (GCP API: oneof).
  cleanup_policies {
    id     = "keep-recent-untagged"
    action = "KEEP"

    most_recent_versions {
      keep_count = 10
    }
  }
}

# =============================================================================
# K3s image-pull identity  (CI activation run-6 deploy fix — 2026-06-11)
# Spec: founder ruling 2026-06-11 (reader-only SA key as a k8s imagePullSecret).
#
# WHY this exists:
#   Our K3s cluster runs OUTSIDE GKE on a plain GCE VM. containerd has no native
#   GCP credential helper, so when a Deployment pulls an image from
#   asia-south1-docker.pkg.dev it presents NO auth and Artifact Registry returns
#   401 Unauthorized -> ImagePullBackOff. This was the run-6 blocker: the CI deploy
#   retagged + applied manifests fine, but the new ReplicaSet could not pull the
#   freshly-built image (the existing 46h pods were hand-loaded, never pulled).
#
# THE FIX (reader-only SA + docker-registry secret):
#   A dedicated, low-privilege service account that holds ONLY
#   roles/artifactregistry.reader, scoped to THIS repo (NOT project-level). A JSON
#   key for it is created OUT-OF-BAND (NOT in Terraform — a TF-created key would
#   land in the GCS state file in plaintext) and loaded into the cluster as a
#   docker-registry secret named "artifact-registry", referenced by api/worker/
#   frontend Deployments via imagePullSecrets.
#
# BLAST RADIUS: this SA can pull (read) images from meesell-prod-images and nothing
#   else. It cannot push, cannot touch other repos, cannot read project-level
#   resources. If its key leaks, the worst case is read access to our own images.
#
# WHY repo-scoped, not project-level: least privilege. A project-level
#   artifactregistry.reader would also expose any future repo (incl. other teams').
#   google_artifact_registry_repository_iam_member binds the role to ONLY this repo.
# =============================================================================

resource "google_service_account" "meesell_image_puller" {
  account_id   = "meesell-image-puller"
  display_name = "MeeSell K3s image pull (AR reader)"
  description  = "Read-only AR puller for K3s (no GCP cred helper outside GKE). Repo-scoped reader on meesell-prod-images. JSON key created out-of-band, loaded as k8s secret 'artifact-registry'; never in Terraform. Run-6 fix 2026-06-11."
}

# Repo-scoped reader: roles/artifactregistry.reader on meesell-prod-images ONLY.
# google_artifact_registry_repository_iam_member is additive (NOT _iam_binding) —
# it does not disturb the existing VM-SA / CI-SA reader/writer grants on this repo.
resource "google_artifact_registry_repository_iam_member" "image_puller_reader" {
  project    = google_artifact_registry_repository.meesell_prod_images.project
  location   = google_artifact_registry_repository.meesell_prod_images.location
  repository = google_artifact_registry_repository.meesell_prod_images.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.meesell_image_puller.email}"
}
