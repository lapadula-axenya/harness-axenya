resource "google_redis_instance" "xenia" {
  name           = "${local.service_prefix}-redis-${var.environment}"
  tier           = var.environment == "prod" ? "STANDARD_HA" : "BASIC"
  memory_size_gb = var.redis_memory_gb
  region         = var.region
  redis_version  = "REDIS_7_0"
  display_name   = "Xenia Harness queue + cache"

  labels = local.labels
}
