# Purpose: Outputs for the vm module.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §9 (module: vm outputs).

output "vm_external_ip" {
  value       = google_compute_instance.meesell_dev.network_interface[0].access_config[0].nat_ip
  description = "External (ephemeral) public IP of the meesell-dev VM."
}

output "vm_instance_self_link" {
  value       = google_compute_instance.meesell_dev.self_link
  description = "Self-link of the GCP compute instance (for use in other GCP resources that reference the instance)."
}

output "vm_name" {
  value       = google_compute_instance.meesell_dev.name
  description = "Computed name of the VM instance."
}
