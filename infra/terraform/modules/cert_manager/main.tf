# Purpose: cert-manager controller via Helm (Jetstack chart).
# Plan ref: §9 cert_manager module, §8 playbook. Issues TLS certs via Let's Encrypt.
# Note: ClusterIssuer lives in module.ingress (depends on this module's CRDs).

terraform {
  required_providers {
    helm       = { source = "hashicorp/helm", version = "~> 2.13" }
    kubernetes = { source = "hashicorp/kubernetes", version = "~> 2.30" }
    time       = { source = "hashicorp/time", version = "~> 0.11" }
  }
}

resource "kubernetes_namespace" "cert_manager" {
  metadata {
    name   = "cert-manager"
    labels = { env = "system" }
  }
}

resource "helm_release" "cert_manager" {
  name       = "cert-manager"
  repository = "https://charts.jetstack.io"
  chart      = "cert-manager"
  version    = var.chart_version
  namespace  = kubernetes_namespace.cert_manager.metadata[0].name

  # cert-manager v1.14.x uses `installCRDs` (boolean) as the Helm chart value.
  # In v1.15+ this becomes `crds.enabled` / `crds.keep`. Keep this aligned with
  # the var.chart_version pin (currently v1.14.5 per playbook §8.2).
  set {
    name  = "installCRDs"
    value = "true"
  }
  # The startup API check Job can race the webhook on slow clusters; skip it.
  # The chart's main controller has its own readiness probes that we rely on.
  set {
    name  = "startupapicheck.enabled"
    value = "false"
  }
  # Modest resources — cert-manager is lightweight
  set {
    name  = "resources.requests.cpu"
    value = "50m"
  }
  set {
    name  = "resources.requests.memory"
    value = "128Mi"
  }
  set {
    name  = "webhook.resources.requests.cpu"
    value = "50m"
  }
  set {
    name  = "webhook.resources.requests.memory"
    value = "128Mi"
  }
  set {
    name  = "cainjector.resources.requests.cpu"
    value = "50m"
  }
  set {
    name  = "cainjector.resources.requests.memory"
    value = "128Mi"
  }

  wait    = true
  timeout = 600
}

# Settle delay so CRDs are fully registered with the API server before any
# ClusterIssuer/Certificate is created against them.
resource "time_sleep" "cert_manager_settle" {
  depends_on      = [helm_release.cert_manager]
  create_duration = "30s"
}
