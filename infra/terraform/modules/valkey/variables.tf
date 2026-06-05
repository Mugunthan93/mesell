# Purpose: Variables for the valkey module.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §10 (variables).
# Playbook reference: docs/INFRASTRUCTURE_PLAYBOOK.md §6.

variable "namespace" {
  type        = string
  description = "Kubernetes namespace to deploy Valkey into (e.g. 'dev')."
}

variable "valkey_password" {
  type        = string
  sensitive   = true
  description = "Valkey password. Passed once at first apply. Stored at ~/.meesell-secrets/dev-valkey-password. Never committed."
}

variable "storage_gb" {
  type        = number
  default     = 5
  description = "PVC size in GB for Valkey data volume. Matches playbook §6.2 volumeClaimTemplate (5Gi)."
}

variable "image_tag" {
  type        = string
  default     = "8"
  description = "Valkey image tag. Must be '8' per CLAUDE.md tech stack decision. Do not change without founder approval."
}
