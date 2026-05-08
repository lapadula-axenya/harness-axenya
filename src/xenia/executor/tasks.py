"""Celery tasks for the worker pool."""
from __future__ import annotations

import asyncio
import logging
import uuid

from xenia.agents.registry import get_registry
from xenia.celery_app import celery_app
from xenia.config import get_settings
from xenia.executor.executor import run_agent
from xenia.executor.retry import RETRYABLE_ERROR_CODES, backoff_seconds
from xenia.llm.omnirouter_client import get_llm_client
from xenia.skills.base import get_skill_registry
from xenia.storage.db import session_scope
from xenia.storage.repositories import RunRepository

logger = logging.getLogger(__name__)


@celery_app.task(name="xenia.run_agent", bind=True, max_retries=0)
def run_agent_task(self, run_id):  # type: ignore[no-untyped-def]
    """Run an agent end-to-end inside a Celery worker.

    The task is idempotent on `run_id` thanks to the LangGraph checkpointer:
    if the worker dies mid-step, redelivery resumes from the last checkpoint.
    """
    run_uuid = uuid.UUID(run_id)
    asyncio.run(_run_agent_async(run_uuid))
    return run_id


async def _run_agent_async(run_id: uuid.UUID) -> None:
    settings = get_settings()
    async with session_scope() as session:
        run = await RunRepository(session).get(run_id)
        if run is None:
            logger.error("run %s not found in DB; skipping task", run_id)
            return
        agent_id = run.agent_id
        payload = dict(run.input_payload)
        triggered_by = run.triggered_by
        retry_count = await _count_retries(session, run_id)

    definition = get_registry().get(agent_id)
    skill_registry = get_skill_registry()
    llm_client = get_llm_client(
        provider=definition.llm.provider,
        anthropic_api_key=settings.anthropic_api_key,
        omnirouter_api_key=settings.omnirouter_api_key,
        omnirouter_base_url=settings.omnirouter_base_url,
    )

    outcome = await run_agent(
        run_id=run_id,
        definition=definition,
        payload=payload,
        llm_client=llm_client,
        skill_registry=skill_registry,
    )

    if (
        outcome.error is not None
        and outcome.error_code in RETRYABLE_ERROR_CODES
        and triggered_by != "retry"
        and retry_count < definition.execution.retry_on_failure
    ):
        await _schedule_retry(run_id=run_id, attempt=retry_count, definition=definition)


async def _count_retries(session: object, original_run_id: uuid.UUID) -> int:
    """Count how many retry runs already point at `original_run_id`."""
    from sqlalchemy import func, select

    from xenia.storage.models import Run

    stmt = select(func.count()).where(Run.parent_run_id == original_run_id)
    result = await session.execute(stmt)  # type: ignore[attr-defined]
    return int(result.scalar_one() or 0)


async def _schedule_retry(
    *, run_id: uuid.UUID, attempt: int, definition: object
) -> None:
    """Create a child run and enqueue it after a backoff delay."""
    from xenia.agents.definition import AgentDefinition

    assert isinstance(definition, AgentDefinition)
    delay = backoff_seconds(attempt, base=definition.execution.retry_backoff_seconds)

    async with session_scope() as session:
        original = await RunRepository(session).get(run_id)
        if original is None:
            return
        new_run = await RunRepository(session).create(
            agent_id=original.agent_id,
            input_payload=dict(original.input_payload),
            triggered_by="retry",
            trigger_source=original.trigger_source,
            timeout_seconds=definition.execution.timeout_seconds,
            parent_run_id=original.id,
        )
        new_run_id = new_run.id

    run_agent_task.apply_async(args=[str(new_run_id)], countdown=delay)
    logger.info(
        "scheduled retry %s for failed run %s (delay=%ss)",
        new_run_id,
        run_id,
        delay,
    )
