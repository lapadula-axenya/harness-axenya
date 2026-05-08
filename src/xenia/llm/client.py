"""LLM client interface — common shape for Anthropic and OmniRouter."""
from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

Role = Literal["user", "assistant"]


class LLMMessage(BaseModel):
    role: Role
    content: list[dict[str, Any]] | str


class ToolUse(BaseModel):
    id: str
    name: str
    input: dict[str, Any]


class LLMResponse(BaseModel):
    """Normalized response across providers."""

    text: str = ""
    tool_uses: list[ToolUse] = Field(default_factory=list)
    stop_reason: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    raw: dict[str, Any] = Field(default_factory=dict)

    @property
    def has_tool_uses(self) -> bool:
        return len(self.tool_uses) > 0


class LLMClient(Protocol):
    async def complete(
        self,
        *,
        model: str,
        system: str,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse: ...
