# github.tf — GitHub Pages config + the FLY_API_TOKEN Actions secret.
#
# SAFETY INVARIANT: Terraform must NEVER be able to delete the git repo. So the
# repository is a DATA source, never a managed resource. Pages is configured through a
# `gh api` shim (not the github_repository_pages block) because that block only exists
# on the repository RESOURCE — managing it would mean managing the repo, which risks
# repo-destroy semantics. The one thing we DO manage is the Actions secret (importable,
# and deleting a secret is harmless / re-creatable).

# Repo as data source — read only. Terraform can never manage or delete it.
data "github_repository" "repo" {
  full_name = "${var.github_owner}/${var.github_repo}"
}

# FLY_API_TOKEN — consumed by ci.yml deploy-backend (flyctl auth). Managed + importable.
# On adoption: import the existing secret (import.sh), then set TF_VAR_fly_github_actions_token
# to the SAME token so the first post-import apply is an idempotent re-set.
# GitHub Actions secrets are write-only (like Fly secrets) — the plaintext cannot be read
# back, so Terraform cannot detect value drift; it only re-sets when this input changes.
resource "github_actions_secret" "fly_api_token" {
  repository      = data.github_repository.repo.name
  secret_name     = "FLY_API_TOKEN"
  plaintext_value = var.fly_github_actions_token
}

# GitHub Pages build_type. The LIVE repo is build_type=workflow (actions/deploy-pages;
# the legacy branch pipeline failed twice on 2026-07-02). Modelled as an idempotent
# `gh api -X PUT repos/<owner>/<repo>/pages -f build_type=workflow` shim so Terraform
# never has to manage the repository resource. No-op when manage_pages_shim = false.
resource "terraform_data" "pages_build_type" {
  count = var.manage_pages_shim ? 1 : 0

  triggers_replace = [
    "${var.github_owner}/${var.github_repo}",
    var.github_pages_build_type,
  ]

  provisioner "local-exec" {
    command = "bash ${path.module}/scripts/gh_pages.sh"
    environment = {
      GH_OWNER      = var.github_owner
      GH_REPO       = var.github_repo
      GH_BUILD_TYPE = var.github_pages_build_type
    }
  }
}
