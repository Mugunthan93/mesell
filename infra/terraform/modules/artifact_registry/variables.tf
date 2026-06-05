# Purpose: Variable declarations for the artifact_registry module.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §9, §10, §20.1.

variable "repository_id" {
  type        = string
  description = "Artifact Registry repository ID. Must be globally unique within the project and region. Root default: meesell-prod-images (prod registry, isolated from the R&D meesell-images registry in mesell/terraform/). No default here — root must pass explicitly."
}
