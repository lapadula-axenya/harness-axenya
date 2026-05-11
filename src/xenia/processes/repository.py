"""Process repository — list/upsert/state transitions."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xenia.processes.scheduler import cron_next
from xenia.storage.models import (
    Process,
    ProcessLastStatus,
    ProcessStatus,
    ProcessTargetKind,
)


class ProcessRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self, *, include_archived: bool = False) -> list[Process]:
        stmt = select(Process).order_by(Process.created_at.asc())
        if not include_archived:
            stmt = stmt.where(Process.status != ProcessStatus.archived)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get(self, process_id: uuid.UUID) -> Process | None:
        return await self.session.get(Process, process_id)

    async def create(
        self,
        *,
        name: str,
        description: str,
        cron_expression: str,
        schedule_human: str,
        target_kind: ProcessTargetKind,
        target_ref: str,
        target_label: str,
        payload: dict[str, Any],
        owner_name: str,
        owner_initials: str,
        status: ProcessStatus = ProcessStatus.active,
    ) -> Process:
        now = datetime.now(UTC)
        next_at = cron_next(cron_expression, after=now) if status == ProcessStatus.active else None
        p = Process(
            name=name,
            description=description,
            cron_expression=cron_expression,
            schedule_human=schedule_human,
            target_kind=target_kind,
            target_ref=target_ref,
            target_label=target_label,
            payload=payload,
            owner_name=owner_name,
            owner_initials=owner_initials,
            status=status,
            next_run_at=next_at,
        )
        self.session.add(p)
        await self.session.flush()
        return p

    async def set_status(
        self, process_id: uuid.UUID, status: ProcessStatus
    ) -> Process | None:
        p = await self.get(process_id)
        if p is None:
            return None
        p.status = status
        now = datetime.now(UTC)
        if status == ProcessStatus.active:
            p.next_run_at = cron_next(p.cron_expression, after=now)
        else:
            p.next_run_at = None
        return p

    async def record_run(
        self,
        process_id: uuid.UUID,
        *,
        last_run_id: uuid.UUID | None,
        last_run_status: ProcessLastStatus,
        ran_at: datetime,
        runs_30d_delta: int = 1,
        success_rate_30d: Decimal | None = None,
    ) -> Process | None:
        p = await self.get(process_id)
        if p is None:
            return None
        p.last_run_at = ran_at
        p.last_run_id = last_run_id
        p.last_run_status = last_run_status
        p.runs_30d = p.runs_30d + runs_30d_delta
        if success_rate_30d is not None:
            p.success_rate_30d = success_rate_30d
        if p.status == ProcessStatus.active:
            p.next_run_at = cron_next(p.cron_expression, after=ran_at)
        return p

    async def due(self, *, now: datetime, limit: int = 50) -> list[Process]:
        stmt = (
            select(Process)
            .where(
                Process.status == ProcessStatus.active,
                Process.next_run_at.is_not(None),
                Process.next_run_at <= now,
            )
            .order_by(Process.next_run_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
