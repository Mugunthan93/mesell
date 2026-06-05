# Purpose: Variables for the traefik_stack module.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §9 (module boundaries), §11 (Pass 2).
# Playbook reference: docs/INFRASTRUCTURE_PLAYBOOK.md §8.1 (Traefik Deployment).

variable "chart_version" {
  type        = string
  default     = "28.3.0"
  description = "Traefik Helm chart version pin."
}
