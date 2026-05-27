# Auto-generated secrets: terraform owns these end to end.
resource "random_password" "jwt_secret" {
  length  = 64
  special = false
}

resource "random_password" "postgres_password" {
  length  = 32
  special = false
}

locals {
  # name -> value. Each becomes a google_secret_manager_secret + initial version.
  # The workload SA is granted secretAccessor on every entry.
  secret_values = {
    JWT_SECRET          = random_password.jwt_secret.result
    POSTGRES_PASSWORD   = random_password.postgres_password.result
    GEMINI_API_KEY      = var.gemini_api_key
    MSG91_AUTH_KEY      = var.msg91_auth_key
    MSG91_TEMPLATE_ID   = var.msg91_template_id
    RAZORPAY_KEY_ID     = var.razorpay_key_id
    RAZORPAY_KEY_SECRET = var.razorpay_key_secret
  }
}

resource "google_secret_manager_secret" "secret" {
  for_each = local.secret_values

  secret_id = "${var.name_prefix}-${lower(replace(each.key, "_", "-"))}"
  labels    = var.labels

  replication {
    auto {}
  }

  depends_on = [google_project_service.enabled]
}

resource "google_secret_manager_secret_version" "version" {
  for_each = local.secret_values

  secret      = google_secret_manager_secret.secret[each.key].id
  secret_data = each.value
}

resource "google_secret_manager_secret_iam_member" "workload_access" {
  for_each = local.secret_values

  secret_id = google_secret_manager_secret.secret[each.key].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.workload.email}"
}
