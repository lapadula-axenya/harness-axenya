"""Generic MCP-backed skill (Phase 3).

Adapts a tool exposed by an MCP server (HTTP/SSE transport) to the
`Skill` interface. The skill is configured at construction time with the
MCP server URL, an auth header (typically `Bearer <token>`), and the
remote tool name. At execute-time it opens a short-lived `ClientSession`,
calls the tool, and converts the response into a `SkillResult`.

Why short-lived sessions: agents can run for minutes; persistent sessions
across executor restarts add complexity for little gain. The MCP server
TCP setup cost is small; if it ever becomes a bottleneck we'll add a
session pool.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from xenia.skills.base import Skill, SkillResult

logger = logging.getLogger(__name__)


class MCPSkill(Skill):
    """Wraps a single tool exposed by an MCP server."""

    def __init__(
        self,
        *,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        server_url: str,
        remote_tool: str,
        auth_header: str | None = None,
        timeout_seconds: int = 30,
        idempotent: bool = False,
    ) -> None:
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.timeout_seconds = timeout_seconds
        self.idempotent = idempotent
        self._server_url = server_url
        self._remote_tool = remote_tool
        self._auth_header = auth_header

    async def execute(self, **kwargs: Any) -> SkillResult:
        try:
            async with self._session() as session:
                response = await session.call_tool(self._remote_tool, kwargs)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "MCP call %s -> %s failed: %s", self.name, self._remote_tool, exc
            )
            return SkillResult(
                ok=False,
                error=str(exc),
                error_code="MCP_UNAVAILABLE",
            )

        if getattr(response, "isError", False):
            content = _extract_text(response)
            return SkillResult(
                ok=False,
                error=content or "MCP server returned error",
                error_code="MCP_TOOL_ERROR",
            )

        return SkillResult(ok=True, data={"content": _extract_content(response)})

    @asynccontextmanager
    async def _session(self):  # type: ignore[no-untyped-def]
        # Imported inside the function so the rest of the harness keeps
        # working when `mcp` isn't installed (dev images, tests).
        from mcp import ClientSession
        from mcp.client.sse import sse_client

        headers = {"Authorization": self._auth_header} if self._auth_header else {}
        async with (
            sse_client(self._server_url, headers=headers) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            yield session


def _extract_text(response: Any) -> str:
    parts: list[str] = []
    for block in getattr(response, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts)


def _extract_content(response: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for block in getattr(response, "content", []) or []:
        block_type = getattr(block, "type", "text")
        if block_type == "text":
            out.append({"type": "text", "text": getattr(block, "text", "")})
        else:
            out.append({"type": block_type, "data": str(block)})
    return out
