# Purpose: Outputs for the firewall module.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §9 (module: firewall outputs).

output "firewall_rule_names" {
  value = [
    google_compute_firewall.meesell_dev_http.name,
    google_compute_firewall.meesell_dev_https.name,
    google_compute_firewall.meesell_dev_k3s_api.name,
  ]
  description = "Names of the three firewall rules created for meesell-dev."
}
