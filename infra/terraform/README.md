# Xenia Harness — Terraform

Provisions the GCP infrastructure described in `SPEC.md` § Phase 4:

| Resource | Module |
|---|---|
| Cloud SQL Postgres 15 | `cloudsql.tf` |
| Memorystore Redis | `redis.tf` |
| Cloud Run service `xenia-api` | `cloud_run_api.tf` |
| Cloud Run service `xenia-worker` | `cloud_run_worker.tf` |
| Artifact Registry | `artifact_registry.tf` |
| Secret Manager + IAM bindings | `secrets.tf` |
| Cloud Monitoring alerts | `alerts.tf` |
| Service accounts + IAM | `iam.tf` |

## Required values

Open `terraform.tfvars.example`, copy to `terraform.tfvars`, and fill:

| Var | Owner | Notes |
|---|---|---|
| `gcp_project_id` | Estevão (Q2) | The GCP project hosting the harness |
| `region` | Estevão | e.g. `us-central1` |
| `billing_account` | Estevão | only needed if creating a project |
| `slack_webhook_url` | Sophia | for `#axenya-agents-alerts` |
| `notification_email` | Sophia | secondary alert channel |

## Apply

```bash
cd infra/terraform
terraform init
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

Bootstrap order: Artifact Registry → Cloud SQL → Memorystore → Service
Accounts → Secret Manager → Cloud Run services → Alerts. Terraform
resolves the dependency graph; the apply is one-shot.

## Outputs

After apply Terraform prints:

* `api_url` — public Cloud Run URL of `xenia-api`
* `worker_revision` — current revision of `xenia-worker`
* `cloudsql_connection_name` — for proxy / migrations
* `redis_host` — internal Memorystore host

Wire those into the GitHub Actions secrets so the deploy workflow can
push new revisions.
