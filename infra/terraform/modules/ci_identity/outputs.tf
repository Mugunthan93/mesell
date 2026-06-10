# Purpose: Outputs for the ci_identity module.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §10, §20.3.
# These outputs are copied into GitLab CI/CD variable settings after terraform apply.
# See the module main.tf header comment for the full CI setup procedure.

output "ci_sa_email" {
  description = "Service account email for the CI identity. Set as GCP_SERVICE_ACCOUNT in GitLab CI/CD variables."
  value       = google_service_account.meesell_prod_ci.email
}

output "wif_pool_resource_name" {
  description = "Full resource name of the Workload Identity Pool. Format: projects/<number>/locations/global/workloadIdentityPools/gitlab-prod-pool."
  value       = google_iam_workload_identity_pool.gitlab_prod.name
}

output "wif_provider_resource_name" {
  description = "Full resource name of the WIF provider. Set as GCP_WIF_PROVIDER in GitLab CI/CD variables. Format: projects/<number>/locations/global/workloadIdentityPools/gitlab-prod-pool/providers/gitlab-prod-provider."
  value       = google_iam_workload_identity_pool_provider.gitlab_prod.name
}

output "ci_sa_impersonation_member" {
  description = "The principalSet:// member string that identifies all GitLab CI jobs from the configured repository. Used in IAM bindings that must reference the WIF-authenticated CI identity. Format: principalSet://iam.googleapis.com/.../attribute.repository/<repo>."
  value       = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.gitlab_prod.name}/attribute.repository/${var.gitlab_repository_path}"
}

# --- GitHub Actions WIF outputs (Phase E — 2026-06-10) ---
# These two outputs are copied into GitHub repository Variables (NOT Secrets — neither
# value is sensitive) at Settings → Secrets and variables → Actions → Variables:
#   GCP_WIF_PROVIDER  ← github_wif_provider_name
#   GCP_CI_SA_EMAIL   ← github_ci_sa_email

output "github_wif_provider_name" {
  description = "Full resource name of the GitHub Actions WIF provider. Set as GitHub repository Variable GCP_WIF_PROVIDER. Format: projects/<number>/locations/global/workloadIdentityPools/github-actions-pool/providers/github-actions-provider."
  value       = google_iam_workload_identity_pool_provider.github_actions.name
}

output "github_ci_sa_email" {
  description = "Email of the meesell-github-ci service account. Set as GitHub repository Variable GCP_CI_SA_EMAIL. Format: meesell-github-ci@project-1f5cbf72-2820-4cdb-949.iam.gserviceaccount.com."
  value       = google_service_account.meesell_github_ci.email
}

output "github_wif_pool_resource_name" {
  description = "Full resource name of the GitHub Actions WIF pool. Format: projects/<number>/locations/global/workloadIdentityPools/github-actions-pool. Useful for cross-account principalSet:// member strings."
  value       = google_iam_workload_identity_pool.github_actions.name
}

output "github_ci_sa_impersonation_member" {
  description = "The principalSet:// member string for GitHub Actions runs from the configured repository. Format: principalSet://iam.googleapis.com/.../attribute.repository/<owner/repo>."
  value       = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github_actions.name}/attribute.repository/${var.github_repository}"
}
