"""Internal dashboard endpoints."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from xenia.api.deps import get_db, require_scope
from xenia.api.schemas import DashboardAgent, DashboardSummary
from xenia.storage.models import Run, RunStatus

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummary,
    dependencies=[Depends(require_scope("dashboard:read"))],
)
async def summary(db: Annotated[AsyncSession, Depends(get_db)]) -> DashboardSummary:
    now = datetime.now(UTC)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    last_24h = now - timedelta(hours=24)

    runs_today = (
        await db.execute(select(func.count()).where(Run.created_at >= today))
    ).scalar_one() or 0
    runs_running = (
        await db.execute(
            select(func.count()).where(Run.status == RunStatus.running)
        )
    ).scalar_one() or 0
    runs_failed_24h = (
        await db.execute(
            select(func.count())
            .where(Run.status == RunStatus.failed)
            .where(Run.created_at >= last_24h)
        )
    ).scalar_one() or 0
    runs_total_24h = (
        await db.execute(
            select(func.count()).where(Run.created_at >= last_24h)
        )
    ).scalar_one() or 0
    cost_today = (
        await db.execute(
            select(func.coalesce(func.sum(Run.cost_usd), 0)).where(
                Run.created_at >= today
            )
        )
    ).scalar_one()

    failure_rate = (
        runs_failed_24h / runs_total_24h if runs_total_24h else 0.0
    )

    return DashboardSummary(
        runs_today=int(runs_today),
        runs_running=int(runs_running),
        runs_failed_24h=int(runs_failed_24h),
        cost_usd_today=Decimal(str(cost_today or 0)),
        failure_rate_24h=round(failure_rate, 4),
    )


@router.get(
    "/agents",
    response_model=list[DashboardAgent],
    dependencies=[Depends(require_scope("dashboard:read"))],
)
async def per_agent(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DashboardAgent]:
    last_24h = datetime.now(UTC) - timedelta(hours=24)
    stmt = (
        select(
            Run.agent_id,
            func.count(),
            func.coalesce(func.sum(Run.cost_usd), 0),
        )
        .where(Run.created_at >= last_24h)
        .group_by(Run.agent_id)
    )
    rows = (await db.execute(stmt)).all()
    return [
        DashboardAgent(
            agent_id=str(r[0]),
            runs_24h=int(r[1]),
            cost_usd_24h=Decimal(str(r[2])),
            last_status=None,
        )
        for r in rows
    ]
