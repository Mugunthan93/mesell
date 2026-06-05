# Purpose: Provider configuration with hardcoded account lock constants.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §19 Layer A.
# LAYER A — Account Lock per docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §19.
# Project is hardcoded as a string literal. Override requires a code change reviewed by the founder.
# There is intentionally NO var.project_id — removing the variable removes the attack surface.

provider "google" {
  project = "project-1f5cbf72-2820-4cdb-949"
  region  = "asia-south1"
  zone    = "asia-south1-a"
}

provider "google-beta" {
  project = "project-1f5cbf72-2820-4cdb-949"
  region  = "asia-south1"
  zone    = "asia-south1-a"

  # billingbudgets.googleapis.com requires an explicit quota project when authenticating
  # via GOOGLE_OAUTH_ACCESS_TOKEN (no implicit quota project is set with token-only auth).
  # user_project_override + billing_project direct quota billing to our project.
  user_project_override = true
  billing_project       = "project-1f5cbf72-2820-4cdb-949"
}

# =============================================================================
# PASS 2 PROVIDERS — Uncomment after kubeconfig retrieval per playbook §3.3
# and `make -f Makefile.tf tf-init-pass2`
#
# Bootstrap sequence:
#   1. Run Pass 1 (make tf-apply-pass1) — creates VM, installs K3s via startup script.
#   2. Wait ~5 minutes for K3s to come up on the VM.
#   3. Retrieve kubeconfig:
#        VM_IP=$(cd infra/terraform && terraform output -raw vm_external_ip)
#        gcloud compute scp meesell-dev:/etc/rancher/k3s/k3s.yaml \
#          ~/.kube/meesell-dev.yaml --zone=asia-south1-a
#        sed -i.bak "s/127.0.0.1/${VM_IP}/g" ~/.kube/meesell-dev.yaml
#        chmod 600 ~/.kube/meesell-dev.yaml
#        kubectl --kubeconfig=~/.kube/meesell-dev.yaml get nodes  # must show Ready
#   4. Set KUBECONFIG_PATH env var to ~/.kube/meesell-dev.yaml.
#   5. Uncomment the kubernetes and helm provider blocks below.
#   6. Run: make -f Makefile.tf tf-init-pass2
#   7. Run: make -f Makefile.tf tf-plan-pass2 FOUNDER_IP=<ip>
# =============================================================================

provider "kubernetes" {
  config_path    = pathexpand(var.kubeconfig_path)
  config_context = "default"
}

provider "helm" {
  kubernetes {
    config_path    = pathexpand(var.kubeconfig_path)
    config_context = "default"
  }
}
