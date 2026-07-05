# gcp_sa.tf — the ONE place this decoupled root touches GCP.
#
# Models the meesell-fly-sa service account + its Storage Object Admin grants on the
# three asset buckets, using the REAL hashicorp/google provider (same convention as
# /terraform/iam.tf + /terraform/storage.tf). These are all safely importable, so
# adoption recreates/destroys NOTHING (see import.sh).
#
# Buckets themselves are NOT declared here — they are owned by the GCP roots
# (/terraform manages meesell-* asset buckets). This root only attaches an IAM member
# to the pre-existing buckets, so a `terraform destroy` here can never delete a bucket.

# The Fly workload service account. Mirror of /terraform's workload SA pattern.
resource "google_service_account" "fly" {
  project      = var.gcp_project_id
  account_id   = var.fly_sa_account_id
  display_name = var.fly_sa_display_name
  description  = "Fly.io backend + worker read/write GCS via base64 key in the Fly secret GCS_SA_KEY_B64."
}

# Storage Object Admin on each asset bucket (member on a pre-existing bucket; never
# an authoritative binding, so it cannot strip other members or delete the bucket).
resource "google_storage_bucket_iam_member" "fly_object_admin" {
  for_each = toset(var.gcs_buckets)

  bucket = each.value
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.fly.email}"
}

# OPTIONAL key — adoption default is manage_sa_key = false, so this creates NOTHING.
# The live key was made out-of-band and is already in the Fly GCS_SA_KEY_B64 secret.
# Set manage_sa_key = true ONLY for a deliberate rotation; the private key material
# then lives in local state (keep state encrypted; see .gitignore + README).
resource "google_service_account_key" "fly" {
  count              = var.manage_sa_key ? 1 : 0
  service_account_id = google_service_account.fly.name
}

# When rotating (manage_sa_key && push_sa_key_to_fly), stage the freshly-minted key,
# base64-encoded, into the Fly GCS_SA_KEY_B64 secret. Reuses the fly_secrets shim
# script but for this single value. The key value is passed via the environment and
# NEVER printed. No-op on adoption (count 0).
resource "terraform_data" "fly_gcs_key_push" {
  count = var.manage_sa_key && var.push_sa_key_to_fly ? 1 : 0

  triggers_replace = [
    var.fly_app_name,
    try(google_service_account_key.fly[0].id, ""),
  ]

  provisioner "local-exec" {
    command = "bash ${path.module}/scripts/fly_secrets.sh"
    environment = {
      FLY_APP                = var.fly_app_name
      TF_VAR_GCS_SA_KEY_B64  = try(google_service_account_key.fly[0].private_key, "")
      MEESELL_SHIM_KEYS_ONLY = "GCS_SA_KEY_B64"
    }
  }
}
