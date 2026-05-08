"""Unit tests for the Phase 1 simple executor (no DB)."""
from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import patch

import pytest

from xenia.agents.definition import (
    AgentDefinition,
    ExecutionConfig,
    LLMConfig,
)
from xenia.executor import executor as ex
from xenia.llm.client import LLMMessage, LLMResponse, ToolUse
from xenia.skills.base import SkillRegistry
from xenia.skills.hubspot import HubspotGetContact


class _StubLLMClient:
    """LLM client that replays a queued list of LLMResponse objects."""

    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    async def complete(self, **kwargs: Any) -> LLMResponse:
        self.calls.append(kwargs)
        if not self._responses:
            raise RuntimeError("no more stub responses")
        return self._responses.pop(0)


def _definition(skills: list[str]) -> AgentDefinition:
    return AgentDefinition(
        id="test_agent",
        nome="Test",
        descricao="Test agent",
        webhook_secret_env="WEBHOOK_SECRET_TEST",
        input_schema={"type": "object", "required": ["foo"], "properties": {"foo": {"type": "string"}}},
        llm=LLMConfig(provider="anthropic", model="claude-sonnet-4-6"),
        skills=skills,
        system_prompt="hello {{foo}}",
        execution=ExecutionConfig(max_steps=3, timeout_seconds=5),
    )


async def test_run_loop_stops_on_text_only_response():
    client = _StubLLMClient(
        [
            LLMResponse(
                text="all done",
                tool_uses=[],
                stop_reason="end_turn",
                tokens_input=10,
                tokens_output=5,
            )
        ]
    )
    skills = SkillRegistry()

    logged: list[tuple[str, int]] = []

    async def fake_log(_run_id, event_type, step, _payload):
        logged.append((event_type, step))

    with patch.object(ex, "_log_event", side_effect=fake_log):
        outcome = await ex._run_loop(
            run_id=uuid.uuid4(),
            definition=_definition([]),
            payload={"foo": "bar"},
            llm_client=client,
            skill_registry=skills,
        )

    assert outcome.output == "all done"
    assert outcome.error is None
    assert outcome.steps_executed == 1
    assert outcome.tokens_input == 10
    assert outcome.tokens_output == 5
    assert ("step_start", 1) in logged
    assert ("llm_response", 1) in logged


async def test_run_loop_executes_tool_then_stops():
    client = _StubLLMClient(
        [
            LLMResponse(
                tool_uses=[
                    ToolUse(
                        id="tu_1",
                        name="hubspot.get_contact",
                        input={"contact_id": "abc"},
                    )
                ],
                stop_reason="tool_use",
                tokens_input=20,
                tokens_output=8,
            ),
            LLMResponse(
                text="contact fetched",
                stop_reason="end_turn",
                tokens_input=15,
                tokens_output=4,
            ),
        ]
    )
    skills = SkillRegistry()
    skills.register(HubspotGetContact())

    with patch.object(ex, "_log_event"):
        outcome = await ex._run_loop(
            run_id=uuid.uuid4(),
            definition=_definition(["hubspot.get_contact"]),
            payload={"foo": "bar"},
            llm_client=client,
            skill_registry=skills,
        )

    assert outcome.output == "contact fetched"
    assert outcome.steps_executed == 2
    assert outcome.tokens_input == 35
    assert outcome.tokens_output == 12
    assert len(client.calls) == 2
    # Second call should include tool_result block
    second_messages: list[LLMMessage] = client.calls[1]["messages"]
    assert any(
        m.role == "user"
        and isinstance(m.content, list)
        and any(b.get("type") == "tool_result" for b in m.content)
        for m in second_messages
    )


async def test_run_loop_handles_unknown_skill_gracefully():
    client = _StubLLMClient(
        [
            LLMResponse(
                tool_uses=[ToolUse(id="tu_1", name="not.a.skill", input={})],
                stop_reason="tool_use",
            ),
            LLMResponse(text="fallback", stop_reason="end_turn"),
        ]
    )
    with patch.object(ex, "_log_event"):
        outcome = await ex._run_loop(
            run_id=uuid.uuid4(),
            definition=_definition([]),
            payload={"foo": "bar"},
            llm_client=client,
            skill_registry=SkillRegistry(),
        )
    assert outcome.output == "fallback"


async def test_run_loop_step_limit():
    # Always returns a tool_use, never finishes -> StepLimitError
    client = _StubLLMClient(
        [
            LLMResponse(
                tool_uses=[ToolUse(id=f"tu_{i}", name="hubspot.get_contact", input={"contact_id": "x"})],
                stop_reason="tool_use",
            )
            for i in range(10)
        ]
    )
    skills = SkillRegistry()
    skills.register(HubspotGetContact())

    with patch.object(ex, "_log_event"), pytest.raises(ex.StepLimitError):
        await ex._run_loop(
            run_id=uuid.uuid4(),
            definition=_definition(["hubspot.get_contact"]),
            payload={"foo": "bar"},
            llm_client=client,
            skill_registry=skills,
        )


def test_render_system_prompt_substitutes_payload():
    rendered = ex._render_system_prompt("hello {{name}}!", {"name": "world"})
    assert rendered == "hello world!"


def test_render_system_prompt_leaves_unmatched_placeholders():
    rendered = ex._render_system_prompt("hello {{name}} {{other}}", {"name": "x"})
    assert rendered == "hello x {{other}}"
