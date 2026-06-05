# Purpose: Production GCS asset bucket for MeeSell user uploads and exports.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §20.2, §6 (PLAN-ADD rows).
# Choices:
#   - location = "ASIA-SOUTH1" hardcoded (account lock region constant, uppercased per GCS API).
#   - uniform_bucket_level_access = true: disables per-object ACLs. Required for
#     public_access_prevention = "enforced" and simplifies IAM reasoning.
#   - public_access_prevention = "enforced": no object can be made public — not by IAM,
#     not by ACL. Images are served via the FastAPI backend (signed URLs or proxied),
#     never directly from GCS. This is a hard safety control.
#   - versioning: enabled. Product images and catalog exports are user data. Accidental
#     deletes or overwrites can be recovered within 30 days.
#   - lifecycle_rule: deletes objects under temp/ prefix after 30 days. CI test uploads,
#     rembg processing intermediates, and export-in-progress files land here. No manual
#     cleanup needed.
#   - force_destroy = false: prevents `terraform destroy` from deleting a non-empty bucket.
#     Requires a manual `gcloud storage rm -r gs://<bucket>/**` before destroy.
#   - lifecycle.prevent_destroy = true (Terraform meta-lifecycle, separate from the GCS
#     lifecycle_rule above): prevents accidental `terraform destroy` of the bucket resource
#     altogether without a code change. Protects against state drift wiping production data.

resource "google_storage_bucket" "meesell_prod_assets" {
  name                        = var.bucket_name
  location                    = "ASIA-SOUTH1"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age            = 30
      matches_prefix = ["temp/"]
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    env     = var.environment
    project = "meesell"
  }

  lifecycle {
    prevent_destroy = true
  }
}
