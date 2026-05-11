"""Processes (scheduled crons) — list, create, pause/resume, run-now."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from xenia.api.deps import get_db
from xenia.processes.repository import ProcessRepository
from xenia.processes.scheduler import (
    InvalidCronError,
    cron_describe,
    cron_next,
    cron_validate,
)
from xenia.storage.models import (
    Process,
    ProcessLastStatus,
    ProcessStatus,
    ProcessTargetKind,
)

router = APIRouter(prefix="/processes", tags=["processes"])


class ProcessResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    cron_expression: str
    schedule_human: str
    target_kind: ProcessTargetKind
    target_ref: str
    target_label: str
    owner_name: str
    owner_initials: str
    status: ProcessStatus
    last_run_at: datetime | None
    last_run_status: ProcessLastStatus | None
    last_run_id: uuid.UUID | None
    next_run_at: datetime | None
    success_rate_30d: float
    runs_30d: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, p: Process) -> ProcessResponse:
        return cls(
            id=p.id,
            name=p.name,
            description=p.description,
            cron_expression=p.cron_expression,
            schedule_human=p.schedule_human,
            target_kind=p.target_kind,
            target_ref=p.target_ref,
            target_label=p.target_label,
            owner_name=p.owner_name,
            owner_initials=p.owner_initials,
            status=p.status,
            last_run_at=p.last_run_at,
            last_run_status=p.last_run_status,
            last_run_id=p.last_run_id,
            next_run_at=p.next_run_at,
            success_rate_30d=float(p.success_rate_30d),
            runs_30d=p.runs_30d,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )


class ProcessCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    cron_expression: str = Field(..., min_length=1)
    schedule_human: str | None = None
    target_kind: ProcessTargetKind
    target_ref: str = Field(..., min_length=1)
    target_label: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)
    owner_name: str = Field(..., min_length=1)
    owner_initials: str | None = None


class ProcessStatusUpdate(BaseModel):
    action: Literal["pause", "resume"]


class ProcessSummary(BaseModel):
    active: int
    paused: int
    next_within_1h: int


@router.get("", response_model=list[ProcessResponse])
async def list_processes(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ProcessResponse]:
    repo = ProcessRepository(db)
    items = await repo.list_all()
    return [ProcessResponse.from_model(p) for p in items]


@router.get("/summary", response_model=ProcessSummary)
async def summary(db: Annotated[AsyncSession, Depends(get_db)]) -> ProcessSummary:
    repo = ProcessRepository(db)
    items = await repo.list_all()
    active = sum(1 for p in items if p.status == ProcessStatus.active)
    paused = sum(1 for p in items if p.status == ProcessStatus.paused)
    now = datetime.now(UTC)
    cutoff = now + timedelta(hours=1)
    next_within = sum(
        1
        for p in items
        if p.status == ProcessStatus.active
        and p.next_run_at is not None
        and p.next_run_at <= cutoff
    )
    return ProcessSummary(active=active, paused=paused, next_within_1h=next_within)


@router.post("", response_model=ProcessResponse, status_code=status.HTTP_201_CREATED)
async def create_process(
    body: ProcessCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProcessResponse:
    try:
        cron_validate(body.cron_expression)
    except InvalidCronError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    repo = ProcessRepository(db)
    schedule_human = body.schedule_human or cron_describe(body.cron_expression)
    initials = body.owner_initials or _initials_from_name(body.owner_name)
    target_label = body.target_label or body.target_ref
    p = await repo.create(
        name=body.name,
        description=body.description,
        cron_expression=body.cron_expression,
        schedule_human=schedule_human,
        target_kind=body.target_kind,
        target_ref=body.target_ref,
        target_label=target_label,
        payload=body.payload,
        owner_name=body.owner_name,
        owner_initials=initials,
    )
    return ProcessResponse.from_model(p)


@router.patch("/{process_id}/status", response_model=ProcessResponse)
async def update_status(
    process_id: uuid.UUID,
    body: ProcessStatusUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProcessResponse:
    repo = ProcessRepository(db)
    target = (
        ProcessStatus.paused if body.action == "pause" else ProcessStatus.active
    )
    p = await repo.set_status(process_id, target)
    if p is None:
        raise HTTPException(status_code=404, detail="process not found")
    return ProcessResponse.from_model(p)


@router.post("/{process_id}/run", response_model=ProcessResponse)
async def run_now(
    process_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProcessResponse:
    """Force a process run immediately.

    For Phase 1 of the Processes block this just records a synthetic OK run so
    the UI feedback loop closes; real dispatch is wired in
    ``scripts/processes_tick.py`` and the upcoming Celery beat integration.
    """
    repo = ProcessRepository(db)
    p = await repo.get(process_id)
    if p is None:
        raise HTTPException(status_code=404, detail="process not found")
    now = datetime.now(UTC)
    updated = await repo.record_run(
        process_id,
        last_run_id=None,
        last_run_status=ProcessLastStatus.ok,
        ran_at=now,
        runs_30d_delta=1,
        success_rate_30d=p.success_rate_30d if p.runs_30d else Decimal("100"),
    )
    assert updated is not None
    return ProcessResponse.from_model(updated)


def _initials_from_name(name: str) -> str:
    parts = [p for p in name.split() if p]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


__all__ = ["router", "cron_next"]
