# Purpose: Root-level outputs for post-apply reference and hand-off to operators.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §10 (root-level outputs).
# Note: Pass 2 outputs (postgres_service_host, valkey_service_host, traefik_lb_ip,
#       ingress_host) are commented out until those modules are added in the second
#       iteration. Uncommenting before the modules exist causes a plan error.

output "vm_external_ip" {
  value       = module.vm.vm_external_ip
  description = "External IP of the meesell-dev VM. Use this to update the K3s API firewall rule when your IP changes: terraform apply -var=\"founder_ip=<new_ip>\"."
}

output "kubeconfig_reminder" {
  value       = <<-EOT
    After Pass 1 is applied and K3s has started (~5 minutes), retrieve the kubeconfig:

      VM_IP=$(cd infra/terraform && terraform output -raw vm_external_ip)
      gcloud compute scp meesell-dev:/etc/rancher/k3s/k3s.yaml \
        ~/.kube/meesell-dev.yaml --zone=asia-south1-a
      sed -i.bak "s/127.0.0.1/$${VM_IP}/g" ~/.kube/meesell-dev.yaml
      chmod 600 ~/.kube/meesell-dev.yaml
      kubectl --kubeconfig=~/.kube/meesell-dev.yaml get nodes  # must show Ready

    Then uncomment the kubernetes/helm providers in providers.tf and run:
      make -f Makefile.tf tf-init-pass2
  EOT
  description = "Post-apply instructions for kubeconfig retrieval (playbook §3.3)."
}

output "billing_budget_name" {
  value       = module.billing_budget.budget_name
  description = "GCP billing budget display name. Check GCP Console → Billing → Budgets to confirm alerts are wired to vaishnaviramoorthy@gmail.com."
}

output "artifact_registry_url" {
  value       = module.artifact_registry.repository_url
  description = "Full Docker push URL for the production registry. Set as IMAGE_REGISTRY in GitLab CI variables."
}

output "asset_bucket_url" {
  value       = module.asset_bucket.bucket_url
  description = "GCS bucket URL for the production asset bucket. Set as GCS_BUCKET in backend/.env."
}

output "ci_sa_email" {
  value       = module.ci_identity.ci_sa_email
  description = "CI service account email. Set as SERVICE_ACCOUNT_EMAIL in GitLab CI project variables (masked)."
}

output "wif_provider_name" {
  value       = module.ci_identity.wif_provider_resource_name
  description = "Full WIF provider resource name. Set as WORKLOAD_IDENTITY_PROVIDER in GitLab CI project variables (masked)."
}

output "ci_sa_impersonation_member" {
  value       = module.ci_identity.ci_sa_impersonation_member
  description = "The principalSet member string used in the WIF → SA IAM binding. For reference only."
}

output "app_secret_resource_names" {
  value       = module.app_secrets.secret_resource_names
  description = "Map of secret_id -> full Secret Manager resource name. Use these resource names when granting secretAccessor IAM bindings to K8s workloads in Pass 2."
}

# --- Pass 2 outputs ---

output "postgres_dev_service_host" {
  description = "In-cluster Postgres hostname for dev namespace."
  value       = module.postgres_dev.service_hostname
}

output "valkey_dev_service_host" {
  description = "In-cluster Valkey hostname for dev namespace."
  value       = module.valkey_dev.service_hostname
}

output "traefik_lb_ip" {
  description = "Traefik LoadBalancer IP (may be empty initially on single-node K3s)."
  value       = module.traefik_stack.traefik_lb_ip
}

# --- Pass 2b outputs ---

output "ingress_host" {
  description = "Public hostname for Supabase Studio."
  value       = try(module.ingress.ingress_host, "")
}

output "cluster_issuer_name" {
  description = "Let's Encrypt ClusterIssuer name (Pass 2b)."
  value       = try(module.ingress.cluster_issuer_name, "")
}

# --- Phase B outputs ---

output "api_host" {
  description = "Public hostname for the FastAPI backend."
  value       = try(module.ingress.api_host, "")
}

output "dev_frontend_host" {
  description = "Public hostname for the Angular frontend (dev environment)."
  value       = try(module.ingress.dev_frontend_host, "")
}

output "testing_frontend_host" {
  description = "Public hostname for the Angular frontend (testing environment)."
  value       = try(module.ingress.testing_frontend_host, "")
}

output "staging_frontend_host" {
  description = "Public hostname for the Angular frontend (staging environment)."
  value       = try(module.ingress.staging_frontend_host, "")
}
