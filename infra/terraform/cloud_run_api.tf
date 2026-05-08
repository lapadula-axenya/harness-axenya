resource "google_cloud_run_v2_service" "api" {
  name     = "${local.service_prefix}-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"
  labels   = local.labels

  template {
    service_account = google_service_account.api.email

    scaling {
      min_instance_count = var.min_api_instances
      max_instance_count = var.max_api_instances
    }

    containers {
      image = var.api_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "1Gi"
        }
        cpu_idle = true
      }

      env {
        name  = "ENV"
        value = var.environment
      }
      env {
        name  = "SERVICE_NAME"
        value = "xenia-api"
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.gcp_project_id
      }
      env {
        name  = "REDIS_URL"
        value = "redis://${google_redis_instance.xenia.host}:${google_redis_instance.xenia.port}/0"
      }
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = "cloudsql_password"
            version = "latest"
          }
        }
      }
      env {
        name = "ANTHROPIC_API_KEY"
        value_source {
          secret_key_ref {
            secret  = var.anthropic_api_key_secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "JWT_SECRET"
        value_source {
          secret_key_ref {
            secret  = var.jwt_secret_id
            version = "latest"
          }
        }
      }
      env {
        name  = "XENIA_USE_CELERY"
        value = "1"
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 5
        period_seconds        = 5
        timeout_seconds       = 3
        failure_threshold     = 5
      }

      liveness_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        period_seconds  = 30
        timeout_seconds = 3
      }
    }

    vpc_access {
      egress = "PRIVATE_RANGES_ONLY"
    }

    timeout = "60s"
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

resource "google_cloud_run_v2_service_iam_member" "api_invoker" {
  name     = google_cloud_run_v2_service.api.name
  location = google_cloud_run_v2_service.api.location
  role     = "roles/run.invoker"
  # Public for webhook intake; webhooks are HMAC-protected at the application layer.
  member = "allUsers"
}

output "api_url" {
  value = google_cloud_run_v2_service.api.uri
}
