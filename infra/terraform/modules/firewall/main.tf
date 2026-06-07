# Purpose: Three firewall rules for the meesell-dev VM (http, https, k3s-api).
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §6 (resource mapping — firewall rows),
#                 §9 (module: firewall), §18 item 8.
# Note: network = "default" per playbook §2.3. The project is not passed as a variable —
#       it is resolved from the google provider configuration in providers.tf (account lock Layer A).
# DANGER: meesell_dev_k3s_api source_ranges is ${var.founder_ip}/32 — never 0.0.0.0/0.
#         The validation block in variables.tf enforces this at plan time.

resource "google_compute_firewall" "meesell_dev_http" {
  name    = "meesell-dev-http"
  network = "default"

  description = "Allow inbound HTTP (tcp:80) to meesell-dev from anywhere. Traefik handles HTTPS redirect."

  allow {
    protocol = "tcp"
    ports    = ["80"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["http-server"]
}

resource "google_compute_firewall" "meesell_dev_https" {
  name    = "meesell-dev-https"
  network = "default"

  description = "Allow inbound HTTPS (tcp:443) to meesell-dev from anywhere. TLS terminated by Traefik + cert-manager."

  allow {
    protocol = "tcp"
    ports    = ["443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["https-server"]
}

resource "google_compute_firewall" "meesell_dev_k3s_api" {
  name    = "meesell-dev-k3s-api"
  network = "default"

  # DANGER: This rule MUST be scoped to known ISP CIDR ranges — never 0.0.0.0/0.
  # Playbook §2.3 updated: use ISP-level CIDRs (e.g. Airtel TN /18, Jio /21) instead of
  # individual /32 IPs. This survives dynamic IP rotation within the same ISP without
  # requiring a terraform apply on every reconnect.
  # Set in dev.tfvars as: founder_ip_ranges = ["122.164.64.0/18", "152.57.80.0/21"]
  description = "Allow K3s API server (tcp:6443) from founder ISP CIDR ranges. Scoped per playbook §2.3 [DANGER] — no 0.0.0.0/0."

  allow {
    protocol = "tcp"
    ports    = ["6443"]
  }

  source_ranges = var.founder_ip_ranges
  target_tags   = ["k3s-server"]
}
