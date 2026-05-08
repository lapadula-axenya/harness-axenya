"""LangGraph builder — Phase 2 stub.

Phase 1 ships a simple loop-based executor in `xenia.executor.executor`. This
module exists so that imports work and the file path matches the spec.
"""
from __future__ import annotations

from typing import Any

from xenia.agents.definition import AgentDefinition


def build_graph(definition: AgentDefinition) -> Any:
    raise NotImplementedError(
        "LangGraph integration lands in Phase 2; Phase 1 uses xenia.executor.executor."
    )
