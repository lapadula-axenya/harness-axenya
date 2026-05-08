"""Generic MCP-backed skill — Phase 3 stub.

Phase 1 ships in-process mocks for the v1 skill list; real MCP connections
land in Phase 3. This file exists so that future code can import a stable
class name.
"""
from __future__ import annotations

from typing import Any

from xenia.skills.base import Skill, SkillResult


class MCPSkill(Skill):
    """Wraps a tool exposed by an MCP server."""

    def __init__(
        self,
        *,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        mcp_server_url: str,
        tool_name: str,
        timeout_seconds: int = 30,
        idempotent: bool = False,
    ) -> None:
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.timeout_seconds = timeout_seconds
        self.idempotent = idempotent
        self._mcp_server_url = mcp_server_url
        self._tool_name = tool_name

    async def execute(self, **kwargs: Any) -> SkillResult:
        raise NotImplementedError("MCP transport lands in Phase 3.")
