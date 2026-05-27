resource "google_compute_address" "static" {
  name         = "${var.name_prefix}-ip"
  region       = var.region
  address_type = "EXTERNAL"
  network_tier = "PREMIUM"
  labels       = var.labels

  depends_on = [google_project_service.enabled]
}

resource "google_compute_firewall" "allow_http_https" {
  name    = "${var.name_prefix}-allow-http-https"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["meesell-public"]

  depends_on = [google_project_service.enabled]
}

resource "google_compute_firewall" "allow_ssh" {
  name    = "${var.name_prefix}-allow-ssh"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = var.ssh_source_cidrs
  target_tags   = ["meesell-public"]

  depends_on = [google_project_service.enabled]
}
