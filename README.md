# Xenia Harness

Cloud-native runtime for autonomous agents at Axenya. Agents are defined as
YAML, triggered by HMAC-signed webhooks (or internal API), and run through a
tool-use loop with persistent state in Postgres.

This branch implements **Phase 1 — Harness mínimo viável** as defined in
[`SPEC.md`](SPEC.md). LangGraph integration, Celery worker, real MCP skills,
and Cloud Run deployment land in subsequent phases.

## Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Webhook gateway, registry, simple executor, mock skills | ✅ this branch |
| 2 | LangGraph + Celery worker + retries | pending |
| 3 | Real MCP skills + OmniRouter | pending |
| 4 | Cloud Run + Langfuse + dashboard | pending |

## Local development

### Prerequisites
- Python 3.12 (`pyenv install 3.12` or similar)
- [`uv`](https://docs.astral.sh/uv/) for dependency management
- Docker (Postgres + Redis via `docker-compose.dev.yml`)

### One-time setup

```bash
cp .env.example .env

# 1. Bring up dependencies
docker-compose -f docker-compose.dev.yml up -d

# 2. Install Python deps (creates .venv in repo root)
uv sync --all-extras

# 3. Apply database migrations
uv run alembic upgrade head

# 4. Seed the agents table from the YAML registry
uv run python scripts/seed_dev.py
```

### Running the API

```bash
uv run uvicorn xenia.api.main:app --reload --port 8080
```

Then trigger a webhook locally:

```bash
uv run python scripts/trigger_webhook.py exemplo_eco '{"foo": "bar"}'
```

### Running tests

```bash
uv run pytest tests/unit -v               # no DB required
uv run pytest tests/integration -v        # needs Postgres + migrations applied
uv run pytest tests/ -v                   # everything
uv run ruff check .
uv run mypy src/
```

## Adding a new agent

1. Drop a new YAML file under `agents/`. See [`agents/README.md`](agents/README.md).
2. Define the env var that holds the HMAC secret (see `.env.example`).
3. Reload: `POST /v1/agents/reload` (engineer JWT) or restart the API.

## Webhook signature

Callers sign webhooks with HMAC-SHA256 over `{timestamp}.{body}`:

```python
signed = f"{timestamp}.".encode() + body
signature = hmac.new(secret, signed, hashlib.sha256).hexdigest()
```

Headers:
- `X-Xenia-Signature: <hex>`
- `X-Xenia-Timestamp: <unix epoch>`

The server rejects requests with timestamp skew > 5 minutes.

## Layout

See [`SPEC.md` § Repository Structure](SPEC.md) — files in this branch follow
that structure exactly. Modules referenced by the spec but not yet implemented
in Phase 1 (LangGraph builder, Celery tasks, MCP skill, Langfuse) ship as
typed stubs so that the import graph and file paths stay stable across phases.
