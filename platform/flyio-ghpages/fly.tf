# fly.tf — Fly.io app + secrets, modelled as HONEST flyctl shims (no provider).
#
# ── WHY A SHIM, NOT A PROVIDER (registry evidence, checked 2026-07-03) ───────
#   fly-apps/fly (official)   : v0.0.23, published 2023-06-22, source repo ARCHIVED.
#   andrewbaxter/fly (fork)   : v0.1.18, published 2024-10-28, solo community tier.
# Neither is a maintained provider fit for adopting LIVE production infra (the app,
# Fly Postgres meesell-db, Upstash Redis meesell-cache, and ~40 secrets already exist
# and must NOT be recreated/destroyed). Per the founder decision rule, Fly resources
# are driven by idempotent flyctl shims: create-if-absent / update-in-place, and the
# destroy provisioner is a NO-OP that prints a manual runbook line — it deletes nothing.
#
# These shims are SAFE to run against live infra: fly_apply.sh detects the existing app
# and no-ops; fly_secrets.sh only STAGES (never deploys/restarts) and only sets vars
# that are non-empty in the environment. `terraform validate` never runs provisioners.

locals {
  # Config identity for the app shim. When any of these change, the app shim re-runs
  # (create-if-absent stays a no-op; the value is the audit trail). fly.toml is the
  # real source of truth for processes/regions — hashed so edits re-trigger the shim.
  fly_toml_sha = fileexists("${path.module}/../../fly.toml") ? filesha256("${path.module}/../../fly.toml") : "no-fly-toml"
}

# The Fly app. Idempotent: create-if-absent, else no-op. NEVER destroys on `terraform
# destroy` (the destroy provisioner prints a manual runbook line instead).
resource "terraform_data" "fly_app" {
  triggers_replace = [
    var.fly_app_name,
    var.fly_region,
    var.fly_org,
    local.fly_toml_sha,
  ]

  # CREATE / UPDATE — idempotent create-if-absent.
  provisioner "local-exec" {
    command = "bash ${path.module}/scripts/fly_apply.sh"
    environment = {
      FLY_APP    = var.fly_app_name
      FLY_REGION = var.fly_region
      FLY_ORG    = var.fly_org
    }
  }

  # DESTROY — deliberately a NO-OP. Deleting the live app (and its attached Postgres +
  # secrets) must be a conscious human act, never a `terraform destroy` side effect.
  provisioner "local-exec" {
    when    = destroy
    command = "bash ${path.module}/scripts/fly_destroy_noop.sh"
    environment = {
      FLY_APP = self.triggers_replace[0]
    }
  }
}

# Fly secrets. Re-stages (via `flyctl secrets set --stage`, no restart) the app secrets
# whose values are present in the environment. Bump var.secrets_revision to force a
# re-stage. NO secret values are stored in state — only the revision counter is; the
# values flow from TF_VAR_fly_secret_* through the local-exec environment and are never
# printed. On adoption every value is "" → the shim stages nothing.
resource "terraform_data" "fly_secrets" {
  triggers_replace = [
    var.fly_app_name,
    var.secrets_revision,
  ]

  provisioner "local-exec" {
    command = "bash ${path.module}/scripts/fly_secrets.sh"
    environment = {
      FLY_APP                     = var.fly_app_name
      TF_VAR_JWT_SECRET           = var.fly_secret_jwt_secret
      TF_VAR_REFRESH_TOKEN_PEPPER = var.fly_secret_refresh_token_pepper
      TF_VAR_GEMINI_API_KEY       = var.fly_secret_gemini_api_key
      TF_VAR_MSG91_AUTH_KEY       = var.fly_secret_msg91_auth_key
      TF_VAR_RAZORPAY_KEY_ID      = var.fly_secret_razorpay_key_id
      TF_VAR_RAZORPAY_KEY_SECRET  = var.fly_secret_razorpay_key_secret
    }
  }

  depends_on = [terraform_data.fly_app]
}
