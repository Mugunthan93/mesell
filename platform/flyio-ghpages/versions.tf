# versions.tf — Fly.io + GitHub Pages platform root module.
#
# Terraform + provider version constraints. Mirrors /terraform (the GCP root):
#   - terraform >= 1.5.0
#   - hashicorp/google ~> 6.10  (real resources: the meesell-fly-sa + bucket IAM)
# Adds:
#   - integrations/github ~> 6.0 (Pages build_type + FLY_API_TOKEN actions secret)
#
# Fly.io itself is NOT modelled with a provider — see fly.tf for why (no maintained
# provider as of 2026-07-03: fly-apps/fly is archived at v0.0.23 [2023-06-22];
# andrewbaxter/fly is a stale community fork at v0.1.18 [2024-10-28]). Fly resources
# are driven by idempotent flyctl shims via terraform_data + local-exec.
#
# terraform_data is a Terraform built-in (>= 1.4) — no provider dependency.

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.10"
    }
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
  }

  # STATE ISOLATION (decoupling contract): this root uses LOCAL state, exactly like
  # /terraform (the GCP root). It deliberately does NOT share the GCS backend
  # (gs://meesell-tfstate) that /infra/terraform uses — each platform root owns its
  # own state, no cross-root references. State contains a GCP SA key when
  # var.manage_sa_key = true, so state must stay local + encrypted at rest and is
  # git-ignored (see .gitignore, mirrored from /terraform/.gitignore).
}
