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
