"""Langfuse tracer — Phase 4 stub.

Wires up real traces in Phase 4. Methods are no-ops in Phase 1 so callers can
invoke them without conditional checks.
"""
from __future__ import annotations

import uuid
from typing import Any


class LangfuseTracer:
    def __init__(self, *, public_key: str, secret_key: str, host: str) -> None:
        self.enabled = bool(public_key and secret_key and host)

    async def trace_run(self, run_id: uuid.UUID, agent_id: str) -> str | None:
        if not self.enabled:
            return None
        return None

    async def log_llm_call(
        self, trace_id: str | None, prompt: Any, response: Any, usage: dict[str, int]
    ) -> None:
        return None

    async def log_tool_call(
        self,
        trace_id: str | None,
        skill_name: str,
        tool_input: dict[str, Any],
        tool_output: dict[str, Any],
    ) -> None:
        return None
