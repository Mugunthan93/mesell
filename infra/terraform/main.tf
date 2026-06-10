# Purpose: Root module orchestrator — locals, account lock guard, module invocations.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §19 Layers B+C, §11 (bootstrap order).
# LAYERS B and C — account lock per §19.
# Layer B: data.google_project.current reads the GCP project at plan time from ADC identity.
# Layer C: null_resource.account_lock_guard preconditions fail the plan if project or billing drifts.
# Note: depends_on on data.google_project is set to google_project_service.required so that
#       the cloudresourcemanager API is confirmed enabled before the data source resolves.
#       In practice cloudresourcemanager is always enabled, but the dependency makes the
#       ordering explicit and avoids a spurious plan-time 403.

locals {
  # Account lock constants — these must match providers.tf and tf-preflight.sh exactly.
  # Changing any of these requires a code-review PR (Layer A discipline).
  expected_project_id         = "project-1f5cbf72-2820-4cdb-949"
  expected_billing_account_id = "01620D-6785AB-0E4698"
  expected_account_email      = "vaishnaviramoorthy@gmail.com"
  expected_zone               = "asia-south1-a"
}

# Layer B — reads the project from GCP using the active ADC identity at plan time.
# Note: depends_on was removed from this data source. With -target plan (Pass 1 bootstrap),
# depends_on caused terraform to defer the read to apply time (unknown-until-apply), making
# data.google_project.current.project_id null at plan time and breaking the Layer C
# precondition. Since cloudresourcemanager.googleapis.com is always enabled on any live GCP
# project (it cannot be disabled), the dependency was purely cosmetic — its only side-effect
# was breaking the -target plan. The data source now reads eagerly at plan time against the
# live ADC identity, which is the intended Layer B behavior.
data "google_project" "current" {}

# Layer C — preconditions that fail terraform plan if the authenticated identity is wrong.
resource "null_resource" "account_lock_guard" {
  triggers = {
    observed_project_id      = data.google_project.current.project_id
    observed_billing_account = data.google_project.current.billing_account
  }

  lifecycle {
    precondition {
      condition     = data.google_project.current.project_id == local.expected_project_id
      error_message = "ACCOUNT LOCK VIOLATION: provider authenticated to project '${data.google_project.current.project_id != null ? data.google_project.current.project_id : "<could not read project — check ADC>"}', expected '${local.expected_project_id}'. Run terraform via `make -f Makefile.tf tf-plan-pass1` to enforce CLOUDSDK_CORE_ACCOUNT and CLOUDSDK_CORE_PROJECT env vars. Check that `gcloud auth application-default login` was run as vaishnaviramoorthy@gmail.com."
    }

    precondition {
      # The google_project data source returns billing_account as the raw account ID
      # (e.g. "01620D-6785AB-0E4698"), NOT the full "billingAccounts/..." resource name.
      # Compare against the raw ID stored in local.expected_billing_account_id.
      condition     = data.google_project.current.billing_account == local.expected_billing_account_id
      error_message = "ACCOUNT LOCK VIOLATION: project billing account is '${data.google_project.current.billing_account != null ? data.google_project.current.billing_account : "<could not read billing account — check ADC>"}', expected '${local.expected_billing_account_id}'. Confirm the correct billing account is linked to project ${local.expected_project_id} in GCP Console → Billing."
    }
  }
}

# =============================================================================
# PASS 1 MODULES — GCP-layer only (no kubernetes provider needed)
# Bootstrap order per §11: APIs → ci_identity → artifact_registry → asset_bucket
#                           → app_secrets → vm → firewall → billing_budget
# Every module depends_on account_lock_guard so the lock check runs FIRST.
# =============================================================================

module "ci_identity" {
  source = "./modules/ci_identity"

  # GitLab CI identity (Phase A — unchanged in Phase E).
  service_account_id     = var.ci_service_account_id
  gitlab_repository_path = var.gitlab_repository_path
  asset_bucket_name      = var.gcs_asset_bucket_name

  # GitHub Actions CI identity (Phase E — 2026-06-10).
  # D6 RESOLVED: a separate SA from meesell-prod-ci for blast-radius isolation.
  github_repository            = var.github_repository
  github_ci_service_account_id = var.github_ci_service_account_id
  vm_name_for_iap              = var.vm_name

  depends_on = [
    null_resource.account_lock_guard,
    google_project_service.required,
    # The github_ci_vm_instance_admin binding references the VM resource by name,
    # so the VM must be created before this module's resources are applied.
    module.vm,
  ]
}

module "artifact_registry" {
  source = "./modules/artifact_registry"

  repository_id = var.artifact_registry_repo_id

  depends_on = [
    null_resource.account_lock_guard,
    google_project_service.required,
  ]
}

module "asset_bucket" {
  source = "./modules/asset_bucket"

  bucket_name = var.gcs_asset_bucket_name

  depends_on = [
    null_resource.account_lock_guard,
    google_project_service.required,
  ]
}

module "app_secrets" {
  source = "./modules/app_secrets"

  secret_ids  = var.app_secret_ids
  environment = var.environment

  depends_on = [
    null_resource.account_lock_guard,
    google_project_service.required,
  ]
}

module "vm" {
  source = "./modules/vm"

  vm_name         = var.vm_name
  machine_type    = var.machine_type
  vm_disk_size_gb = var.vm_disk_size_gb
  environment     = var.environment

  depends_on = [
    null_resource.account_lock_guard,
    google_project_service.required,
  ]
}

module "firewall" {
  source = "./modules/firewall"

  founder_ip_ranges = var.founder_ip_ranges

  depends_on = [
    null_resource.account_lock_guard,
    google_project_service.required,
    module.vm,
  ]
}

module "billing_budget" {
  source = "./modules/billing_budget"

  budget_amount_inr = var.budget_amount_inr

  depends_on = [
    null_resource.account_lock_guard,
    google_project_service.required,
  ]
}

# Phase D codification (2026-06-10):
# Cloud Build runs as the Compute Engine default SA in this project (not the
# conventional Cloud Build SA). The IAM bindings that let it download source
# from the `_cloudbuild` bucket and push to Artifact Registry are codified here
# so they survive re-provision and don't drift silently. See module README for
# the full quirk explanation.
module "cloudbuild_permissions" {
  source = "./modules/cloudbuild_permissions"

  depends_on = [
    null_resource.account_lock_guard,
    google_project_service.required,
    module.artifact_registry,
  ]
}

# =============================================================================
# PASS 2 MODULES — Kubernetes workloads (kubernetes + helm providers active)
# Bootstrap order per §11: namespaces → postgres_dev + valkey_dev → supabase_studio_dev
#                           → traefik_stack (independent of workloads)
# cert_manager and ingress deferred to Pass 2b (requires domain from founder).
# =============================================================================

module "namespaces" {
  source     = "./modules/namespaces"
  namespaces = var.namespaces
  depends_on = [null_resource.account_lock_guard]
}

module "postgres_dev" {
  source            = "./modules/postgres"
  namespace         = "dev"
  postgres_password = var.postgres_password
  storage_gb        = var.postgres_storage_gb
  image_tag         = var.postgres_image_tag
  depends_on        = [module.namespaces, null_resource.account_lock_guard]
}

module "valkey_dev" {
  source          = "./modules/valkey"
  namespace       = "dev"
  valkey_password = var.valkey_password
  storage_gb      = var.valkey_storage_gb
  image_tag       = var.valkey_image_tag
  depends_on      = [module.namespaces, null_resource.account_lock_guard]
}

module "supabase_studio_dev" {
  source               = "./modules/supabase_studio"
  namespace            = "dev"
  image_tag            = var.supabase_studio_image_tag
  postgres_secret_name = module.postgres_dev.secret_name
  depends_on           = [module.postgres_dev]
}

module "traefik_stack" {
  source        = "./modules/traefik_stack"
  chart_version = var.traefik_chart_version
  depends_on    = [null_resource.account_lock_guard]
}

# =============================================================================
# PASS 2b MODULES — cert-manager + Ingress + TLS
# Two-stage apply discipline per §11 bootstrap note:
#   Stage 1: -target=module.cert_manager  (installs Helm chart + CRDs)
#   Stage 2: -target=module.ingress       (ClusterIssuer + Ingress — needs CRDs from Stage 1)
# =============================================================================

module "cert_manager" {
  source        = "./modules/cert_manager"
  chart_version = "v1.14.5"
  depends_on    = [module.traefik_stack]
}

module "ingress" {
  source              = "./modules/ingress"
  namespace           = "dev"
  domain              = var.domain
  acme_email          = var.acme_email
  studio_service_name = "supabase-studio"
  studio_service_port = 3000

  depends_on = [
    module.cert_manager,
    module.supabase_studio_dev,
    module.traefik_stack,
  ]
}
