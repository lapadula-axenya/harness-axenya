resource "google_sql_database_instance" "xenia" {
  name             = "${local.service_prefix}-pg-${var.environment}"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier              = var.cloudsql_tier
    availability_type = var.environment == "prod" ? "REGIONAL" : "ZONAL"
    disk_size         = 50
    disk_autoresize   = true

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
      start_time                     = "03:00"
    }

    database_flags {
      name  = "max_connections"
      value = "200"
    }

    user_labels = local.labels
  }

  deletion_protection = var.environment == "prod"
}

resource "google_sql_database" "xenia" {
  name     = "xenia"
  instance = google_sql_database_instance.xenia.name
}

resource "google_sql_user" "xenia" {
  name     = "xenia"
  instance = google_sql_database_instance.xenia.name
  password = random_password.cloudsql.result
}

resource "random_password" "cloudsql" {
  length  = 32
  special = true
}

resource "google_secret_manager_secret" "cloudsql_password" {
  secret_id = "cloudsql_password"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "cloudsql_password" {
  secret      = google_secret_manager_secret.cloudsql_password.id
  secret_data = random_password.cloudsql.result
}
