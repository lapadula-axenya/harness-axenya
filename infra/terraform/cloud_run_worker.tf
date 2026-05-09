resource "google_cloud_run_v2_service" "worker" {
  name     = "${local.service_prefix}-worker"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  labels   = local.labels

  template {
    service_account = google_service_account.worker.email

    scaling {
      min_instance_count = var.min_worker_instances
      max_instance_count = var.max_worker_instances
    }

    containers {
      image   = var.worker_image
      command = ["celery"]
      args    = ["-A", "xenia.celery_app", "worker", "--queues=xenia", "--concurrency=4", "--loglevel=info"]

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
        cpu_idle = false
      }

      env {
        name  = "ENV"
        value = var.environment
      }
      env {
        name  = "SERVICE_NAME"
        value = "xenia-worker"
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
        name = "ANTHROPIC_API_KEY"
        value_source {
          secret_key_ref {
            secret  = var.anthropic_api_key_secret_id
            version = "latest"
          }
        }
      }
      env {
        name  = "XENIA_USE_CELERY"
        value = "1"
      }
    }

    timeout = "3600s" # workers run long agent tasks
  }
}

output "worker_revision" {
  value = google_cloud_run_v2_service.worker.template[0].revision
}
