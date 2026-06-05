# Purpose: Enable required GCP APIs for the production workspace.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §11 (bootstrap order — APIs first),
#                 §10 (var.gcp_api_services default list).
# Note: disable_on_destroy = false prevents Terraform from disabling APIs when resources
#       are removed. Disabling an API can break other resources in the project that were
#       not managed by this workspace. Never set disable_on_destroy = true here.

resource "google_project_service" "required" {
  for_each = toset(var.gcp_api_services)

  service                    = each.value
  disable_on_destroy         = false
  disable_dependent_services = false

  timeouts {
    create = "10m"
    update = "10m"
  }
}
