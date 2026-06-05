# Purpose: Deploy Supabase Studio as a Deployment + ClusterIP Service (admin UI only).
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §9 (module boundaries), §11 (Pass 2).
# Playbook reference: docs/INFRASTRUCTURE_PLAYBOOK.md §7 (Supabase Studio Deployment).
# Choices:
#   - Deployment (not StatefulSet) — Studio is stateless; it reads from PostgreSQL.
#   - STUDIO_PG_META_URL points to postgres-meta sidecar URL (playbook §7 env pattern).
#   - POSTGRES_PASSWORD is sourced from the postgres-credentials Secret (not duplicated).
#   - ClusterIP service (not headless) — Studio is accessed via port-forward or ingress (Day 2).
#   - Auth/Realtime/Storage subsystems NOT enabled — per CLAUDE.md decision #15 (trimmed Supabase).

resource "kubernetes_deployment" "supabase_studio" {
  metadata {
    name      = "supabase-studio"
    namespace = var.namespace
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = "supabase-studio"
      }
    }

    template {
      metadata {
        labels = {
          app = "supabase-studio"
        }
      }

      spec {
        container {
          name  = "studio"
          image = "supabase/studio:${var.image_tag}"

          port {
            container_port = 3000
          }

          env {
            name  = "STUDIO_PG_META_URL"
            value = "http://postgres.${var.namespace}.svc.cluster.local:8080"
          }

          env {
            name = "POSTGRES_PASSWORD"
            value_from {
              secret_key_ref {
                name = var.postgres_secret_name
                key  = "password"
              }
            }
          }

          env {
            name  = "DEFAULT_ORGANIZATION_NAME"
            value = "MeeSell"
          }

          env {
            name  = "DEFAULT_PROJECT_NAME"
            value = "meesell-dev"
          }

          env {
            name  = "SUPABASE_URL"
            value = "http://localhost:3000"
          }

          env {
            name  = "SUPABASE_PUBLIC_URL"
            value = "http://localhost:3000"
          }

          resources {
            requests = {
              cpu    = "100m"
              memory = "256Mi"
            }
            limits = {
              cpu    = "500m"
              memory = "512Mi"
            }
          }

          readiness_probe {
            http_get {
              path = "/"
              port = 3000
            }
            initial_delay_seconds = 15
            period_seconds        = 10
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "supabase_studio" {
  metadata {
    name      = "supabase-studio"
    namespace = var.namespace
  }

  spec {
    selector = {
      app = "supabase-studio"
    }

    port {
      name        = "http"
      port        = 3000
      target_port = 3000
    }

    type = "ClusterIP"
  }
}
