"""Unit tests for the dispatcher selection logic."""
from __future__ import annotations

import os
import uuid
from unittest.mock import MagicMock, patch

from xenia.executor.dispatch import (
    CeleryDispatcher,
    InProcessDispatcher,
    get_dispatcher,
)


def test_get_dispatcher_inprocess_when_celery_disabled():
    bg = MagicMock()
    with patch.dict(os.environ, {"XENIA_USE_CELERY": "0"}):
        dispatcher = get_dispatcher(bg)
    assert isinstance(dispatcher, InProcessDispatcher)


def test_get_dispatcher_celery_when_enabled():
    bg = MagicMock()
    with patch.dict(os.environ, {"XENIA_USE_CELERY": "1"}):
        dispatcher = get_dispatcher(bg)
    assert isinstance(dispatcher, CeleryDispatcher)


def test_get_dispatcher_celery_when_no_background_tasks():
    with patch.dict(os.environ, {"XENIA_USE_CELERY": "0"}, clear=False):
        dispatcher = get_dispatcher(None)
    assert isinstance(dispatcher, CeleryDispatcher)


def test_celery_dispatcher_calls_send_task():
    run_id = uuid.uuid4()
    with patch("xenia.executor.dispatch.celery_app") as celery_mock:
        CeleryDispatcher().dispatch(run_id)
    celery_mock.send_task.assert_called_once_with(
        "xenia.run_agent", args=[str(run_id)], queue="xenia"
    )


def test_inprocess_dispatcher_adds_background_task():
    run_id = uuid.uuid4()
    bg = MagicMock()
    InProcessDispatcher(bg).dispatch(run_id)
    assert bg.add_task.called
