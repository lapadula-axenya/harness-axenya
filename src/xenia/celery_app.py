"""Celery app — stub for Phase 1, configured fully in Phase 2."""
from __future__ import annotations

from celery import Celery

from xenia.config import get_settings

_settings = get_settings()

celery_app = Celery(
    "xenia",
    broker=_settings.redis_url,
    backend=_settings.redis_url,
    include=[],
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)
