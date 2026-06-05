# Purpose: Create Kubernetes namespaces for each environment (dev, staging).
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §9 (module boundaries), §11 (Pass 2 bootstrap order).
# Playbook reference: docs/INFRASTRUCTURE_PLAYBOOK.md §4 (Namespace Setup).
# Choices:
#   - for_each over a map(string) so namespaces are addressed individually in state
#     (no index drift when adding/removing namespaces).
#   - prod is NOT in the default map — playbook §15(c) defers prod to Week 2.
#   - Labels: env=<value> mirrors the kubectl label applied in §4 manually.

resource "kubernetes_namespace" "ns" {
  for_each = var.namespaces

  metadata {
    name = each.key
    labels = {
      env = each.value
    }
  }
}
