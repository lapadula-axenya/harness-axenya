resource "google_service_account" "api" {
  account_id   = "${local.service_prefix}-api"
  display_name = "Xenia API runtime"
}

resource "google_service_account" "worker" {
  account_id   = "${local.service_prefix}-worker"
  display_name = "Xenia Worker runtime"
}

resource "google_service_account" "deployer" {
  account_id   = "${local.service_prefix}-deployer"
  display_name = "Xenia Cloud Build deployer (used by GitHub Actions WIF)"
}

# Runtime IAM — what the services actually need.
locals {
  runtime_roles = [
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
    "roles/monitoring.metricWriter",
    "roles/logging.logWriter",
    "roles/redis.editor",
  ]
}

resource "google_project_iam_member" "api_runtime" {
  for_each = toset(local.runtime_roles)
  project  = var.gcp_project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.api.email}"
}

resource "google_project_iam_member" "worker_runtime" {
  for_each = toset(local.runtime_roles)
  project  = var.gcp_project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.worker.email}"
}

# Deploy IAM — what Cloud Build / GH Actions need to push images and deploy.
resource "google_project_iam_member" "deployer_run_admin" {
  project = var.gcp_project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_project_iam_member" "deployer_artifact_writer" {
  project = var.gcp_project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_project_iam_member" "deployer_sa_user" {
  project = var.gcp_project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}
