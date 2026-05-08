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
  description = "Artifact Registry image for xenia-api (set by Cloud Build / GH Actions)"
  type        = string
}

variable "worker_image" {
  description = "Artifact Registry image for xenia-worker"
  type        = string
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
  description = "Slack incoming webhook for #axenya-agents-alerts"
  type        = string
  sensitive   = true
}

variable "notification_email" {
  description = "Secondary alert email"
  type        = string
}
