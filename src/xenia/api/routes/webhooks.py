"""Webhook intake — HMAC-validated entrypoints that enqueue runs."""
from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from jsonschema import Draft202012Validator, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from xenia.agents.registry import AgentNotFoundError, AgentRegistry
from xenia.api.deps import get_agent_registry, get_db, get_settings_dep
from xenia.api.schemas import RunCreatedResponse
from xenia.config import Settings
from xenia.executor.dispatch import get_dispatcher
from xenia.observability import metrics
from xenia.security.hmac_verify import verify_signature
from xenia.storage.repositories import RunRepository

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post(
    "/{agent_id}",
    response_model=RunCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def webhook(
    agent_id: str,
    request: Request,
    background: BackgroundTasks,
    settings: Annotated[Settings, Depends(get_settings_dep)],
    registry: Annotated[AgentRegistry, Depends(get_agent_registry)],
    db: Annotated[AsyncSession, Depends(get_db)],
    x_xenia_signature: Annotated[str | None, Header()] = None,
    x_xenia_timestamp: Annotated[str | None, Header()] = None,
) -> RunCreatedResponse:
    body_bytes = await request.body()

    try:
        definition = registry.get(agent_id)
    except AgentNotFoundError:
        raise HTTPException(status_code=404, detail=f"agent {agent_id!r} not found") from None

    if not definition.enabled:
        raise HTTPException(status_code=404, detail=f"agent {agent_id!r} is disabled")

    secret = os.environ.get(definition.webhook_secret_env)
    if not secret:
        raise HTTPException(
            status_code=503,
            detail=f"webhook secret env {definition.webhook_secret_env!r} not configured",
        )

    if not x_xenia_signature or not x_xenia_timestamp:
        metrics.webhook_auth_failures.inc(agent_id)
        raise HTTPException(
            status_code=401, detail="missing signature or timestamp"
        )
    if not verify_signature(
        body_bytes,
        x_xenia_signature,
        x_xenia_timestamp,
        secret,
        max_skew_seconds=settings.webhook_timestamp_skew_seconds,
    ):
        metrics.webhook_auth_failures.inc(agent_id)
        raise HTTPException(status_code=401, detail="invalid webhook signature")

    import json
    try:
        payload = json.loads(body_bytes)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"invalid JSON: {exc}") from exc

    try:
        Draft202012Validator(definition.input_schema).validate(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"payload violates input_schema at {'/'.join(str(p) for p in exc.absolute_path) or '<root>'}: {exc.message}",
        ) from exc

    run_repo = RunRepository(db)
    run = await run_repo.create(
        agent_id=agent_id,
        input_payload=payload,
        triggered_by="webhook",
        trigger_source=None,
        timeout_seconds=definition.execution.timeout_seconds,
    )
    await db.commit()
    metrics.runs_created.inc(agent_id, "webhook")

    get_dispatcher(background).dispatch(run.id)

    return RunCreatedResponse(
        run_id=run.id,
        status=run.status.value if hasattr(run.status, "value") else str(run.status),
        poll_url=f"/v1/runs/{run.id}",
        stream_url=f"/v1/runs/{run.id}/events",
    )
