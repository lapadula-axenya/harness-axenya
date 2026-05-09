output "cloudsql_connection_name" {
  value = google_sql_database_instance.xenia.connection_name
}

output "redis_host" {
  value = "${google_redis_instance.xenia.host}:${google_redis_instance.xenia.port}"
}

output "artifact_registry" {
  value = "${var.region}-docker.pkg.dev/${var.gcp_project_id}/${google_artifact_registry_repository.xenia.repository_id}"
}

output "deployer_service_account" {
  value = google_service_account.deployer.email
}
