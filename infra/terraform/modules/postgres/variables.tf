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

variable "max_connections" {
  type        = number
  default     = 200
  description = "PostgreSQL max_connections. MS-0 / D5 step 1 (MS-DB-3, infra plan §3.3) raised this 100 -> 200 for the microservices connection-pool budget. ~5MB/conn memory cost is covered by the 1.5Gi memory limit. Passed to the container as `-c max_connections=N`."
}
