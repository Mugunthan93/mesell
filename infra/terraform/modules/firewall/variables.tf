# Purpose: Input variables for the firewall module.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §9 (module: firewall), §18 item 8.

variable "founder_ip" {
  type        = string
  description = "Founder's current public IPv4 address. Used to scope the K3s API firewall rule (tcp:6443) to /32. Must not be 0.0.0.0 — opening K3s API to the world violates playbook §2.3 [DANGER]."

  validation {
    # can(cidrhost(...)) validates the IP is a valid IPv4/CIDR; != "0.0.0.0" enforces minimum scope.
    condition     = can(cidrhost("${var.founder_ip}/32", 0)) && var.founder_ip != "0.0.0.0"
    error_message = "founder_ip must be a valid non-zero IPv4 address (e.g. 203.0.113.45). Value '${var.founder_ip}' is invalid or is the catch-all 0.0.0.0. Playbook §2.3 [DANGER] prohibits opening tcp:6443 to the world. Capture your current IP with: export FOUNDER_IP=$(curl -s ifconfig.me). See plan §19 for the account lock rationale."
  }
}
