"""Langfuse integration — Phase 4.

Each run becomes one Langfuse trace; each LLM call lands as a `generation`
inside that trace; each tool call becomes a `span`. When the Langfuse env
vars are blank (dev/test), the tracer is a no-op so callers don't need to
guard each call site.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)


class LangfuseTracer:
    def __init__(
        self, *, public_key: str = "", secret_key: str = "", host: str = ""
    ) -> None:
        self.enabled = bool(public_key and secret_key and host)
        self._client: Any = None
        if self.enabled:
            try:
                from langfuse import Langfuse

                self._client = Langfuse(
                    public_key=public_key,
                    secret_key=secret_key,
                    host=host,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Langfuse client init failed: %s", exc)
                self.enabled = False

    def trace_run(self, run_id: uuid.UUID, agent_id: str) -> str | None:
        if not self.enabled or self._client is None:
            return None
        try:
            trace = self._client.trace(
                id=str(run_id),
                name=f"run:{agent_id}",
                metadata={"agent_id": agent_id},
            )
            return getattr(trace, "id", str(run_id))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Langfuse trace_run failed: %s", exc)
            return None

    def log_llm_call(
        self,
        *,
        trace_id: str | None,
        model: str,
        prompt: list[Any],
        response_text: str,
        tokens_input: int,
        tokens_output: int,
    ) -> None:
        if not self.enabled or self._client is None or trace_id is None:
            return
        try:
            self._client.generation(
                trace_id=trace_id,
                name="llm_call",
                model=model,
                input=prompt,
                output=response_text,
                usage={
                    "input": tokens_input,
                    "output": tokens_output,
                    "total": tokens_input + tokens_output,
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Langfuse log_llm_call failed: %s", exc)

    def log_tool_call(
        self,
        *,
        trace_id: str | None,
        skill_name: str,
        tool_input: dict[str, Any],
        tool_output: dict[str, Any],
        ok: bool,
    ) -> None:
        if not self.enabled or self._client is None or trace_id is None:
            return
        try:
            self._client.span(
                trace_id=trace_id,
                name=f"skill:{skill_name}",
                input=tool_input,
                output=tool_output,
                level="DEFAULT" if ok else "ERROR",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Langfuse log_tool_call failed: %s", exc)

    def flush(self) -> None:
        if self.enabled and self._client is not None:
            try:
                self._client.flush()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Langfuse flush failed: %s", exc)


_global_tracer: LangfuseTracer | None = None


def get_tracer() -> LangfuseTracer:
    global _global_tracer
    if _global_tracer is None:
        from xenia.config import get_settings

        s = get_settings()
        _global_tracer = LangfuseTracer(
            public_key=s.langfuse_public_key,
            secret_key=s.langfuse_secret_key,
            host=s.langfuse_host,
        )
    return _global_tracer


def reset_tracer() -> None:
    global _global_tracer
    _global_tracer = None
