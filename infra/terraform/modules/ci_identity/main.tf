# Purpose: CI service account and Workload Identity Federation for GitLab CI.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §20.3, §6 (PLAN-ADD rows).
# Why no JSON key is created:
#   JSON keys are long-lived credentials that can be leaked in CI logs, container images,
#   or git history. Workload Identity Federation (WIF) uses short-lived OIDC tokens issued
#   by GitLab for each pipeline job — no key file is ever written to disk. This is the
#   Google-recommended approach for GitLab CI and is required by the account lock discipline
#   in §19 (no credentials outside ADC/WIF flows).
#
# GitLab CI setup (after terraform apply):
#   Set these CI/CD variables in gitlab.com → Settings → CI/CD → Variables:
#     GCP_PROJECT_ID       = "project-1f5cbf72-2820-4cdb-949"
#     GCP_WIF_PROVIDER     = <output: wif_provider_resource_name>
#     GCP_SERVICE_ACCOUNT  = <output: ci_sa_email>
#   Then authenticate in .gitlab-ci.yml with:
#     - id_tokens:
#         GITLAB_OIDC_TOKEN:
#           aud: https://iam.googleapis.com/<wif_provider_resource_name>
#     script:
#       - gcloud iam workload-identity-pools create-cred-config $GCP_WIF_PROVIDER
#           --service-account=$GCP_SERVICE_ACCOUNT
#           --output-file=$GOOGLE_APPLICATION_CREDENTIALS
#           --credential-source-file=$GITLAB_OIDC_TOKEN_FILE

resource "google_service_account" "meesell_prod_ci" {
  account_id   = var.service_account_id
  display_name = "MeeSell Prod CI (GitLab Workload Identity)"
  description  = "Used by GitLab CI to push to Artifact Registry and write to GCS bucket. No JSON key issued — auth via Workload Identity Federation per docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §20.3."
}

resource "google_iam_workload_identity_pool" "gitlab_prod" {
  workload_identity_pool_id = "gitlab-prod-pool"
  display_name              = "GitLab Prod Pool"
  description               = "Federated identity pool for GitLab.com CI/CD."
}

resource "google_iam_workload_identity_pool_provider" "gitlab_prod" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.gitlab_prod.workload_identity_pool_id
  workload_identity_pool_provider_id = "gitlab-prod-provider"
  display_name                       = "GitLab.com OIDC Provider"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.aud"        = "assertion.aud"
    "attribute.repository" = "assertion.project_path"
    "attribute.ref"        = "assertion.ref"
    "attribute.ref_type"   = "assertion.ref_type"
  }

  # Restrict impersonation to CI jobs running within the MeeSell GitLab repository only.
  # Any job from a different repository — even in the same GitLab group — cannot use this pool.
  attribute_condition = "assertion.project_path == \"${var.gitlab_repository_path}\""

  oidc {
    issuer_uri = "https://gitlab.com"
  }
}

resource "google_service_account_iam_member" "wif_impersonation" {
  service_account_id = google_service_account.meesell_prod_ci.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.gitlab_prod.name}/attribute.repository/${var.gitlab_repository_path}"
}

resource "google_project_iam_member" "ci_artifactregistry_writer" {
  # ACCOUNT LOCK: project ID hardcoded per §19 Layer A.
  project = "project-1f5cbf72-2820-4cdb-949"
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.meesell_prod_ci.email}"
}

resource "google_storage_bucket_iam_member" "ci_gcs_object_admin" {
  bucket = var.asset_bucket_name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.meesell_prod_ci.email}"
}

# =============================================================================
# GitHub Actions WIF + meesell-github-ci SA  (Phase E — 2026-06-10)
# Spec: docs/DEVOPS_ARCHITECTURE.md §4.
# D6 RESOLVED (founder 2026-06-09): a separate SA from meesell-prod-ci. The
# GitLab pool/SA above stays untouched — a leak in one cannot affect the other.
# =============================================================================

resource "google_service_account" "meesell_github_ci" {
  account_id   = var.github_ci_service_account_id
  display_name = "MeeSell GitHub CI (GitHub Actions WIF)"
  description  = "Used by GitHub Actions for image builds (Cloud Build) and IAP-tunneled deploys. No JSON key — WIF only. Separate from meesell-prod-ci (D6, 2026-06-09)."
}

resource "google_iam_workload_identity_pool" "github_actions" {
  workload_identity_pool_id = "github-actions-pool"
  display_name              = "GitHub Actions Pool"
  description               = "Federated identity pool for github.com Actions runners. Distinct from the GitLab pool above so a GitHub compromise cannot affect the GitLab CI surface or vice-versa."
}

resource "google_iam_workload_identity_pool_provider" "github_actions" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github_actions.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-actions-provider"
  display_name                       = "GitHub Actions OIDC Provider"
  description                        = "OIDC provider for github.com Actions OIDC tokens. Attribute condition restricts to the configured repository only."

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.aud"        = "assertion.aud"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
    "attribute.actor"      = "assertion.actor"
    "attribute.event_name" = "assertion.event_name"
  }

  # Restrict impersonation to GitHub Actions runs in the MeeSell repository only.
  # Any Actions workflow in a different repo — even one the founder owns — cannot
  # exchange a token for this SA. WIF-1 decision: repository-only (not ref-bound)
  # so PRs can also use the SA for the lint/test gates without separate plumbing.
  attribute_condition = "assertion.repository == \"${var.github_repository}\""

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "github_wif_impersonation" {
  service_account_id = google_service_account.meesell_github_ci.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github_actions.name}/attribute.repository/${var.github_repository}"
}

# Project-level roles for the GitHub CI SA.
# Each role is granted via google_project_iam_member (additive), NEVER iam_binding.

resource "google_project_iam_member" "github_ci_artifactregistry_writer" {
  project = "project-1f5cbf72-2820-4cdb-949"
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.meesell_github_ci.email}"
}

resource "google_project_iam_member" "github_ci_cloudbuild_editor" {
  project = "project-1f5cbf72-2820-4cdb-949"
  role    = "roles/cloudbuild.builds.editor"
  member  = "serviceAccount:${google_service_account.meesell_github_ci.email}"
}

resource "google_project_iam_member" "github_ci_secretmanager_accessor" {
  project = "project-1f5cbf72-2820-4cdb-949"
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.meesell_github_ci.email}"
}

resource "google_project_iam_member" "github_ci_iap_tunnel" {
  # IAP tunnel access is granted at the project level here. The IAP service does
  # apply additional resource-level checks; the SA can only tunnel to instances
  # it ALSO has compute.instanceAdmin.v1 on (see vm_instance_admin below).
  project = "project-1f5cbf72-2820-4cdb-949"
  role    = "roles/iap.tunnelResourceAccessor"
  member  = "serviceAccount:${google_service_account.meesell_github_ci.email}"
}

# VM-scoped compute.instanceAdmin.v1 — explicitly bound to the meesell-dev instance
# only. The SA cannot administer any other VM in the project. This is the brief's
# "scoped to meesell-dev VM" constraint.
resource "google_compute_instance_iam_member" "github_ci_vm_instance_admin" {
  project       = "project-1f5cbf72-2820-4cdb-949"
  zone          = "asia-south1-a"
  instance_name = var.vm_name_for_iap
  role          = "roles/compute.instanceAdmin.v1"
  member        = "serviceAccount:${google_service_account.meesell_github_ci.email}"
}

# act-as on the Compute Engine default SA  (CI activation run-4 fix — 2026-06-11)
# WHY: `gcloud builds submit` runs Cloud Build as the project's Compute Engine
# default SA (888244156264-compute@developer.gserviceaccount.com — see Phase D
# memory + module.cloudbuild_permissions). To submit a build that runs AS that SA,
# meesell-github-ci must hold roles/iam.serviceAccountUser (act-as) ON the compute
# SA. Without it, build submission fails with a "Permission iam.serviceAccounts.actAs
# denied" error — this was the run-4 blocker (GitHub Actions run 27331720017).
# The legacy GitLab CI SA (meesell-prod-ci) had this grant out-of-band; the TF-managed
# GitHub CI SA never did — that gap is what this resource closes.
# Compute SA hardcoded to match the sibling cloudbuild_permissions/main.tf style.
resource "google_service_account_iam_member" "github_ci_act_as_compute" {
  service_account_id = "projects/project-1f5cbf72-2820-4cdb-949/serviceAccounts/888244156264-compute@developer.gserviceaccount.com"
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.meesell_github_ci.email}"
}
