"""Celery tasks — Phase 2 stub.

Phase 1 dispatches `run_agent` via FastAPI BackgroundTasks; the same callsite
will swap in `enqueue_run.delay()` in Phase 2.
"""
from __future__ import annotations

import uuid

from xenia.celery_app import celery_app


@celery_app.task(name="xenia.run_agent")  # type: ignore[untyped-decorator]
def run_agent_task(run_id: str) -> str:
    raise NotImplementedError(
        f"Celery task pipeline lands in Phase 2. (run_id={uuid.UUID(run_id)})"
    )
