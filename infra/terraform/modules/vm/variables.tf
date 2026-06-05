# Purpose: Input variables for the vm module.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §9 (module: vm), §18 file list item 7.

variable "vm_name" {
  type        = string
  description = "GCP Compute instance name (e.g. meesell-dev). Used as the node name in K3s startup script."
}

variable "machine_type" {
  type        = string
  description = "GCP machine type (e.g. e2-standard-2)."
}

variable "vm_disk_size_gb" {
  type        = number
  description = "Boot disk size in GB."
}

variable "environment" {
  type        = string
  description = "Environment label (dev, staging, prod). Applied as a resource label."
}
