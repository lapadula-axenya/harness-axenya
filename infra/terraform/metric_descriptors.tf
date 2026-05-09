# Pre-create custom metric descriptors so alert policies can reference them
# before the first run emits any data point. Without this, `terraform apply`
# fails on a chicken-and-egg: alerts can't bind to a metric type GCP has
# never seen, but the metric type only materialises when the app writes its
# first sample.

resource "google_monitoring_metric_descriptor" "runs_created" {
  description  = "Number of agent runs created"
  display_name = "Xenia runs created"
  type         = "custom.googleapis.com/xenia/runs/created"
  metric_kind  = "GAUGE"
  value_type   = "INT64"
  unit         = "1"
}

resource "google_monitoring_metric_descriptor" "queue_depth" {
  description  = "Celery queue depth"
  display_name = "Xenia queue depth"
  type         = "custom.googleapis.com/xenia/queue/depth"
  metric_kind  = "GAUGE"
  value_type   = "INT64"
  unit         = "1"
}

resource "google_monitoring_metric_descriptor" "webhook_auth_failures" {
  description  = "Webhook HMAC auth failures"
  display_name = "Xenia webhook auth failures"
  type         = "custom.googleapis.com/xenia/webhook/auth_failures"
  metric_kind  = "GAUGE"
  value_type   = "INT64"
  unit         = "1"
}

resource "google_monitoring_metric_descriptor" "runs_cost_usd" {
  description  = "Cost in USD per run"
  display_name = "Xenia run cost (USD)"
  type         = "custom.googleapis.com/xenia/runs/cost_usd"
  metric_kind  = "GAUGE"
  value_type   = "DOUBLE"
  unit         = "USD"
}

resource "google_monitoring_metric_descriptor" "runs_tokens" {
  description  = "Tokens consumed per run"
  display_name = "Xenia tokens"
  type         = "custom.googleapis.com/xenia/runs/tokens"
  metric_kind  = "GAUGE"
  value_type   = "INT64"
  unit         = "1"
}

resource "google_monitoring_metric_descriptor" "skills_calls" {
  description  = "Number of skill (tool) invocations"
  display_name = "Xenia skill calls"
  type         = "custom.googleapis.com/xenia/skills/calls"
  metric_kind  = "GAUGE"
  value_type   = "INT64"
  unit         = "1"
}
