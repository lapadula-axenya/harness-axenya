"""Unit tests for Phase 2 executor — graph drives LangGraph, no DB needed.

The compiled graph uses an in-memory MemorySaver checkpointer so we can run
the full StateGraph without Postgres.
"""
from __future__ import annotations

from typing import Any

import pytest
from langgraph.checkpoint.memory import MemorySaver

from xenia.agents.definition import (
    AgentDefinition,
    ExecutionConfig,
    LLMConfig,
)
from xenia.agents.graph_builder import build_graph
from xenia.llm.client import LLMResponse, ToolUse
from xenia.skills.base import SkillRegistry
from xenia.skills.hubspot import HubspotGetContact


class _StubLLMClient:
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
        input_schema={
            "type": "object",
            "required": ["foo"],
            "properties": {"foo": {"type": "string"}},
        },
        llm=LLMConfig(provider="anthropic", model="claude-sonnet-4-6"),
        skills=skills,
        system_prompt="hello {{foo}}",
        execution=ExecutionConfig(max_steps=5, timeout_seconds=5),
    )


async def _run(graph, payload: dict[str, Any]) -> dict[str, Any]:
    final: dict[str, Any] = {}
    config = {"configurable": {"thread_id": "test"}}
    async for event in graph.astream(
        {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "go"}]}
            ],
            "payload": payload,
            "step": 0,
            "tokens_input": 0,
            "tokens_output": 0,
            "cancelled": False,
        },
        config=config,
        stream_mode="values",
    ):
        final = event
    return final


@pytest.mark.asyncio
async def test_default_graph_text_only_response():
    client = _StubLLMClient(
        [
            LLMResponse(
                text="all done",
                stop_reason="end_turn",
                tokens_input=10,
                tokens_output=4,
            )
        ]
    )
    builder = build_graph(_definition([]), client, SkillRegistry())
    graph = builder.compile(checkpointer=MemorySaver())

    final = await _run(graph, {"foo": "bar"})
    assert final["output"] == "all done"
    assert final["tokens_input"] == 10
    assert final["tokens_output"] == 4


@pytest.mark.asyncio
async def test_default_graph_executes_tool_then_finishes():
    client = _StubLLMClient(
        [
            LLMResponse(
                tool_uses=[
                    ToolUse(
                        id="tu_1",
                        name="hubspot.get_contact",
                        input={"contact_id": "c1"},
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
    builder = build_graph(_definition(["hubspot.get_contact"]), client, skills)
    graph = builder.compile(checkpointer=MemorySaver())

    final = await _run(graph, {"foo": "bar"})
    assert final["output"] == "contact fetched"
    assert final["tokens_input"] == 35
    assert final["tokens_output"] == 12
    # Two LLM calls: initial + after tool result
    assert len(client.calls) == 2


@pytest.mark.asyncio
async def test_default_graph_cancel_short_circuits():
    """When cancelled flag is set, llm_call short-circuits without invoking client."""
    client = _StubLLMClient([])  # would raise if called
    builder = build_graph(_definition([]), client, SkillRegistry())
    graph = builder.compile(checkpointer=MemorySaver())

    final: dict[str, Any] = {}
    config = {"configurable": {"thread_id": "cancel-test"}}
    async for event in graph.astream(
        {
            "messages": [],
            "payload": {"foo": "bar"},
            "step": 0,
            "tokens_input": 0,
            "tokens_output": 0,
            "cancelled": True,
        },
        config=config,
        stream_mode="values",
    ):
        final = event
    # No LLM calls happened
    assert client.calls == []
    assert final.get("output") is None
