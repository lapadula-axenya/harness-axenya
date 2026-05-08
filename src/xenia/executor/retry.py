"""Retry policy — Phase 1 helper, full retry orchestration in Phase 2."""
from __future__ import annotations

RETRYABLE_ERROR_CODES = frozenset(
    {
        "MCP_UNAVAILABLE",
        "LLM_RATE_LIMIT",
        "LLM_TIMEOUT",
        "DB_TRANSIENT",
    }
)


def is_retryable(error_code: str | None) -> bool:
    return error_code is not None and error_code in RETRYABLE_ERROR_CODES


def backoff_seconds(attempt: int, base: int = 30) -> int:
    """Exponential backoff: base * 2^attempt, capped at 30 minutes."""
    capped: int = min(base * (2**attempt), 1800)
    return capped
