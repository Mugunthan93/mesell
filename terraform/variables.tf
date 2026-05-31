variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "GCP region (Meesho buyer base is heavily India-North/West)."
  type        = string
  default     = "asia-south1"
}

variable "zone" {
  description = "GCP zone within the region."
  type        = string
  default     = "asia-south1-a"
}

variable "name_prefix" {
  description = "Prefix applied to all resource names."
  type        = string
  default     = "meesell"
}

variable "labels" {
  description = "Labels applied to every resource that supports them."
  type        = map(string)
  default = {
    app     = "meesell"
    managed = "terraform"
  }
}

# ----- Compute --------------------------------------------------------------

variable "vm_machine_type" {
  description = "GCE machine type. e2-standard-2 = 2 vCPU / 8 GB; sufficient for MVP."
  type        = string
  default     = "e2-standard-2"
}

variable "vm_disk_size_gb" {
  description = "Boot disk size. Needs headroom for K3s + Postgres data + container images."
  type        = number
  default     = 50
}

variable "vm_disk_type" {
  description = "GCE persistent disk type."
  type        = string
  default     = "pd-balanced"
}

variable "vm_image" {
  description = "VM OS image. Ubuntu 24.04 LTS is what setup-vm.sh targets."
  type        = string
  default     = "ubuntu-os-cloud/ubuntu-2404-lts-amd64"
}

variable "ssh_user" {
  description = "OS login user the SSH key authorizes."
  type        = string
  default     = "claude"
}

variable "ssh_public_key" {
  description = "SSH public key contents (the whole 'ssh-ed25519 AAAA... user@host' line)."
  type        = string
  sensitive   = true
}

variable "ssh_source_cidrs" {
  description = "Source CIDR ranges allowed to reach SSH (22). Narrow this to your office/VPN IP for production."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# ----- Storage --------------------------------------------------------------

variable "bucket_location" {
  description = "Multi-region or region for the GCS bucket. Match the API region to avoid egress cost."
  type        = string
  default     = "ASIA-SOUTH1"
}

variable "bucket_force_destroy" {
  description = "If true, terraform destroy nukes the bucket even if it has objects. Leave false in prod."
  type        = bool
  default     = false
}

# ----- DNS ------------------------------------------------------------------

variable "manage_dns" {
  description = "If true, create a Cloud DNS managed zone + A records for the apex, www, and api subdomains of `domain`."
  type        = bool
  default     = true
}

variable "domain" {
  description = "Public domain (e.g. meesell.in). Required when manage_dns = true."
  type        = string
  default     = ""
}

# ----- Secrets the operator must provide ------------------------------------

variable "gemini_api_key" {
  description = "Google Gemini API key for catalog generation."
  type        = string
  sensitive   = true
  default     = "AIza_replace_me"
}

variable "msg91_auth_key" {
  description = "MSG91 auth key for OTP SMS dispatch."
  type        = string
  sensitive   = true
  default     = "replace_me"
}

variable "msg91_template_id" {
  description = "MSG91 OTP template ID."
  type        = string
  sensitive   = true
  default     = "replace_me"
}

variable "razorpay_key_id" {
  description = "Razorpay subscription key ID."
  type        = string
  sensitive   = true
  default     = "rzp_test_replace_me"
}

variable "razorpay_key_secret" {
  description = "Razorpay subscription key secret."
  type        = string
  sensitive   = true
  default     = "replace_me"
}

variable "github_repository" {
  description = "Full GitHub repository path (owner/repo). Restricts which GitHub repo may exchange OIDC tokens for the CI SA. Example: Mugunthan93/mesell"
  type        = string
  default     = "Mugunthan93/mesell"
}

variable "github_issuer_uri" {
  description = "GitHub Actions OIDC issuer. Fixed value for github.com."
  type        = string
  default     = "https://token.actions.githubusercontent.com"
}
