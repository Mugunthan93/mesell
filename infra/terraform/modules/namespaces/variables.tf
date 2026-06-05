# Purpose: Variables for the namespaces module.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §10 (variables).
# Playbook reference: docs/INFRASTRUCTURE_PLAYBOOK.md §4.

variable "namespaces" {
  type        = map(string)
  default     = { dev = "dev", staging = "staging" }
  description = "Map of namespace name → env label to create. prod is excluded until Week 2 per playbook §15(c)."
}
