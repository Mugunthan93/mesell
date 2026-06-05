# Purpose: Terraform state backend configuration.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §4 (state backend), Decision D2.
# Note: Local backend is used per founder decision D2 to defer GCS complexity for the
#       initial scaffold. State lives at mesell/infra/terraform/terraform.tfstate on the
#       founder's laptop. Acknowledged risk: laptop disk failure before migration = state loss.
#
# MIGRATION TO GCS (when ready):
#   1. Create GCS bucket manually:
#      gcloud storage buckets create gs://meesell-tfstate \
#        --location=ASIA-SOUTH1 \
#        --uniform-bucket-level-access \
#        --account=vaishnaviramoorthy@gmail.com
#   2. Replace the backend block below with:
#      backend "gcs" {
#        bucket = "meesell-tfstate"
#        prefix = "terraform/state"
#      }
#   3. Run: cd mesell/infra/terraform && terraform init -migrate-state
#   4. Confirm state was copied to GCS before deleting the local .tfstate file.

terraform {
  backend "local" {
    path = "terraform.tfstate"
  }
}
