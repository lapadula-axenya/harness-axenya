"""Phase 2 LangGraph-driven executor.

Each run is a LangGraph thread (`thread_id = str(run_id)`). The Postgres
checkpointer persists state between steps, so a worker that dies mid-run can
be replaced and resume from the last checkpoint.

Contract:
  * `run_agent(run_id=...)` is the single entry-point used by the Celery task
    and by the API in dev/test mode (BackgroundTasks).
  * Every node transition produces a `run_events` row.
  * Cancellation is checked between steps by polling the `runs.status`
    column. A run flipped to `cancelled` exits the loop within one
    checkpoint boundary (≤10s in practice).
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import Any

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import CompiledStateGraph

from xenia.agents.definition import AgentDefinition
from xenia.agents.graph_builder import AgentState, build_graph
from xenia.config import get_settings
from xenia.llm.client import LLMClient
from xenia.skills.base import SkillRegistry
from xenia.storage.db import session_scope
from xenia.storage.models import RunStatus
from xenia.storage.repositories import RunEventRepository, RunRepository

logger = logging.getLogger(__name__)


@dataclass
class ExecutionOutcome:
    output: str | None
    error: str | None
    error_code: str | None
    error_class: str | None
    steps_executed: int
    tokens_input: int
    tokens_output: int
    cancelled: bool = False


class ExecutorError(Exception):
    def __init__(self, message: str, *, code: str = "EXECUTOR_ERROR") -> None:
        super().__init__(message)
        self.code = code


class StepLimitError(ExecutorError):
    def __init__(self, max_steps: int) -> None:
        super().__init__(
            f"agent exceeded max_steps={max_steps} without producing final answer",
            code="STEP_LIMIT_EXCEEDED",
        )


class ExecutorTimeoutError(ExecutorError):
    def __init__(self, timeout: int) -> None:
        super().__init__(
            f"agent exceeded timeout_seconds={timeout}", code="TIMEOUT"
        )


class CancelledError(ExecutorError):
    def __init__(self) -> None:
        super().__init__("run was cancelled", code="CANCELLED")


async def _open_checkpointer() -> AsyncPostgresSaver:
    """Open an `AsyncPostgresSaver` against the configured Postgres URL.

    Uses the sync URL form (`postgresql+psycopg://`) without the SQLAlchemy
    driver prefix — `langgraph-checkpoint-postgres` expects raw psycopg DSNs.
    """
    settings = get_settings()
    dsn = settings.database_url_sync.replace("postgresql+psycopg://", "postgresql://")
    saver_ctx = AsyncPostgresSaver.from_conn_string(dsn)
    saver = await saver_ctx.__aenter__()
    await saver.setup()
    saver._ctx = saver_ctx
    return saver


async def _close_checkpointer(saver: AsyncPostgresSaver) -> None:
    ctx = getattr(saver, "_ctx", None)
    if ctx is not None:
        await ctx.__aexit__(None, None, None)


async def run_agent(
    *,
    run_id: uuid.UUID,
    definition: AgentDefinition,
    payload: dict[str, Any],
    llm_client: LLMClient,
    skill_registry: SkillRegistry,
) -> ExecutionOutcome:
    """Execute a single run end-to-end. Persists status + events transactionally."""
    async with session_scope() as session:
        run_repo = RunRepository(session)
        run = await run_repo.get(run_id)
        if run is None:
            raise ExecutorError(f"run {run_id} not found")
        if run.status == RunStatus.cancelled:
            return ExecutionOutcome(
                output=None,
                error="cancelled before start",
                error_code="CANCELLED",
                error_class="CancelledError",
                steps_executed=0,
                tokens_input=0,
                tokens_output=0,
                cancelled=True,
            )
        await run_repo.mark_running(run)

    saver = await _open_checkpointer()
    try:
        outcome = await asyncio.wait_for(
            _run_graph(
                run_id=run_id,
                definition=definition,
                payload=payload,
                llm_client=llm_client,
                skill_registry=skill_registry,
                saver=saver,
            ),
            timeout=definition.execution.timeout_seconds,
        )
    except TimeoutError:
        outcome = ExecutionOutcome(
            output=None,
            error=f"timeout after {definition.execution.timeout_seconds}s",
            error_code="TIMEOUT",
            error_class="ExecutorTimeoutError",
            steps_executed=0,
            tokens_input=0,
            tokens_output=0,
        )
    except CancelledError:
        outcome = ExecutionOutcome(
            output=None,
            error="run cancelled",
            error_code="CANCELLED",
            error_class="CancelledError",
            steps_executed=0,
            tokens_input=0,
            tokens_output=0,
            cancelled=True,
        )
    except ExecutorError as exc:
        outcome = ExecutionOutcome(
            output=None,
            error=str(exc),
            error_code=exc.code,
            error_class=type(exc).__name__,
            steps_executed=0,
            tokens_input=0,
            tokens_output=0,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("unexpected executor error", extra={"run_id": str(run_id)})
        outcome = ExecutionOutcome(
            output=None,
            error=str(exc),
            error_code="UNEXPECTED",
            error_class=type(exc).__name__,
            steps_executed=0,
            tokens_input=0,
            tokens_output=0,
        )
    finally:
        await _close_checkpointer(saver)

    await _persist_outcome(run_id, outcome)
    return outcome


async def _run_graph(
    *,
    run_id: uuid.UUID,
    definition: AgentDefinition,
    payload: dict[str, Any],
    llm_client: LLMClient,
    skill_registry: SkillRegistry,
    saver: AsyncPostgresSaver,
) -> ExecutionOutcome:
    builder = build_graph(definition, llm_client, skill_registry)
    graph: CompiledStateGraph = builder.compile(checkpointer=saver)

    config = {"configurable": {"thread_id": str(run_id)}}
    initial_state: AgentState = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _build_initial_user_message(payload)}
                ],
            }
        ],
        "payload": payload,
        "step": 0,
        "tokens_input": 0,
        "tokens_output": 0,
        "last_error": None,
        "output": None,
        "cancelled": False,
        "branch": None,
    }

    final_state: AgentState | None = None
    step_counter = 0
    async for event in graph.astream(
        initial_state,
        config=config,
        stream_mode="values",
    ):
        final_state = event
        step_counter = int(event.get("step", step_counter) or step_counter)

        await _log_event(
            run_id,
            "step_start",
            step_counter,
            {
                "messages": len(event.get("messages") or []),
                "tokens_input_total": int(event.get("tokens_input") or 0),
                "tokens_output_total": int(event.get("tokens_output") or 0),
            },
        )

        # Co-operative cancellation check — fast-fail if /v1/runs/{id}/cancel
        # was hit. The graph stops after the current node finishes.
        if step_counter % 1 == 0 and await _is_cancelled(run_id):
            raise CancelledError()

        if step_counter >= definition.execution.max_steps:
            raise StepLimitError(definition.execution.max_steps)

    if final_state is None:
        raise ExecutorError("graph produced no events")

    output: str | None = final_state.get("output")
    return ExecutionOutcome(
        output=output,
        error=None,
        error_code=None,
        error_class=None,
        steps_executed=int(final_state.get("step") or step_counter),
        tokens_input=int(final_state.get("tokens_input") or 0),
        tokens_output=int(final_state.get("tokens_output") or 0),
    )


async def _persist_outcome(run_id: uuid.UUID, outcome: ExecutionOutcome) -> None:
    async with session_scope() as session:
        run_repo = RunRepository(session)
        event_repo = RunEventRepository(session)
        run = await run_repo.get(run_id)
        if run is None:
            return
        if outcome.cancelled:
            await run_repo.mark_cancelled(run)
            await event_repo.append(
                run_id=run_id,
                event_type="cancelled",
                step_number=outcome.steps_executed,
                payload={"reason": outcome.error or "user-requested"},
            )
            return
        if outcome.error is None:
            await run_repo.mark_done(
                run,
                output=outcome.output,
                steps_executed=outcome.steps_executed,
                tokens_input=outcome.tokens_input,
                tokens_output=outcome.tokens_output,
            )
            await event_repo.append(
                run_id=run_id,
                event_type="completed",
                step_number=outcome.steps_executed,
                payload={"output_chars": len(outcome.output or "")},
            )
        else:
            await run_repo.mark_failed(
                run,
                error=outcome.error,
                error_class=outcome.error_class or "Unknown",
                steps_executed=outcome.steps_executed,
            )
            await event_repo.append(
                run_id=run_id,
                event_type="error",
                step_number=outcome.steps_executed,
                payload={
                    "error": outcome.error,
                    "error_code": outcome.error_code,
                    "error_class": outcome.error_class,
                },
            )


async def _is_cancelled(run_id: uuid.UUID) -> bool:
    async with session_scope() as session:
        run = await RunRepository(session).get(run_id)
        return run is not None and run.status == RunStatus.cancelled


def _build_initial_user_message(payload: dict[str, Any]) -> str:
    import json

    return (
        "Você recebeu o seguinte payload de entrada. Use as ferramentas "
        "disponíveis quando precisar; responda em texto quando a tarefa estiver "
        f"concluída.\n\nPayload:\n```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```"
    )


async def _log_event(
    run_id: uuid.UUID, event_type: str, step: int, data: dict[str, Any]
) -> None:
    async with session_scope() as session:
        await RunEventRepository(session).append(
            run_id=run_id,
            event_type=event_type,
            step_number=step,
            payload=data,
        )


def _render_system_prompt(template: str, payload: dict[str, Any]) -> str:
    """Backward-compatible helper kept for tests that patched the old loop."""
    rendered = template
    for key, value in payload.items():
        rendered = rendered.replace("{{" + key + "}}", str(value))
    return rendered
