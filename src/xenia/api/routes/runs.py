"""Run CRUD + cancel + retry."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from jsonschema import Draft202012Validator, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from xenia.agents.registry import AgentNotFoundError, AgentRegistry
from xenia.api.deps import (
    get_agent_registry,
    get_db,
    get_settings_dep,
    get_skills,
    require_scope,
)
from xenia.api.schemas import (
    RunCreate,
    RunCreatedResponse,
    RunEventResponse,
    RunResponse,
)
from xenia.config import Settings
from xenia.executor.executor import run_agent
from xenia.llm.omnirouter_client import get_llm_client
from xenia.observability import metrics
from xenia.skills.base import SkillRegistry
from xenia.storage.models import RunStatus
from xenia.storage.repositories import RunEventRepository, RunRepository

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post(
    "/{agent_id}",
    response_model=RunCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_scope("runs:create"))],
)
async def create_run(
    agent_id: str,
    body: RunCreate,
    background: BackgroundTasks,
    settings: Annotated[Settings, Depends(get_settings_dep)],
    registry: Annotated[AgentRegistry, Depends(get_agent_registry)],
    skills: Annotated[SkillRegistry, Depends(get_skills)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RunCreatedResponse:
    try:
        definition = registry.get(agent_id)
    except AgentNotFoundError:
        raise HTTPException(status_code=404, detail=f"agent {agent_id!r} not found") from None
    if not definition.enabled:
        raise HTTPException(status_code=404, detail=f"agent {agent_id!r} is disabled")

    try:
        Draft202012Validator(definition.input_schema).validate(body.payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"payload violates input_schema: {exc.message}",
        ) from exc

    run_repo = RunRepository(db)
    run = await run_repo.create(
        agent_id=agent_id,
        input_payload=body.payload,
        triggered_by=body.triggered_by,
        trigger_source=body.trigger_source,
        timeout_seconds=definition.execution.timeout_seconds,
    )
    await db.commit()
    metrics.runs_created.inc(agent_id, body.triggered_by)

    llm_client = get_llm_client(
        provider=definition.llm.provider,
        anthropic_api_key=settings.anthropic_api_key,
        omnirouter_api_key=settings.omnirouter_api_key,
        omnirouter_base_url=settings.omnirouter_base_url,
    )
    background.add_task(
        run_agent,
        run_id=run.id,
        definition=definition,
        payload=body.payload,
        llm_client=llm_client,
        skill_registry=skills,
    )
    return RunCreatedResponse(
        run_id=run.id,
        status=run.status.value if hasattr(run.status, "value") else str(run.status),
        poll_url=f"/v1/runs/{run.id}",
        stream_url=f"/v1/runs/{run.id}/events",
    )


@router.get(
    "/{run_id}",
    response_model=RunResponse,
    dependencies=[Depends(require_scope("runs:read"))],
)
async def get_run(
    run_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RunResponse:
    run = await RunRepository(db).get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return RunResponse.model_validate(run)


@router.get(
    "",
    response_model=list[RunResponse],
    dependencies=[Depends(require_scope("runs:read"))],
)
async def list_runs(
    db: Annotated[AsyncSession, Depends(get_db)],
    agent_id: str | None = None,
    status_: list[RunStatus] | None = Query(default=None, alias="status"),
    since: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[RunResponse]:
    runs = await RunRepository(db).list(
        agent_id=agent_id, statuses=status_, since=since, limit=limit
    )
    return [RunResponse.model_validate(r) for r in runs]


@router.get(
    "/{run_id}/events",
    response_model=list[RunEventResponse],
    dependencies=[Depends(require_scope("runs:read"))],
)
async def run_events(
    run_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[RunEventResponse]:
    run = await RunRepository(db).get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    events = await RunEventRepository(db).list_for_run(run_id)
    return [RunEventResponse.model_validate(e) for e in events]


@router.post(
    "/{run_id}/cancel",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_scope("runs:cancel"))],
)
async def cancel_run(
    run_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    repo = RunRepository(db)
    run = await repo.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    if run.status not in (RunStatus.queued, RunStatus.running, RunStatus.paused):
        raise HTTPException(
            status_code=409,
            detail=f"cannot cancel run in status {run.status}",
        )
    await repo.mark_cancelled(run)
    return None


@router.post(
    "/{run_id}/retry",
    response_model=RunCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_scope("runs:create"))],
)
async def retry_run(
    run_id: UUID,
    background: BackgroundTasks,
    settings: Annotated[Settings, Depends(get_settings_dep)],
    registry: Annotated[AgentRegistry, Depends(get_agent_registry)],
    skills: Annotated[SkillRegistry, Depends(get_skills)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RunCreatedResponse:
    repo = RunRepository(db)
    original = await repo.get(run_id)
    if original is None:
        raise HTTPException(status_code=404, detail="run not found")
    try:
        definition = registry.get(original.agent_id)
    except AgentNotFoundError:
        raise HTTPException(status_code=404, detail="agent not found") from None

    new_run = await repo.create(
        agent_id=original.agent_id,
        input_payload=original.input_payload,
        triggered_by="retry",
        trigger_source=original.trigger_source,
        timeout_seconds=definition.execution.timeout_seconds,
        parent_run_id=original.id,
    )
    await db.commit()

    llm_client = get_llm_client(
        provider=definition.llm.provider,
        anthropic_api_key=settings.anthropic_api_key,
        omnirouter_api_key=settings.omnirouter_api_key,
        omnirouter_base_url=settings.omnirouter_base_url,
    )
    background.add_task(
        run_agent,
        run_id=new_run.id,
        definition=definition,
        payload=original.input_payload,
        llm_client=llm_client,
        skill_registry=skills,
    )
    return RunCreatedResponse(
        run_id=new_run.id,
        status=new_run.status.value if hasattr(new_run.status, "value") else str(new_run.status),
        poll_url=f"/v1/runs/{new_run.id}",
        stream_url=f"/v1/runs/{new_run.id}/events",
    )
