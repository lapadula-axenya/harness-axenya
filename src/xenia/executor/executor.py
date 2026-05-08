"""Phase 1 simple tool-use executor.

Runs a Claude-style loop:
  - send messages + tools to the LLM
  - if the response contains tool_uses, execute each, append tool_result blocks,
    repeat
  - otherwise, return the assistant's text

LangGraph + checkpointing replaces this in Phase 2; the public entry-point
`execute_run` will then dispatch to LangGraph.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import Any

from xenia.agents.definition import AgentDefinition
from xenia.llm.client import LLMClient, LLMMessage, LLMResponse
from xenia.skills.base import SkillRegistry, SkillResult
from xenia.storage.db import session_scope
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


async def run_agent(
    *,
    run_id: uuid.UUID,
    definition: AgentDefinition,
    payload: dict[str, Any],
    llm_client: LLMClient,
    skill_registry: SkillRegistry,
) -> ExecutionOutcome:
    """Run a single agent invocation. Persists run + events transactionally."""
    async with session_scope() as session:
        run_repo = RunRepository(session)
        event_repo = RunEventRepository(session)
        run = await run_repo.get(run_id)
        if run is None:
            raise ExecutorError(f"run {run_id} not found")
        await run_repo.mark_running(run)

    try:
        outcome = await asyncio.wait_for(
            _run_loop(
                run_id=run_id,
                definition=definition,
                payload=payload,
                llm_client=llm_client,
                skill_registry=skill_registry,
            ),
            timeout=definition.execution.timeout_seconds,
        )
    except TimeoutError:
        outcome = ExecutionOutcome(
            output=None,
            error=f"timeout after {definition.execution.timeout_seconds}s",
            error_code="TIMEOUT",
            error_class="TimeoutExceeded",
            steps_executed=0,
            tokens_input=0,
            tokens_output=0,
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

    async with session_scope() as session:
        run_repo = RunRepository(session)
        event_repo = RunEventRepository(session)
        run = await run_repo.get(run_id)
        if run is None:
            raise ExecutorError(f"run {run_id} disappeared")
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

    return outcome


async def _run_loop(
    *,
    run_id: uuid.UUID,
    definition: AgentDefinition,
    payload: dict[str, Any],
    llm_client: LLMClient,
    skill_registry: SkillRegistry,
) -> ExecutionOutcome:
    system_prompt = _render_system_prompt(definition.system_prompt, payload)
    tools = skill_registry.tools_for(definition.skills)

    messages: list[LLMMessage] = [
        LLMMessage(
            role="user",
            content=[{"type": "text", "text": _build_initial_user_message(payload)}],
        )
    ]

    tokens_input = 0
    tokens_output = 0
    final_text: str | None = None

    for step in range(1, definition.execution.max_steps + 1):
        await _log_event(run_id, "step_start", step, {"messages": len(messages)})

        response: LLMResponse = await llm_client.complete(
            model=definition.llm.model,
            system=system_prompt,
            messages=messages,
            tools=tools or None,
            max_tokens=definition.llm.max_tokens,
            temperature=definition.llm.temperature,
        )
        tokens_input += response.tokens_input
        tokens_output += response.tokens_output

        await _log_event(
            run_id,
            "llm_response",
            step,
            {
                "stop_reason": response.stop_reason,
                "tool_uses": len(response.tool_uses),
                "text_chars": len(response.text),
                "tokens_input": response.tokens_input,
                "tokens_output": response.tokens_output,
            },
        )

        if not response.has_tool_uses:
            final_text = response.text
            return ExecutionOutcome(
                output=final_text,
                error=None,
                error_code=None,
                error_class=None,
                steps_executed=step,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
            )

        # Append assistant message containing tool_use blocks.
        assistant_blocks: list[dict[str, Any]] = []
        if response.text:
            assistant_blocks.append({"type": "text", "text": response.text})
        for tu in response.tool_uses:
            assistant_blocks.append(
                {
                    "type": "tool_use",
                    "id": tu.id,
                    "name": tu.name,
                    "input": tu.input,
                }
            )
        messages.append(LLMMessage(role="assistant", content=assistant_blocks))

        # Execute every tool_use and produce tool_result blocks.
        tool_result_blocks: list[dict[str, Any]] = []
        for tu in response.tool_uses:
            await _log_event(
                run_id,
                "tool_call",
                step,
                {"tool_use_id": tu.id, "name": tu.name, "input": tu.input},
            )
            result = await _invoke_skill(skill_registry, tu.name, tu.input)
            await _log_event(
                run_id,
                "tool_result",
                step,
                {"tool_use_id": tu.id, "ok": result.ok, "error": result.error},
            )
            tool_result_blocks.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": [
                        {"type": "text", "text": _format_skill_result(result)}
                    ],
                    "is_error": not result.ok,
                }
            )

        messages.append(LLMMessage(role="user", content=tool_result_blocks))

    raise StepLimitError(definition.execution.max_steps)


def _render_system_prompt(template: str, payload: dict[str, Any]) -> str:
    """Replace {{var}} placeholders with payload values (string-only, no eval)."""
    rendered = template
    for key, value in payload.items():
        rendered = rendered.replace("{{" + key + "}}", str(value))
    return rendered


def _build_initial_user_message(payload: dict[str, Any]) -> str:
    import json

    return (
        "Você recebeu o seguinte payload de entrada. Use as ferramentas "
        "disponíveis quando precisar; responda em texto quando a tarefa estiver "
        f"concluída.\n\nPayload:\n```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```"
    )


async def _invoke_skill(
    registry: SkillRegistry, name: str, args: dict[str, Any]
) -> SkillResult:
    if not registry.has(name):
        return SkillResult(
            ok=False,
            error=f"unknown skill: {name}",
            error_code="UNKNOWN_SKILL",
        )
    skill = registry.get(name)
    try:
        return await asyncio.wait_for(
            skill.execute(**args), timeout=skill.timeout_seconds
        )
    except TimeoutError:
        return SkillResult(
            ok=False,
            error=f"skill {name} timed out after {skill.timeout_seconds}s",
            error_code="SKILL_TIMEOUT",
        )
    except Exception as exc:  # noqa: BLE001
        return SkillResult(
            ok=False, error=str(exc), error_code="SKILL_ERROR"
        )


def _format_skill_result(result: SkillResult) -> str:
    import json

    payload: dict[str, Any] = {"ok": result.ok}
    if result.data is not None:
        payload["data"] = result.data
    if result.error is not None:
        payload["error"] = result.error
    if result.error_code is not None:
        payload["error_code"] = result.error_code
    return json.dumps(payload, ensure_ascii=False)


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
