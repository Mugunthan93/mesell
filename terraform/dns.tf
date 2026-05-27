# Cloud DNS zone + records. Skipped entirely if manage_dns = false (use this
# when your registrar already runs the zone elsewhere; then point an A record
# at vm_external_ip yourself).

resource "google_dns_managed_zone" "primary" {
  count       = var.manage_dns ? 1 : 0
  name        = local.dns_zone_name
  dns_name    = "${var.domain}."
  description = "MeeSell public DNS zone."
  labels      = var.labels
  visibility  = "public"

  depends_on = [google_project_service.enabled]
}

resource "google_dns_record_set" "apex" {
  count        = var.manage_dns ? 1 : 0
  managed_zone = google_dns_managed_zone.primary[0].name
  name         = google_dns_managed_zone.primary[0].dns_name
  type         = "A"
  ttl          = 300
  rrdatas      = [google_compute_address.static.address]
}

resource "google_dns_record_set" "www" {
  count        = var.manage_dns ? 1 : 0
  managed_zone = google_dns_managed_zone.primary[0].name
  name         = "www.${google_dns_managed_zone.primary[0].dns_name}"
  type         = "A"
  ttl          = 300
  rrdatas      = [google_compute_address.static.address]
}

resource "google_dns_record_set" "api" {
  count        = var.manage_dns ? 1 : 0
  managed_zone = google_dns_managed_zone.primary[0].name
  name         = "api.${google_dns_managed_zone.primary[0].dns_name}"
  type         = "A"
  ttl          = 300
  rrdatas      = [google_compute_address.static.address]
}
