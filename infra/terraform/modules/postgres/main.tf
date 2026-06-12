# Purpose: Deploy PostgreSQL 16 as a StatefulSet with PVC, headless Service, and Kubernetes Secret.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §9 (module boundaries), §11 (Pass 2), §14 (prevent_destroy).
# Playbook reference: docs/INFRASTRUCTURE_PLAYBOOK.md §5 (PostgreSQL Deployment).
# Choices:
#   - Secret uses ignore_changes lifecycle so Terraform never overwrites a rotated password.
#   - PVC via volumeClaimTemplates in the StatefulSet — provisioned by K3s local-path.
#   - prevent_destroy on PVC template enforces playbook §5 rollback discipline (no silent data loss).
#   - PGDATA set to /var/lib/postgresql/data/pgdata (subdirectory) to avoid Docker-volume-in-mountpoint issue.
#   - readinessProbe delays match playbook §5.2 values exactly.

resource "kubernetes_secret" "postgres_credentials" {
  metadata {
    name      = "postgres-credentials"
    namespace = var.namespace
  }

  data = {
    username = "meesell"
    password = var.postgres_password
    database = "meesell"
  }

  lifecycle {
    ignore_changes = [data]
  }
}

resource "kubernetes_service" "postgres" {
  metadata {
    name      = "postgres"
    namespace = var.namespace
  }

  spec {
    cluster_ip = "None"

    selector = {
      app = "postgres"
    }

    port {
      name = "postgres"
      port = 5432
    }
  }
}

resource "kubernetes_stateful_set" "postgres" {
  metadata {
    name      = "postgres"
    namespace = var.namespace
  }

  spec {
    replicas     = 1
    service_name = kubernetes_service.postgres.metadata[0].name

    selector {
      match_labels = {
        app = "postgres"
      }
    }

    template {
      metadata {
        labels = {
          app = "postgres"
        }
      }

      spec {
        container {
          name  = "postgres"
          image = "postgres:${var.image_tag}"

          # I8 / MS-DB-3 (microservices-export Sub-Plan A) — minimal additive pool
          # right-size. Default postgres:16 max_connections=100 is insufficient once
          # the monolith + svc-export both hold pools during the strangler window
          # (infra plan §3.3 / R-MS-1). Bump to 200 BEFORE any service moves.
          # Memory cost ~+500MB worst case (~5MB/conn × +100) — fits the 1Gi limit
          # headroom at dev idle. This ships ahead of the service per founder ruling
          # D5 (MS-DB-3 first). PgBouncer (MS-DB-4) is NOT in Sub-Plan A.
          # `-c max_connections=200` is passed as a server arg (postgres entrypoint
          # appends `args` to the `postgres` command), the least-intrusive way to set
          # a GUC without a custom postgresql.conf ConfigMap mount.
          args = ["-c", "max_connections=200"]

          port {
            container_port = 5432
          }

          env {
            name = "POSTGRES_USER"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.postgres_credentials.metadata[0].name
                key  = "username"
              }
            }
          }

          env {
            name = "POSTGRES_PASSWORD"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.postgres_credentials.metadata[0].name
                key  = "password"
              }
            }
          }

          env {
            name = "POSTGRES_DB"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.postgres_credentials.metadata[0].name
                key  = "database"
              }
            }
          }

          env {
            name  = "PGDATA"
            value = "/var/lib/postgresql/data/pgdata"
          }

          resources {
            requests = {
              cpu    = "200m"
              memory = "500Mi"
            }
            limits = {
              cpu    = "1000m"
              memory = "1Gi"
            }
          }

          readiness_probe {
            exec {
              command = ["pg_isready", "-U", "meesell", "-d", "meesell"]
            }
            initial_delay_seconds = 10
            period_seconds        = 5
          }

          liveness_probe {
            exec {
              command = ["pg_isready", "-U", "meesell", "-d", "meesell"]
            }
            initial_delay_seconds = 30
            period_seconds        = 15
          }

          volume_mount {
            name       = "data"
            mount_path = "/var/lib/postgresql/data"
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
