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

  # DANGER: This rule MUST be scoped to the founder's /32 IP.
  # Playbook §2.3: "meesell-dev-k3s-api sourceRanges MUST equal ${FOUNDER_IP}/32, never 0.0.0.0/0."
  # When the founder's IP changes: terraform apply -var="founder_ip=<new_ip>" — Terraform updates
  # this resource and the validation block ensures the new value is also never 0.0.0.0.
  description = "Allow K3s API server (tcp:6443) from founder IP only. Scoped to /32 per playbook §2.3 [DANGER]."

  allow {
    protocol = "tcp"
    ports    = ["6443"]
  }

  source_ranges = ["${var.founder_ip}/32"]
  target_tags   = ["k3s-server"]
}
