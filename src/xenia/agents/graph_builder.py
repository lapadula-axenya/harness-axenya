"""LangGraph builder — Phase 2.

Compiles an `AgentDefinition` into a LangGraph `StateGraph`. Two paths:

  * **default graph** (no `graph:` field) — classic tool-use loop:
      START -> llm_call -> (tool_exec -> llm_call)* -> END

  * **custom graph** (`graph:` block) — declarative nodes + edges from YAML.
    Supported node types: `llm_call`, `tool_call`, `branch`, `human_input`.
    Conditional edges are evaluated against the current `AgentState` via a
    safe AST walker (no `eval`).

Compiled graphs are returned uncompiled so callers can attach a checkpointer
(see `xenia.executor.executor`).
"""
from __future__ import annotations

import ast
import json
import operator
from collections.abc import Callable
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from xenia.agents.definition import AgentDefinition, GraphConfig, GraphNode
from xenia.llm.client import LLMClient, LLMMessage, LLMResponse
from xenia.skills.base import SkillRegistry, SkillResult


class AgentState(TypedDict, total=False):
    """Shared state passed between LangGraph nodes.

    `messages` is a plain list of `{role, content}` dicts that we
    accumulate via `operator.add`. We deliberately don't use
    `langgraph.graph.message.add_messages` because that reducer coerces
    entries into LangChain message objects, while our nodes want the raw
    Anthropic-style block lists.
    """

    messages: Annotated[list[dict[str, Any]], operator.add]
    payload: dict[str, Any]
    step: int
    tokens_input: int
    tokens_output: int
    last_error: str | None
    output: str | None
    cancelled: bool
    branch: str | None  # last branch decision, used by conditional edges


# ── Default graph ──────────────────────────────────────────────────────────


def _make_llm_node(
    definition: AgentDefinition,
    llm_client: LLMClient,
) -> Callable[[AgentState], Any]:
    """LLM call node — sends conversation + tools, captures response."""
    system_prompt = _render_system_prompt(definition.system_prompt)

    async def node(state: AgentState) -> AgentState:
        if state.get("cancelled"):
            return state

        rendered_system = _interpolate(system_prompt, state.get("payload") or {})
        sdk_messages = _to_llm_messages(state.get("messages") or [])
        tools = _tool_schemas(definition, state)

        response: LLMResponse = await llm_client.complete(
            model=definition.llm.model,
            system=rendered_system,
            messages=sdk_messages,
            tools=tools or None,
            max_tokens=definition.llm.max_tokens,
            temperature=definition.llm.temperature,
        )

        new_messages: list[dict[str, Any]] = []
        if response.tool_uses or response.text:
            blocks: list[dict[str, Any]] = []
            if response.text:
                blocks.append({"type": "text", "text": response.text})
            for tu in response.tool_uses:
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": tu.id,
                        "name": tu.name,
                        "input": tu.input,
                    }
                )
            new_messages.append({"role": "assistant", "content": blocks})

        result: AgentState = {
            "messages": new_messages,
            "step": (state.get("step") or 0) + 1,
            "tokens_input": (state.get("tokens_input") or 0) + response.tokens_input,
            "tokens_output": (state.get("tokens_output") or 0) + response.tokens_output,
        }
        if not response.has_tool_uses:
            result["output"] = response.text
        return result

    return node


def _make_tool_node(
    skill_registry: SkillRegistry,
    *,
    only_tool: str | None = None,
) -> Callable[[AgentState], Any]:
    """Tool execution node — finds the latest tool_use blocks and runs them.

    When `only_tool` is set (custom-graph `tool_call` nodes), ignores tool_use
    blocks and invokes that fixed tool with the current payload as kwargs.
    """

    async def node(state: AgentState) -> AgentState:
        if state.get("cancelled"):
            return state

        new_messages: list[dict[str, Any]] = []

        if only_tool:
            args = dict(state.get("payload") or {})
            result = await _invoke_skill(skill_registry, only_tool, args)
            new_messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": f"node-{only_tool}",
                            "content": [
                                {"type": "text", "text": _format_skill_result(result)}
                            ],
                            "is_error": not result.ok,
                        }
                    ],
                }
            )
            return {"messages": new_messages}

        last_assistant = _last_assistant(state)
        if last_assistant is None:
            return state

        tool_results: list[dict[str, Any]] = []
        for block in last_assistant.get("content", []):
            if block.get("type") != "tool_use":
                continue
            tu_id = block["id"]
            name = block["name"]
            args = block.get("input") or {}
            skill_result = await _invoke_skill(skill_registry, name, args)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tu_id,
                    "content": [
                        {"type": "text", "text": _format_skill_result(skill_result)}
                    ],
                    "is_error": not skill_result.ok,
                }
            )
        if tool_results:
            new_messages.append({"role": "user", "content": tool_results})
        return {"messages": new_messages}

    return node


def _should_use_tool(state: AgentState) -> str:
    """Conditional router for the default graph."""
    if state.get("cancelled"):
        return "end"
    last = _last_assistant(state)
    if last is None:
        return "end"
    for block in last.get("content", []):
        if block.get("type") == "tool_use":
            return "tool"
    return "end"


def _build_default(
    definition: AgentDefinition,
    llm_client: LLMClient,
    skill_registry: SkillRegistry,
) -> StateGraph:
    builder: StateGraph = StateGraph(AgentState)
    builder.add_node("llm_call", _make_llm_node(definition, llm_client))
    builder.add_node("tool_exec", _make_tool_node(skill_registry))
    builder.add_edge(START, "llm_call")
    builder.add_conditional_edges(
        "llm_call",
        _should_use_tool,
        {"tool": "tool_exec", "end": END},
    )
    builder.add_edge("tool_exec", "llm_call")
    return builder


# ── Custom graph ──────────────────────────────────────────────────────────


def _make_custom_node(
    node_def: GraphNode,
    definition: AgentDefinition,
    llm_client: LLMClient,
    skill_registry: SkillRegistry,
) -> Callable[[AgentState], Any]:
    if node_def.type == "llm_call":
        custom_def = definition.model_copy()
        custom_def.system_prompt = node_def.prompt or definition.system_prompt
        return _make_llm_node(custom_def, llm_client)
    if node_def.type == "tool_call":
        if not node_def.tool:
            raise ValueError(f"node {node_def.name!r} has type=tool_call but no `tool`")
        return _make_tool_node(skill_registry, only_tool=node_def.tool)
    if node_def.type == "branch":
        async def branch_node(state: AgentState) -> AgentState:
            return state

        return branch_node
    if node_def.type == "human_input":
        async def hold_node(state: AgentState) -> AgentState:
            # Phase 2 implementation: pause the graph; resume requires
            # external POST. The interrupt mechanic uses LangGraph's
            # native interrupt_before; here we just no-op so the graph
            # halts on the next checkpoint boundary.
            return state

        return hold_node
    raise ValueError(f"unsupported node type: {node_def.type}")


def _build_custom(
    graph_cfg: GraphConfig,
    definition: AgentDefinition,
    llm_client: LLMClient,
    skill_registry: SkillRegistry,
) -> StateGraph:
    builder: StateGraph = StateGraph(AgentState)

    by_name: dict[str, GraphNode] = {n.name: n for n in graph_cfg.nodes}
    for node_def in graph_cfg.nodes:
        builder.add_node(
            node_def.name,
            _make_custom_node(node_def, definition, llm_client, skill_registry),
        )

    # Group edges by source so we can use add_conditional_edges when needed.
    edges_by_source: dict[str, list[Any]] = {}
    for edge in graph_cfg.edges:
        edges_by_source.setdefault(edge.from_, []).append(edge)

    for source, edges in edges_by_source.items():
        from_node = START if source == "ENTRY" else source
        if any(e.condition for e in edges):
            mapping: dict[str, str] = {}
            default_target: str | None = None
            for edge in edges:
                target = END if edge.to == "END" else edge.to
                if edge.condition:
                    mapping[edge.condition] = target
                else:
                    default_target = target
            mapping_local = dict(mapping)
            default_local = default_target

            def _router(state: AgentState, m: dict[str, str] = mapping_local,
                        d: str | None = default_local) -> str:
                for cond_str, _target in m.items():
                    if _evaluate_condition(cond_str, state):
                        return cond_str
                return d or END

            builder.add_conditional_edges(from_node, _router, {**mapping_local, END: END})
        else:
            for edge in edges:
                target = END if edge.to == "END" else edge.to
                builder.add_edge(from_node, target)

    # Validate that targets exist.
    for edge in graph_cfg.edges:
        if edge.to != "END" and edge.to not in by_name:
            raise ValueError(f"edge points to unknown node: {edge.to!r}")
        if edge.from_ != "ENTRY" and edge.from_ not in by_name:
            raise ValueError(f"edge originates from unknown node: {edge.from_!r}")

    return builder


def build_graph(
    definition: AgentDefinition,
    llm_client: LLMClient,
    skill_registry: SkillRegistry,
) -> StateGraph:
    """Compile the agent's StateGraph (uncompiled — caller attaches checkpointer)."""
    if definition.graph is None:
        return _build_default(definition, llm_client, skill_registry)
    return _build_custom(definition.graph, definition, llm_client, skill_registry)


# ── Helpers ───────────────────────────────────────────────────────────────


def _render_system_prompt(template: str) -> str:
    return template


def _interpolate(template: str, payload: dict[str, Any]) -> str:
    rendered = template
    for key, value in payload.items():
        rendered = rendered.replace("{{" + key + "}}", str(value))
    return rendered


def _to_llm_messages(state_messages: list[Any]) -> list[LLMMessage]:
    out: list[LLMMessage] = []
    for m in state_messages:
        if isinstance(m, dict):
            out.append(LLMMessage(role=m["role"], content=m.get("content", "")))
        else:
            out.append(LLMMessage(role=m.role, content=m.content))
    return out


def _tool_schemas(definition: AgentDefinition, state: AgentState) -> list[dict[str, Any]]:
    from xenia.skills.base import get_skill_registry

    registry = get_skill_registry()
    schemas: list[dict[str, Any]] = []
    for name in definition.skills:
        if registry.has(name):
            schemas.append(registry.get(name).to_tool_schema())
    return schemas


def _last_assistant(state: AgentState) -> dict[str, Any] | None:
    for m in reversed(state.get("messages") or []):
        if isinstance(m, dict) and m.get("role") == "assistant":
            return m
    return None


async def _invoke_skill(
    registry: SkillRegistry, name: str, args: dict[str, Any]
) -> SkillResult:
    import asyncio

    if not registry.has(name):
        return SkillResult(
            ok=False, error=f"unknown skill: {name}", error_code="UNKNOWN_SKILL"
        )
    skill = registry.get(name)
    try:
        return await asyncio.wait_for(skill.execute(**args), timeout=skill.timeout_seconds)
    except TimeoutError:
        return SkillResult(
            ok=False,
            error=f"skill {name} timed out after {skill.timeout_seconds}s",
            error_code="SKILL_TIMEOUT",
        )
    except Exception as exc:  # noqa: BLE001
        return SkillResult(ok=False, error=str(exc), error_code="SKILL_ERROR")


def _format_skill_result(result: SkillResult) -> str:
    payload: dict[str, Any] = {"ok": result.ok}
    if result.data is not None:
        payload["data"] = result.data
    if result.error is not None:
        payload["error"] = result.error
    if result.error_code is not None:
        payload["error_code"] = result.error_code
    return json.dumps(payload, ensure_ascii=False)


# ── Safe condition evaluator ──────────────────────────────────────────────

# Supports expressions of the form:
#   state.field == 'literal'
#   state.field != 'literal'
#   state.field in ['a', 'b']
#   state.field
# (truthy check). No function calls, no attribute traversal beyond `state.x`.

_ALLOWED_NODE_TYPES = (
    ast.Expression,
    ast.Compare,
    ast.Constant,
    ast.Name,
    ast.Load,
    ast.Eq,
    ast.NotEq,
    ast.In,
    ast.NotIn,
    ast.List,
    ast.Tuple,
    ast.Attribute,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.UnaryOp,
    ast.Not,
)


def _evaluate_condition(expr: str, state: AgentState) -> bool:
    """Evaluate `expr` against `state` without invoking eval/exec.

    Only a small subset of expressions is allowed; anything else raises.
    """
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"invalid condition: {expr!r}: {exc}") from exc

    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODE_TYPES):
            raise ValueError(
                f"disallowed expression in condition: {type(node).__name__}"
            )

    return bool(_eval_node(tree.body, state))


def _eval_node(node: ast.AST, state: AgentState) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id == "state":
            return state
        if node.id == "True":
            return True
        if node.id == "False":
            return False
        raise ValueError(f"unknown name in condition: {node.id}")
    if isinstance(node, ast.Attribute):
        target = _eval_node(node.value, state)
        if isinstance(target, dict):
            return target.get(node.attr)
        return getattr(target, node.attr, None)
    if isinstance(node, ast.List | ast.Tuple):
        return [_eval_node(e, state) for e in node.elts]
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, state)
        for op, comp in zip(node.ops, node.comparators, strict=True):
            right = _eval_node(comp, state)
            if isinstance(op, ast.Eq):
                ok = left == right
            elif isinstance(op, ast.NotEq):
                ok = left != right
            elif isinstance(op, ast.In):
                ok = left in right
            elif isinstance(op, ast.NotIn):
                ok = left not in right
            else:
                raise ValueError(f"unsupported comparator: {type(op).__name__}")
            if not ok:
                return False
            left = right
        return True
    if isinstance(node, ast.BoolOp):
        values = [_eval_node(v, state) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        return any(values)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _eval_node(node.operand, state)
    raise ValueError(f"unsupported node: {type(node).__name__}")
