# Purpose: Deploy Valkey 8 (Redis-compatible) as a StatefulSet with PVC, headless Service, and Kubernetes Secret.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §9 (module boundaries), §11 (Pass 2), §14 (prevent_destroy).
# Playbook reference: docs/INFRASTRUCTURE_PLAYBOOK.md §6 (Valkey Deployment).
# Choices:
#   - Secret uses ignore_changes lifecycle so Terraform never overwrites a rotated password.
#   - args inject --requirepass and --appendonly yes per playbook §6.2.
#   - readinessProbe uses sh -c wrapper to expand $VALKEY_PASSWORD at runtime (same as playbook §6.2).
#   - prevent_destroy on StatefulSet protects PVC (data is appendonly.aof — loss is unrecoverable).

resource "kubernetes_secret" "valkey_credentials" {
  metadata {
    name      = "valkey-credentials"
    namespace = var.namespace
  }

  data = {
    password = var.valkey_password
  }

  lifecycle {
    ignore_changes = [data]
  }
}

resource "kubernetes_service" "valkey" {
  metadata {
    name      = "valkey"
    namespace = var.namespace
  }

  spec {
    cluster_ip = "None"

    selector = {
      app = "valkey"
    }

    port {
      name = "valkey"
      port = 6379
    }
  }
}

resource "kubernetes_stateful_set" "valkey" {
  metadata {
    name      = "valkey"
    namespace = var.namespace
  }

  spec {
    replicas     = 1
    service_name = kubernetes_service.valkey.metadata[0].name

    selector {
      match_labels = {
        app = "valkey"
      }
    }

    template {
      metadata {
        labels = {
          app = "valkey"
        }
      }

      spec {
        container {
          name    = "valkey"
          image   = "valkey/valkey:${var.image_tag}"
          command = ["valkey-server"]
          args    = ["--requirepass", "$(VALKEY_PASSWORD)", "--appendonly", "yes", "--maxmemory", "128mb", "--maxmemory-policy", "allkeys-lru"]

          port {
            container_port = 6379
          }

          env {
            name = "VALKEY_PASSWORD"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.valkey_credentials.metadata[0].name
                key  = "password"
              }
            }
          }

          resources {
            requests = {
              cpu    = "100m"
              memory = "200Mi"
            }
            limits = {
              cpu    = "500m"
              memory = "512Mi"
            }
          }

          readiness_probe {
            exec {
              command = ["sh", "-c", "valkey-cli -a \"$VALKEY_PASSWORD\" ping | grep PONG"]
            }
            initial_delay_seconds = 5
            period_seconds        = 5
          }

          volume_mount {
            name       = "data"
            mount_path = "/data"
          }
        }
      }
    }

    volume_claim_template {
      metadata {
        name = "data"
      }

      spec {
        access_modes = ["ReadWriteOnce"]

        resources {
          requests = {
            storage = "${var.storage_gb}Gi"
          }
        }
      }
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}
