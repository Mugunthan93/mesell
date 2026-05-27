resource "google_compute_instance" "vm" {
  name         = local.vm_name
  machine_type = var.vm_machine_type
  zone         = var.zone
  tags         = ["meesell-public"]
  labels       = var.labels

  boot_disk {
    initialize_params {
      image = var.vm_image
      size  = var.vm_disk_size_gb
      type  = var.vm_disk_type
    }
  }

  network_interface {
    network = "default"
    access_config {
      nat_ip       = google_compute_address.static.address
      network_tier = "PREMIUM"
    }
  }

  service_account {
    email = google_service_account.workload.email
    # cloud-platform covers Secret Manager, Storage, AR, etc. We rely on
    # the IAM bindings (not scope) to actually authorize each call.
    scopes = ["cloud-platform"]
  }

  metadata = {
    ssh-keys = local.ssh_metadata_value
    startup-script = templatefile("${path.module}/templates/startup.sh", {
      project_id        = var.project_id
      region            = var.region
      name_prefix       = var.name_prefix
      bucket_name       = google_storage_bucket.assets.name
      registry_url      = local.registry_url
      workload_sa_email = google_service_account.workload.email
      domain            = var.domain
    })
  }

  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }

  depends_on = [
    google_compute_address.static,
    google_service_account.workload,
    google_storage_bucket.assets,
    google_artifact_registry_repository.images,
    google_secret_manager_secret_version.version,
  ]
}
