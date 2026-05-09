"""Run dispatch — sends a queued run to the worker pool.

In Phase 2 the canonical path is `Celery.send_task`. For tests and dev
environments without Redis, callers can pass a `BackgroundTasks` instance
which falls back to in-process execution. The fallback shares the exact
codepath as the worker (`tasks._run_agent_async`) so behavior is identical.
"""
from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Protocol

from xenia.celery_app import celery_app

if TYPE_CHECKING:
    from fastapi import BackgroundTasks

logger = logging.getLogger(__name__)


class RunDispatcher(Protocol):
    def dispatch(self, run_id: uuid.UUID) -> None: ...


class CeleryDispatcher:
    """Production path — enqueue on the Celery 'xenia' queue."""

    def dispatch(self, run_id: uuid.UUID) -> None:
        celery_app.send_task("xenia.run_agent", args=[str(run_id)], queue="xenia")
        logger.info("dispatched run %s to celery", run_id)


class InProcessDispatcher:
    """Dev/test path — runs the same async coroutine in-process."""

    def __init__(self, background_tasks: BackgroundTasks) -> None:
        self._bg = background_tasks

    def dispatch(self, run_id: uuid.UUID) -> None:
        from xenia.executor.tasks import _run_agent_async

        async def _runner() -> None:
            await _run_agent_async(run_id)

        self._bg.add_task(_runner)


def get_dispatcher(background_tasks: BackgroundTasks | None = None) -> RunDispatcher:
    """Pick the right dispatcher based on environment.

    Phase 2 default: when `XENIA_USE_CELERY=1`, enqueue. Otherwise stay
    in-process so the dev loop and the integration tests still work without
    a worker running.
    """
    import os

    use_celery = os.environ.get("XENIA_USE_CELERY", "0") == "1"
    if use_celery:
        return CeleryDispatcher()
    if background_tasks is None:
        # No fallback target — dispatch via Celery anyway and let it fail
        # loudly if Redis isn't reachable.
        return CeleryDispatcher()
    return InProcessDispatcher(background_tasks)
