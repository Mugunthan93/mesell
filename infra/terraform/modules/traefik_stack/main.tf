# Purpose: Traefik ingress controller via Helm. Deployed Pass 2.
# Plan ref: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §9, §20 / Playbook §8.1.
# Note: cert-manager + Ingress resources deferred to Pass 2b until founder provides domain.
#       Traefik itself is deployed now so it's ready when those land.

terraform {
  required_providers {
    kubernetes = { source = "hashicorp/kubernetes", version = "~> 2.30" }
    helm       = { source = "hashicorp/helm", version = "~> 2.13" }
  }
}

resource "kubernetes_namespace" "traefik" {
  metadata {
    name   = "traefik"
    labels = { env = "system" }
  }
}

resource "helm_release" "traefik" {
  name       = "traefik"
  repository = "https://traefik.github.io/charts"
  chart      = "traefik"
  version    = var.chart_version
  namespace  = kubernetes_namespace.traefik.metadata[0].name

  set {
    name  = "service.type"
    value = "LoadBalancer"
  }
  set {
    name  = "ports.web.port"
    value = "80"
  }
  set {
    name  = "ports.websecure.port"
    value = "443"
  }
  set {
    name  = "additionalArguments[0]"
    value = "--api.dashboard=false"
  }

  timeout = 300
}
