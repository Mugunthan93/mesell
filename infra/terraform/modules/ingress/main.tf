# Purpose: ClusterIssuer (Let's Encrypt) + Ingress for studio.<domain> with TLS.
# Plan ref: §9 ingress module, playbook §9. HTTP-01 challenge via Traefik.

terraform {
  required_providers {
    kubernetes = { source = "hashicorp/kubernetes", version = "~> 2.30" }
  }
}

# ClusterIssuer — defines the ACME (Let's Encrypt) configuration.
# HTTP-01 challenge solver routes via Traefik ingress class.
resource "kubernetes_manifest" "cluster_issuer_letsencrypt_prod" {
  manifest = {
    apiVersion = "cert-manager.io/v1"
    kind       = "ClusterIssuer"
    metadata = {
      name = "letsencrypt-prod"
    }
    spec = {
      acme = {
        server = "https://acme-v02.api.letsencrypt.org/directory"
        email  = var.acme_email
        privateKeySecretRef = {
          name = "letsencrypt-prod-key"
        }
        solvers = [
          {
            http01 = {
              ingress = {
                class = "traefik"
              }
            }
          }
        ]
      }
    }
  }
}

# Ingress for studio.<domain> — TLS provisioned by ClusterIssuer above.
resource "kubernetes_ingress_v1" "studio" {
  metadata {
    name      = "studio"
    namespace = var.namespace
    annotations = {
      "cert-manager.io/cluster-issuer"                   = "letsencrypt-prod"
      "traefik.ingress.kubernetes.io/router.entrypoints" = "websecure"
      "traefik.ingress.kubernetes.io/router.tls"         = "true"
    }
  }
  spec {
    ingress_class_name = "traefik"
    rule {
      host = "studio.${var.domain}"
      http {
        path {
          path      = "/"
          path_type = "Prefix"
          backend {
            service {
              name = var.studio_service_name
              port {
                number = var.studio_service_port
              }
            }
          }
        }
      }
    }
    tls {
      hosts       = ["studio.${var.domain}"]
      secret_name = "studio-tls"
    }
  }

  depends_on = [kubernetes_manifest.cluster_issuer_letsencrypt_prod]
}

# Ingress for api.<domain> — FastAPI backend (dev namespace).
resource "kubernetes_ingress_v1" "api" {
  metadata {
    name      = "api"
    namespace = var.namespace
    annotations = {
      "cert-manager.io/cluster-issuer"                   = "letsencrypt-prod"
      "traefik.ingress.kubernetes.io/router.entrypoints" = "websecure"
      "traefik.ingress.kubernetes.io/router.tls"         = "true"
    }
  }
  spec {
    ingress_class_name = "traefik"
    rule {
      host = "api.${var.domain}"
      http {
        path {
          path      = "/"
          path_type = "Prefix"
          backend {
            service {
              name = var.api_service_name
              port {
                number = var.api_service_port
              }
            }
          }
        }
      }
    }
    tls {
      hosts       = ["api.${var.domain}"]
      secret_name = "api-tls"
    }
  }

  depends_on = [kubernetes_manifest.cluster_issuer_letsencrypt_prod]
}

# Ingress for dev.<domain> — Angular frontend (dev namespace, dev environment).
resource "kubernetes_ingress_v1" "dev_frontend" {
  metadata {
    name      = "dev-frontend"
    namespace = var.namespace
    annotations = {
      "cert-manager.io/cluster-issuer"                   = "letsencrypt-prod"
      "traefik.ingress.kubernetes.io/router.entrypoints" = "websecure"
      "traefik.ingress.kubernetes.io/router.tls"         = "true"
    }
  }
  spec {
    ingress_class_name = "traefik"
    rule {
      host = "dev.${var.domain}"
      http {
        path {
          path      = "/"
          path_type = "Prefix"
          backend {
            service {
              name = var.frontend_service_name
              port {
                number = var.frontend_service_port
              }
            }
          }
        }
      }
    }
    tls {
      hosts       = ["dev.${var.domain}"]
      secret_name = "dev-frontend-tls"
    }
  }

  depends_on = [kubernetes_manifest.cluster_issuer_letsencrypt_prod]
}

# Ingress for testing.<domain> — Angular frontend (dev namespace, testing environment).
resource "kubernetes_ingress_v1" "testing_frontend" {
  metadata {
    name      = "testing-frontend"
    namespace = var.namespace
    annotations = {
      "cert-manager.io/cluster-issuer"                   = "letsencrypt-prod"
      "traefik.ingress.kubernetes.io/router.entrypoints" = "websecure"
      "traefik.ingress.kubernetes.io/router.tls"         = "true"
    }
  }
  spec {
    ingress_class_name = "traefik"
    rule {
      host = "testing.${var.domain}"
      http {
        path {
          path      = "/"
          path_type = "Prefix"
          backend {
            service {
              name = var.frontend_service_name
              port {
                number = var.frontend_service_port
              }
            }
          }
        }
      }
    }
    tls {
      hosts       = ["testing.${var.domain}"]
      secret_name = "testing-frontend-tls"
    }
  }

  depends_on = [kubernetes_manifest.cluster_issuer_letsencrypt_prod]
}

# Ingress for staging.<domain> — Angular frontend (staging namespace).
resource "kubernetes_ingress_v1" "staging_frontend" {
  metadata {
    name      = "staging-frontend"
    namespace = var.staging_namespace
    annotations = {
      "cert-manager.io/cluster-issuer"                   = "letsencrypt-prod"
      "traefik.ingress.kubernetes.io/router.entrypoints" = "websecure"
      "traefik.ingress.kubernetes.io/router.tls"         = "true"
    }
  }
  spec {
    ingress_class_name = "traefik"
    rule {
      host = "staging.${var.domain}"
      http {
        path {
          path      = "/"
          path_type = "Prefix"
          backend {
            service {
              name = var.frontend_service_name
              port {
                number = var.frontend_service_port
              }
            }
          }
        }
      }
    }
    tls {
      hosts       = ["staging.${var.domain}"]
      secret_name = "staging-frontend-tls"
    }
  }

  depends_on = [kubernetes_manifest.cluster_issuer_letsencrypt_prod]
}
