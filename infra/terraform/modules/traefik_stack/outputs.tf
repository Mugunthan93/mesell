# Purpose: Outputs for the traefik_stack module.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §10 (outputs).
# Note: traefik_lb_ip is best-effort. On single-node K3s without an external LB, the Service
#       may stay Pending or use the node IP. Empty value is acceptable initially.

output "traefik_lb_ip" {
  description = "External IP of the Traefik LoadBalancer service (may be empty initially on single-node K3s)."
  value = try(
    data.kubernetes_service.traefik.status[0].load_balancer[0].ingress[0].ip,
    ""
  )
}

data "kubernetes_service" "traefik" {
  metadata {
    name      = "traefik"
    namespace = "traefik"
  }
  depends_on = [helm_release.traefik]
}
