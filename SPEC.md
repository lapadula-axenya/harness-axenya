# Technical Spec: Xenia Harness

**Status:** Draft
**Author:** Sophia Lapadula
**Reviewers:** Mariano (CEO), Estevão (Head of Eng), Rafa (Manager)
**Last Updated:** 2026-05-08
**Repo:** `axenya/xenia-harness`

---

## Overview

**Problema:** A Axenya quer adotar a tese de "service-as-software" — substituir
trabalho manual repetitivo por agentes autônomos com outcomes mensuráveis. Hoje
não existe infraestrutura interna pra rodar agentes long-running, com estado,
ativáveis por sistemas externos (HubSpot, Slack, Make, Ksenia). Cada nova
automação vira um projeto custom de DevOps.

**Solução:** Construir o Xenia Harness — uma plataforma cloud-native que executa
agentes definidos por configuração (YAML), ativáveis por webhook, com estado
durável e observabilidade. Agentes usam LangGraph pra orquestração e MCP pra
integrações.

The full spec lives in the original markdown shared by Sophia. This file is a
short stub that callers/operators can read for an at-a-glance overview; for
implementation details and acceptance criteria refer to the four-phase rollout
in the original document.

## Phased Rollout (summary)

- **Fase 1 — Harness mínimo viável:** webhooks com HMAC, registry YAML,
  executor de tool-use simples, mocks de skills, CRUD de runs em Postgres.
  ✅ implementada nessa branch (`claude/xenia-harness-spec-70U9J`).
- **Fase 2 — LangGraph + Celery:** orquestração com checkpoints, worker
  separado, retry/cancel/retry endpoints.
- **Fase 3 — Skills MCP + integrações reais:** clients MCP (HubSpot, Slack,
  Atlassian), BigQuery whitelisted, Ksenia HTTP.
- **Fase 4 — Produção:** Cloud Run + Cloud SQL + Memorystore via Terraform,
  Langfuse traces, dashboard interno, alertas.

## Phase 1 acceptance (this branch)

```bash
docker-compose -f docker-compose.dev.yml up -d
uv sync --all-extras
uv run alembic upgrade head
uv run pytest tests/unit tests/integration -v
uv run python scripts/trigger_webhook.py exemplo_eco '{"foo": "bar"}'
```

Expected: unit + integration tests green, webhook returns 202 with `run_id`,
polling `/v1/runs/{run_id}` shows `status=done` with the mocked LLM output.

## Decisions made for Phase 1

- **Package manager:** uv (locked-in across phases).
- **OmniRouter client:** Anthropic-compatible shim (`xenia.llm.omnirouter_client`)
  pointing at a configurable `base_url`. Real divergence handled in Phase 3 if
  needed.
- **Custom LangGraph `graph:`:** committed as v1 priority — schema is in place
  in Phase 1; the builder lands in Phase 2.

Open questions (Q2, Q4–Q7) remain to be answered before the relevant phases.
