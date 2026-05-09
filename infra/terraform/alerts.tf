# Alerts per SPEC.md § Observability.
#
# The Slack notification channel needs OAuth via GCP console (not a raw
# incoming webhook URL), so we provision it manually post-apply and feed
# its id back into Terraform via `slack_channel_id`. Default = empty,
# which means alerts route only to email until the Slack channel is wired.

resource "google_monitoring_notification_channel" "email" {
  display_name = "Xenia alerts (email)"
  type         = "email"
  labels = {
    email_address = var.notification_email
  }
}

locals {
  channels = compact([
    var.slack_channel_id,
    google_monitoring_notification_channel.email.id,
  ])
}

resource "google_monitoring_alert_policy" "failure_rate_high" {
  display_name = "Xenia: many runs created (5m)"
  combiner     = "OR"
  conditions {
    display_name = "runs created"
    condition_threshold {
      filter          = "metric.type=\"custom.googleapis.com/xenia/runs/created\" AND resource.type=\"global\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 100
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MAX"
      }
    }
  }
  notification_channels = local.channels
  user_labels           = local.labels
  depends_on            = [google_monitoring_metric_descriptor.runs_created]
}

resource "google_monitoring_alert_policy" "queue_depth" {
  display_name = "Xenia: queue depth > 1000 (5m)"
  combiner     = "OR"
  conditions {
    display_name = "queue depth"
    condition_threshold {
      filter          = "metric.type=\"custom.googleapis.com/xenia/queue/depth\" AND resource.type=\"global\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 1000
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
  notification_channels = local.channels
  depends_on = [google_monitoring_metric_descriptor.queue_depth]
}

resource "google_monitoring_alert_policy" "webhook_auth" {
  display_name = "Xenia: webhook auth failures > 100 (1m)"
  combiner     = "OR"
  conditions {
    display_name = "webhook auth failures"
    condition_threshold {
      filter          = "metric.type=\"custom.googleapis.com/xenia/webhook/auth_failures\" AND resource.type=\"global\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 100
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }
  notification_channels = local.channels
  depends_on            = [google_monitoring_metric_descriptor.webhook_auth_failures]
}

resource "google_monitoring_alert_policy" "cost_per_day" {
  display_name = "Xenia: cost > $100/day for any agent"
  combiner     = "OR"
  conditions {
    display_name = "daily cost"
    condition_threshold {
      filter          = "metric.type=\"custom.googleapis.com/xenia/runs/cost_usd\" AND resource.type=\"global\""
      duration        = "3600s"
      comparison      = "COMPARISON_GT"
      threshold_value = 100
      aggregations {
        alignment_period   = "86400s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }
  notification_channels = local.channels
  depends_on = [google_monitoring_metric_descriptor.runs_cost_usd]
}
