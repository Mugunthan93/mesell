# Purpose: Variables for the supabase_studio module.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §10 (variables).
# Playbook reference: docs/INFRASTRUCTURE_PLAYBOOK.md §7.

variable "namespace" {
  type        = string
  description = "Kubernetes namespace to deploy Supabase Studio into (e.g. 'dev')."
}

variable "image_tag" {
  type        = string
  default     = "latest"
  description = "Supabase Studio image tag. 'latest' is acceptable for admin UI tooling (not a data-path service)."
}

variable "postgres_secret_name" {
  type        = string
  description = "Name of the Kubernetes Secret holding postgres credentials. Passed from module.postgres_dev.secret_name."
}
