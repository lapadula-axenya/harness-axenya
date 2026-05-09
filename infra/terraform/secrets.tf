# Secret Manager — declarations only. The actual secret values are set
# out-of-band (`gcloud secrets versions add ...`) so they never land in
# Terraform state.

locals {
  managed_secrets = [
    var.anthropic_api_key_secret_id,
    var.jwt_secret_id,
    "hubspot_mcp_token",
    "slack_mcp_token",
    "jira_mcp_token",
    "ksenia_api_token",
    "langfuse_secret_key",
    "langfuse_public_key",
    # Webhook secrets are per-agent: WEBHOOK_SECRET_<AGENT_ID>
    # Generate via: gcloud secrets create webhook_secret_triagem_lead ...
  ]
}

resource "google_secret_manager_secret" "managed" {
  for_each  = toset(local.managed_secrets)
  secret_id = each.value
  replication {
    auto {}
  }
}

# Bind runtime SAs to read these secrets.
resource "google_secret_manager_secret_iam_member" "api_access" {
  for_each = google_secret_manager_secret.managed
  secret_id = each.value.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api.email}"
}

resource "google_secret_manager_secret_iam_member" "worker_access" {
  for_each = google_secret_manager_secret.managed
  secret_id = each.value.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.worker.email}"
}
