# Purpose: GCP Compute instance for the K3s single-node cluster host.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §8 (K3s install strategy — cloud-init),
#                 §14 (prevent_destroy), §6 (resource mapping — VM row).
# Note: Zone is hardcoded to asia-south1-a (the account lock constant) rather than passed as
#       a variable. The zone is a project-level constant like the project ID — it should never
#       differ between dev/staging/prod on this single-node cluster. Passing it as a variable
#       would enable accidental zone drift.
# Note: secure_boot is set to false per the playbook §2.2 gcloud command
#       (--no-shielded-secure-boot). vtpm and integrity_monitoring are true per the same command.

resource "google_compute_instance" "meesell_dev" {
  name         = var.vm_name
  machine_type = var.machine_type
  zone         = "asia-south1-a"

  tags = ["k3s-server", "http-server", "https-server"]

  labels = {
    env     = var.environment
    project = "meesell"
    owner   = "founder"
  }

  boot_disk {
    initialize_params {
      image = "projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts"
      size  = var.vm_disk_size_gb
      type  = "pd-balanced"
    }
    auto_delete = true
  }

  network_interface {
    network    = "default"
    subnetwork = "default"

    access_config {
      # Ephemeral public IP — matches playbook §2.2 (PREMIUM network tier default)
      network_tier = "PREMIUM"
    }
  }

  service_account {
    # Default compute service account — cloud-platform scope allows K3s nodes to pull
    # from Artifact Registry and write to GCS without a separate service account key.
    # The workload identity binding is established in module.ci_identity.
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }

  metadata = {
    startup-script = templatefile("${path.module}/templates/startup.sh.tftpl", {
      vm_name = var.vm_name
    })
  }

  shielded_instance_config {
    enable_vtpm                 = true
    enable_integrity_monitoring = true
    enable_secure_boot          = false
  }

  scheduling {
    on_host_maintenance = "MIGRATE"
    automatic_restart   = true
    provisioning_model  = "STANDARD"
  }

  lifecycle {
    # DANGER: Destroying this instance destroys the entire K3s cluster.
    # Removal requires a deliberate code change reviewed by the founder
    # per playbook §0 [DANGER] and plan §14.
    prevent_destroy = true

    # Ignore changes to the startup_script after first boot — the script runs once
    # on VM creation and re-running it on VM restart is a no-op (K3s installer is
    # idempotent). Ignoring metadata changes prevents Terraform from replacing the VM
    # if the script template changes (use `terraform taint` if a re-run is needed).
    ignore_changes = [metadata]
  }
}
