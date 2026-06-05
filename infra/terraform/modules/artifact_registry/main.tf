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
