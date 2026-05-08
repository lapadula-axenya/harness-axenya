"""Unit tests for the YAML graph builder + condition evaluator."""
from __future__ import annotations

import pytest

from xenia.agents.definition import (
    AgentDefinition,
    ExecutionConfig,
    GraphConfig,
    GraphEdge,
    GraphNode,
    LLMConfig,
)
from xenia.agents.graph_builder import _evaluate_condition, build_graph
from xenia.llm.client import LLMResponse
from xenia.skills.base import SkillRegistry


class _NoopLLM:
    async def complete(self, **kwargs):  # type: ignore[no-untyped-def]
        return LLMResponse(text="ok", stop_reason="end_turn")


def test_evaluate_condition_equals_true():
    assert _evaluate_condition("state.branch == 'A'", {"branch": "A"}) is True


def test_evaluate_condition_equals_false():
    assert _evaluate_condition("state.branch == 'A'", {"branch": "B"}) is False


def test_evaluate_condition_in_list():
    assert _evaluate_condition("state.branch in ['A', 'B']", {"branch": "B"}) is True


def test_evaluate_condition_and():
    state = {"branch": "A", "step": 3}
    assert _evaluate_condition("state.branch == 'A' and state.step == 3", state) is True


def test_evaluate_condition_rejects_function_call():
    with pytest.raises(ValueError):
        _evaluate_condition("state.foo(1)", {"foo": "bar"})


def test_evaluate_condition_rejects_import():
    with pytest.raises(ValueError):
        _evaluate_condition("__import__('os')", {})


def _definition(graph: GraphConfig) -> AgentDefinition:
    return AgentDefinition(
        id="t",
        nome="t",
        descricao="t",
        webhook_secret_env="WEBHOOK_SECRET_T",
        input_schema={"type": "object", "properties": {}},
        llm=LLMConfig(provider="anthropic", model="m"),
        skills=[],
        system_prompt="x",
        execution=ExecutionConfig(),
        graph=graph,
    )


def test_build_default_graph_when_no_yaml_graph():
    definition = AgentDefinition(
        id="t",
        nome="t",
        descricao="t",
        webhook_secret_env="WEBHOOK_SECRET_T",
        input_schema={"type": "object", "properties": {}},
        llm=LLMConfig(provider="anthropic", model="m"),
        skills=[],
        system_prompt="x",
        execution=ExecutionConfig(),
    )
    builder = build_graph(definition, _NoopLLM(), SkillRegistry())
    # Graph should compile without error
    compiled = builder.compile()
    assert compiled is not None


def test_build_custom_graph_compiles():
    graph = GraphConfig(
        nodes=[
            GraphNode(name="step_a", type="llm_call", prompt="say hi"),
            GraphNode(name="step_b", type="llm_call", prompt="say bye"),
        ],
        edges=[
            GraphEdge.model_validate({"from": "ENTRY", "to": "step_a"}),
            GraphEdge.model_validate({"from": "step_a", "to": "step_b"}),
            GraphEdge.model_validate({"from": "step_b", "to": "END"}),
        ],
    )
    builder = build_graph(_definition(graph), _NoopLLM(), SkillRegistry())
    compiled = builder.compile()
    assert compiled is not None


def test_build_custom_graph_unknown_node_raises():
    graph = GraphConfig(
        nodes=[GraphNode(name="step_a", type="llm_call", prompt="x")],
        edges=[
            GraphEdge.model_validate({"from": "ENTRY", "to": "step_a"}),
            GraphEdge.model_validate({"from": "step_a", "to": "ghost"}),
        ],
    )
    with pytest.raises(ValueError, match="ghost"):
        build_graph(_definition(graph), _NoopLLM(), SkillRegistry())


def test_build_custom_graph_tool_call_requires_tool_field():
    graph = GraphConfig(
        nodes=[GraphNode(name="t", type="tool_call")],
        edges=[
            GraphEdge.model_validate({"from": "ENTRY", "to": "t"}),
            GraphEdge.model_validate({"from": "t", "to": "END"}),
        ],
    )
    with pytest.raises(ValueError, match="tool"):
        build_graph(_definition(graph), _NoopLLM(), SkillRegistry())
