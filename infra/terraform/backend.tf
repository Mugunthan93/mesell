# Purpose: Terraform state backend configuration.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §4 (state backend), Decision D2.
#
# MIGRATED 2026-06-10 — local → GCS.
# State now lives in: gs://meesell-tfstate/terraform/state/default.tfstate
# Bucket config: ASIA-SOUTH1, uniform-bucket-level-access, versioning enabled.
# State locking: handled by GCS object generation numbers (atomic; no separate lock table needed).
#
# Auth notes:
#   - Read/write goes through Application Default Credentials (ADC). Use the documented
#     GOOGLE_OAUTH_ACCESS_TOKEN workaround if ADC is bound to a non-owner identity:
#       export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token \
#         --account=vaishnaviramoorthy@gmail.com)
#   - The vaishnaviramoorthy@gmail.com account already has roles/storage.admin on the
#     bucket via project ownership — no extra IAM binding needed.
#
# Restore-from-backup:
#   gcloud storage cp gs://meesell-tfstate/terraform/state/default.tfstate.backup \
#     gs://meesell-tfstate/terraform/state/default.tfstate
#   terraform init -reconfigure
#
# Historical: local backend was used per founder decision D2 to defer GCS complexity for
# initial scaffold. The local terraform.tfstate file is retained as a one-time backup but
# is no longer authoritative — do not edit it. Bootstrap migration ran 2026-06-10 by
# meesell-infra-builder with `terraform init -migrate-state`.

terraform {
  backend "gcs" {
    bucket = "meesell-tfstate"
    prefix = "terraform/state"
  }
}
