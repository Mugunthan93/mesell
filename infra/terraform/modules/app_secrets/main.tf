# Purpose: Secret Manager secret containers for MeeSell application secrets.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §20.4, §6 (PLAN-ADD rows), §7.
#
# IMPORTANT — NO secret versions are created here.
# Terraform manages the secret CONTAINERS only (the metadata + replication config).
# The actual secret VALUES are populated by the founder after terraform apply using:
#
#   printf 'YOUR_SECRET_VALUE' | gcloud secrets versions add <secret-id> \
#     --project=project-1f5cbf72-2820-4cdb-949 \
#     --account=vaishnaviramoorthy@gmail.com \
#     --data-file=-
#
# Populate each secret ID from the list. Verify with:
#   gcloud secrets versions list <secret-id> \
#     --project=project-1f5cbf72-2820-4cdb-949 \
#     --account=vaishnaviramoorthy@gmail.com
#
# Secret ID → backend/.env.example mapping:
#   gemini-api-key       → GEMINI_API_KEY
#   msg91-auth-key       → MSG91_AUTH_KEY
#   jwt-secret           → JWT_SECRET
#   razorpay-key-id      → RAZORPAY_KEY_ID
#   razorpay-key-secret  → RAZORPAY_KEY_SECRET
#
# Why no google_secret_manager_secret_version here:
#   Adding a version resource would require the plaintext value in either the Terraform
#   state or a -var flag. The state file is not committed, but it is a sensitive file on
#   disk. Keeping values completely out of Terraform state is the safer MVP pattern —
#   the playbook's ~/.meesell-secrets/ remains the only location for plaintext values.

resource "google_secret_manager_secret" "app_secrets" {
  for_each = toset(var.secret_ids)

  secret_id = each.key

  replication {
    auto {}
  }

  labels = {
    env     = var.environment
    project = "meesell"
  }
}
