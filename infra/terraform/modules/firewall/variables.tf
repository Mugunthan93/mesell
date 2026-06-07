# Purpose: Input variables for the firewall module.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §9 (module: firewall), §18 item 8.

variable "founder_ip_ranges" {
  type        = list(string)
  description = "List of CIDR blocks allowed to reach the K3s API (tcp:6443). Use ISP CIDR ranges (e.g. /18, /21) instead of individual /32 IPs to survive dynamic IP rotation. Must not include 0.0.0.0/0 — playbook §2.3 [DANGER]."

  validation {
    condition     = length(var.founder_ip_ranges) > 0 && !contains(var.founder_ip_ranges, "0.0.0.0/0")
    error_message = "founder_ip_ranges must be a non-empty list of CIDR blocks and must not contain 0.0.0.0/0. Opening K3s API (tcp:6443) to the world violates playbook §2.3 [DANGER]."
  }
}
