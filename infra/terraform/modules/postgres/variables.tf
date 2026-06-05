# Purpose: Variables for the postgres module.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §10 (variables).
# Playbook reference: docs/INFRASTRUCTURE_PLAYBOOK.md §5.

variable "namespace" {
  type        = string
  description = "Kubernetes namespace to deploy PostgreSQL into (e.g. 'dev')."
}

variable "postgres_password" {
  type        = string
  sensitive   = true
  description = "PostgreSQL password. Passed once at first apply. Stored at ~/.meesell-secrets/dev-postgres-password. Never committed."
}

variable "storage_gb" {
  type        = number
  default     = 20
  description = "PVC size in GB for PostgreSQL data volume. Matches playbook §5.2 volumeClaimTemplate (20Gi)."
}

variable "image_tag" {
  type        = string
  default     = "16"
  description = "PostgreSQL image tag. Must be '16' per CLAUDE.md tech stack decision. Do not change without founder approval."
}
