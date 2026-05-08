"""Repositories — data access for agents, runs, events."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from xenia.storage.models import Agent, Run, RunEvent, RunStatus


class AgentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(
        self,
        *,
        agent_id: str,
        nome: str,
        descricao: str,
        yaml_hash: str,
        yaml_content: str,
    ) -> Agent:
        existing = await self.session.get(Agent, agent_id)
        if existing is None:
            agent = Agent(
                id=agent_id,
                nome=nome,
                descricao=descricao,
                yaml_hash=yaml_hash,
                yaml_content=yaml_content,
            )
            self.session.add(agent)
            return agent
        existing.nome = nome
        existing.descricao = descricao
        existing.yaml_hash = yaml_hash
        existing.yaml_content = yaml_content
        return existing

    async def get(self, agent_id: str) -> Agent | None:
        return await self.session.get(Agent, agent_id)

    async def list_all(self) -> list[Agent]:
        result = await self.session.execute(select(Agent).order_by(Agent.id))
        return list(result.scalars().all())

    async def set_enabled(self, agent_id: str, enabled: bool) -> Agent | None:
        agent = await self.session.get(Agent, agent_id)
        if agent is None:
            return None
        agent.enabled = enabled
        return agent


class RunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        agent_id: str,
        input_payload: dict[str, Any],
        triggered_by: str,
        trigger_source: str | None,
        timeout_seconds: int,
        parent_run_id: uuid.UUID | None = None,
    ) -> Run:
        now = datetime.now(UTC)
        run = Run(
            agent_id=agent_id,
            input_payload=input_payload,
            triggered_by=triggered_by,
            trigger_source=trigger_source,
            parent_run_id=parent_run_id,
            timeout_at=now + timedelta(seconds=timeout_seconds),
            status=RunStatus.queued,
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def get(self, run_id: uuid.UUID) -> Run | None:
        return await self.session.get(Run, run_id)

    async def list(
        self,
        *,
        agent_id: str | None = None,
        statuses: list[RunStatus] | None = None,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[Run]:
        stmt = select(Run).order_by(desc(Run.created_at)).limit(limit)
        if agent_id:
            stmt = stmt.where(Run.agent_id == agent_id)
        if statuses:
            stmt = stmt.where(Run.status.in_(statuses))
        if since:
            stmt = stmt.where(Run.created_at >= since)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_running(self, run: Run) -> None:
        run.status = RunStatus.running
        run.started_at = datetime.now(UTC)

    async def mark_done(
        self,
        run: Run,
        *,
        output: str | None,
        steps_executed: int,
        tokens_input: int,
        tokens_output: int,
    ) -> None:
        run.status = RunStatus.done
        run.output = output
        run.steps_executed = steps_executed
        run.tokens_input = tokens_input
        run.tokens_output = tokens_output
        run.completed_at = datetime.now(UTC)

    async def mark_failed(
        self,
        run: Run,
        *,
        error: str,
        error_class: str,
        steps_executed: int,
    ) -> None:
        run.status = RunStatus.failed
        run.error = error
        run.error_class = error_class
        run.steps_executed = steps_executed
        run.completed_at = datetime.now(UTC)

    async def mark_cancelled(self, run: Run) -> None:
        run.status = RunStatus.cancelled
        run.completed_at = datetime.now(UTC)


class RunEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append(
        self,
        *,
        run_id: uuid.UUID,
        event_type: str,
        step_number: int,
        payload: dict[str, Any],
    ) -> RunEvent:
        event = RunEvent(
            run_id=run_id,
            event_type=event_type,
            step_number=step_number,
            payload=payload,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_for_run(self, run_id: uuid.UUID) -> list[RunEvent]:
        stmt = (
            select(RunEvent)
            .where(RunEvent.run_id == run_id)
            .order_by(RunEvent.created_at, RunEvent.id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
