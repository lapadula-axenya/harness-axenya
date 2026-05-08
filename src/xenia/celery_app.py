"""Celery application — Phase 2 worker entrypoint."""
from __future__ import annotations

from celery import Celery

from xenia.config import get_settings

_settings = get_settings()

celery_app = Celery(
    "xenia",
    broker=_settings.redis_url,
    backend=_settings.redis_url,
    include=["xenia.executor.tasks"],
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_default_queue="xenia",
    task_track_started=True,
    result_expires=86400,
)
