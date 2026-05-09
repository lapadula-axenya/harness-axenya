# Xenia Harness — Runbook

Operator playbook for the four most likely incidents in production. Each
section: trigger, diagnosis, mitigation, postmortem owner.

> **On-call**: TBD — Q6 (Mariano + Sophia). Until that's settled, assume
> Sophia primary, Estevão secondary, business hours BR.

---

## 1. Queue cheia (queue_depth > 1000 por 5min)

**Trigger**: alert `Xenia: queue depth > 1000 (5m)` (P2, `#axenia-agents-alerts`).

**Diagnosis**

```bash
# Redis depth
gcloud redis instances describe xenia-redis-prod --region=us-central1 --format='value(memorySizeGb)'
gcloud redis instances describe xenia-redis-prod --region=us-central1 \
  --format='value(persistenceConfig)'

# Worker count + recent errors
gcloud run services describe xenia-worker --region=us-central1 --format=yaml | grep -E 'minScale|maxScale'
gcloud run services logs read xenia-worker --region=us-central1 --limit=200
```

Common causes:
- LLM provider throttled (Anthropic 429). Look for `LLM_RATE_LIMIT` in run errors.
- Worker pool stuck on a slow agent (timeout misconfigured > 5m).
- A skill MCP server is down — workers spin retrying.

**Mitigation**

1. Scale workers up immediately:
   ```bash
   gcloud run services update xenia-worker --region=us-central1 --max-instances=40
   ```
2. If a single agent is the offender, pause it:
   ```bash
   curl -X PATCH https://xenia-api-PROD.a.run.app/v1/agents/<id> \
     -H "Authorization: Bearer $JWT" \
     -d '{"enabled": false}'
   ```
3. If LLM-throttled, drop traffic to the affected agent and wait out the rate window.

**Postmortem owner**: Sophia.

---

## 2. MCP server down (HubSpot/Slack/Jira)

**Trigger**: `MCP_UNAVAILABLE` count rises in Langfuse traces; runs flip to `failed` with that error_code.

**Diagnosis**

```bash
# Check the MCP server URL is reachable from a Cloud Run shell
gcloud run services proxy xenia-api --region=us-central1 &
curl -i $HUBSPOT_MCP_URL  # expect 200 from /health
```

If the MCP server is genuinely down:

**Mitigation**

1. **Don't disable the agent** — Phase 2 retry kicks in; the run will
   recover when the MCP server returns.
2. If the outage is long (>15min), suppress the agent to avoid retry storms:
   ```bash
   curl -X PATCH .../v1/agents/<id> -d '{"enabled": false}'
   ```
3. Comms: post in `#axenya-agents-alerts` with ETA.
4. When MCP server recovers, re-enable the agent. Pending failed runs stay in
   the DB for ad-hoc retry: `POST /v1/runs/{id}/retry`.

**Postmortem owner**: skill owner (HubSpot integration → Sophia).

---

## 3. Custo explodiu (cost_usd_today > $100 em qualquer agente)

**Trigger**: alert `Xenia: cost > $100/day for any agent` (P3, Slack + Sophia email).

**Diagnosis**

```bash
# Top-spending agents in the last 24h
psql $DATABASE_URL -c "
  SELECT agent_id, SUM(cost_usd) AS spent, COUNT(*) AS runs
  FROM runs WHERE created_at > NOW() - INTERVAL '24 hours'
  GROUP BY agent_id ORDER BY spent DESC LIMIT 10;
"

# Recent expensive runs
psql $DATABASE_URL -c "
  SELECT id, agent_id, tokens_input, tokens_output, cost_usd, error
  FROM runs WHERE cost_usd > 1.0
  ORDER BY cost_usd DESC LIMIT 20;
"
```

Common causes:
- Tool-call loop without convergence (agent keeps re-querying BigQuery /
  Anthropic). Check `steps_executed` ≈ `max_steps`.
- New agent deployed with `max_tokens` too high.
- Webhook caller spamming the same payload.

**Mitigation**

1. Disable the offending agent.
2. Rotate the webhook secret if you suspect external abuse:
   ```bash
   gcloud secrets versions add webhook_secret_<id> --data-file=- <<< "$(openssl rand -hex 32)"
   ```
3. Open a PR adjusting the agent YAML (`max_steps`, `max_tokens`,
   `temperature` down).

**Postmortem owner**: agent owner (in YAML metadata).

---

## 4. Checkpoint corrupto

**Trigger**: critical alert (P2 manual escalate); typically surfaces as runs
that immediately fail with `KeyError` or `pydantic.ValidationError` in the
LangGraph deserialiser.

**Diagnosis**

```bash
# Identify affected run
psql $DATABASE_URL -c "
  SELECT id, agent_id, error, error_class FROM runs
  WHERE error_class IN ('KeyError', 'ValidationError') ORDER BY created_at DESC LIMIT 20;
"

# Inspect the LangGraph checkpoint table
psql $DATABASE_URL -c "
  SELECT thread_id, checkpoint_ns, checkpoint_id
  FROM checkpoints WHERE thread_id = '<run_id>';
"
```

**Mitigation**

1. **Don't auto-retry** — corrupt state will keep failing. Mark the run
   `failed` definitively:
   ```bash
   psql $DATABASE_URL -c "UPDATE runs SET status = 'failed' WHERE id = '<run_id>';"
   ```
2. Drop the corrupt checkpoint so a manual `POST /retry` can start from
   scratch:
   ```bash
   psql $DATABASE_URL -c "DELETE FROM checkpoints WHERE thread_id = '<run_id>';"
   ```
3. Trigger a new run via `POST /v1/runs/{run_id}/retry` (creates child run,
   fresh state).
4. If multiple runs are affected, capture a sample checkpoint payload before
   deleting and file a bug — this is almost always a graph schema change
   shipped without a migration.

**Postmortem owner**: Estevão (owns LangGraph integration).

---

## Useful one-liners

```bash
# Tail API + worker logs in one stream
gcloud run services logs tail xenia-api xenia-worker --region=us-central1

# Recent failed runs
psql $DATABASE_URL -c "
  SELECT id, agent_id, error_code, created_at FROM runs
  WHERE status='failed' ORDER BY created_at DESC LIMIT 50;
"

# Force a redeploy without code change (e.g. to pick up new secrets)
gcloud run services update xenia-api --region=us-central1 --update-env-vars=BUMP=$(date +%s)

# Roll back to previous revision
PREV=$(gcloud run revisions list --service=xenia-api --region=us-central1 --format='value(name)' --limit=2 | tail -1)
gcloud run services update-traffic xenia-api --region=us-central1 --to-revisions=$PREV=100
```

## Escalation path

| Severity | First | Second | When |
|---|---|---|---|
| P1 (data loss / outage > 30min) | Sophia | Estevão → Mariano | within 15min |
| P2 (degradation) | Sophia | Estevão | next business hour |
| P3 (cost / advisories) | Sophia | — | next business day |
