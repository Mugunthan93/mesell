locals {
  vm_name            = "${var.name_prefix}-vm"
  workload_sa_id     = "${var.name_prefix}-workload"
  bucket_name        = "${var.project_id}-${var.name_prefix}-assets"
  registry_id        = "${var.name_prefix}-images"
  registry_url       = "${var.region}-docker.pkg.dev/${var.project_id}/${local.registry_id}"
  dns_zone_name      = replace(var.domain, ".", "-")
  ssh_metadata_value = "${var.ssh_user}:${var.ssh_public_key}"
}
