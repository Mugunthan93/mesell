# providers.tf — provider configuration for the Fly.io + GitHub Pages root.
#
# google  — configures the SAME project/region as /terraform so the meesell-fly-sa
#           and the three bucket IAM members resolve identically. No credentials are
#           hardcoded: auth comes from Application Default Credentials (gcloud auth
#           application-default login) or GOOGLE_OAUTH_ACCESS_TOKEN, exactly like the
#           GCP roots. `terraform validate` needs no credentials.
#
# github  — owner-scoped. The token is read from the GITHUB_TOKEN env var (never a
#           committed value). Used only for the FLY_API_TOKEN actions secret; the
#           repository itself is a DATA source (github.tf) so Terraform can never
#           manage or delete the git repo.

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

provider "github" {
  owner = var.github_owner
  # token sourced from $GITHUB_TOKEN in the environment (do not set it here).
}
