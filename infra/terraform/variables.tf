variable "gcp_project_id" {
  description = "GCP project hosting the harness — Q2 owner: Estevão"
  type        = string
}

variable "region" {
  description = "GCP region (e.g. us-central1)"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "dev | staging | prod"
  type        = string
  default     = "prod"
}

variable "api_image" {
  description = "Artifact Registry image for xenia-api. Defaults to the public Cloud Run hello image so Terraform can bootstrap the service before any xenia image is pushed; the GitHub Actions deploy workflow flips it to the real image after the first successful build."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "worker_image" {
  description = "Artifact Registry image for xenia-worker. Same bootstrap pattern as api_image."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "cloudsql_tier" {
  description = "Cloud SQL machine tier (spec recommends db-custom-2-7680)"
  type        = string
  default     = "db-custom-2-7680"
}

variable "redis_memory_gb" {
  description = "Memorystore Redis size in GB"
  type        = number
  default     = 1
}

variable "min_api_instances" {
  type    = number
  default = 1
}

variable "max_api_instances" {
  type    = number
  default = 10
}

variable "min_worker_instances" {
  type    = number
  default = 1
}

variable "max_worker_instances" {
  type    = number
  default = 20
}

variable "anthropic_api_key_secret_id" {
  description = "Secret Manager secret holding the Anthropic API key"
  type        = string
  default     = "anthropic_api_key"
}

variable "jwt_secret_id" {
  description = "Secret Manager secret for JWT HS256 key"
  type        = string
  default     = "jwt_secret"
}

variable "slack_webhook_url" {
  description = "Slack incoming webhook for #axenya-agents-alerts (kept for backwards compat; not consumed by Terraform — Slack channels need OAuth via GCP console)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "slack_channel_id" {
  description = "Existing Cloud Monitoring notification-channel id for Slack. Leave blank to use email-only alerts. Format: projects/<PROJECT>/notificationChannels/<NUM>"
  type        = string
  default     = ""
}

variable "notification_email" {
  description = "Secondary alert email"
  type        = string
}
