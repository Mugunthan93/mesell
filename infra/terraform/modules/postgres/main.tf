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

          # MS-0 / D5 step 1 (MS-DB-3): raise max_connections 100 -> 200 to give the
          # connection-pool headroom the microservices migration (infra plan §3.3)
          # requires. The postgres entrypoint forwards extra args to the `postgres`
          # binary, so `-c max_connections=200` overrides the compiled default at boot.
          # Memory cost ~= 5MB/conn * 100 extra conns ~= +500MB worst case -> the
          # memory LIMIT is raised 1Gi -> 1.5Gi below (request stays 500Mi: idle
          # connection slots cost little until used, so scheduler pressure is unchanged
          # and CPU — the binding constraint on the e2-standard-2 node — is untouched).
          args = ["-c", "max_connections=${var.max_connections}"]

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
              # MS-0 / D5 step 1: memory limit raised 1Gi -> 1.5Gi to cover the
              # ~+500MB worst-case from max_connections=200 (~5MB/conn * 100 extra).
              # Node has ~4.6Gi free RAM (44% requested of 8GB), so this is well
              # within budget. CPU limit unchanged.
              cpu    = "1000m"
              memory = "1536Mi"
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
