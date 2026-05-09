resource "google_artifact_registry_repository" "xenia" {
  location      = var.region
  repository_id = "${local.service_prefix}-images"
  description   = "Xenia harness Docker images"
  format        = "DOCKER"
  labels        = local.labels
}
