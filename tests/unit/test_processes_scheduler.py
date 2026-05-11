"""Tests for the cron scheduler helpers used by the Processos surface."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from xenia.processes.scheduler import (
    InvalidCronError,
    cron_describe,
    cron_next,
    cron_validate,
)


def test_cron_validate_accepts_standard_5_field():
    cron_validate("*/15 * * * *")
    cron_validate("0 8-18/2 * * 1-5")
    cron_validate("0 9 1 * *")


def test_cron_validate_rejects_garbage():
    with pytest.raises(InvalidCronError):
        cron_validate("")
    with pytest.raises(InvalidCronError):
        cron_validate("not a cron")
    with pytest.raises(InvalidCronError):
        cron_validate("99 99 * * *")


def test_cron_next_is_after_anchor():
    anchor = datetime(2026, 5, 11, 12, 0, tzinfo=UTC)
    nxt = cron_next("*/15 * * * *", after=anchor)
    assert nxt > anchor
    # exactly 15 minutes later
    assert nxt == datetime(2026, 5, 11, 12, 15, tzinfo=UTC)


def test_cron_next_hourly_window_skips_to_next_day():
    """8-18/2 weekdays only — Saturday 23h should jump to Monday 08h."""
    saturday_late = datetime(2026, 5, 9, 23, 0, tzinfo=UTC)
    nxt = cron_next("0 8-18/2 * * 1-5", after=saturday_late)
    assert nxt.weekday() == 0  # Monday
    assert nxt.hour == 8


@pytest.mark.parametrize(
    "expression, hint",
    [
        ("*/15 * * * *", "15"),
        ("0 2 * * *", "2"),
        ("0 9 1 * *", "1"),
    ],
)
def test_cron_describe_includes_useful_token(expression: str, hint: str):
    label = cron_describe(expression)
    assert hint in label, f"expected hint {hint!r} in label {label!r}"
