"""Anthropic SDK wrapper implementing the LLMClient protocol."""
from __future__ import annotations

from typing import Any

from anthropic import AsyncAnthropic

from xenia.llm.client import LLMMessage, LLMResponse, ToolUse


class AnthropicClient:
    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = AsyncAnthropic(**kwargs)

    async def complete(
        self,
        *,
        model: str,
        system: str,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        sdk_messages = [m.model_dump() for m in messages]
        kwargs: dict[str, Any] = {
            "model": model,
            "system": system,
            "messages": sdk_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools

        response = await self._client.messages.create(**kwargs)
        return _normalize(response)


def _normalize(response: Any) -> LLMResponse:
    text_parts: list[str] = []
    tool_uses: list[ToolUse] = []
    for block in response.content:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            text_parts.append(block.text)
        elif block_type == "tool_use":
            tool_uses.append(
                ToolUse(id=block.id, name=block.name, input=dict(block.input))
            )

    usage = getattr(response, "usage", None)
    return LLMResponse(
        text="".join(text_parts),
        tool_uses=tool_uses,
        stop_reason=getattr(response, "stop_reason", "") or "",
        tokens_input=getattr(usage, "input_tokens", 0) if usage else 0,
        tokens_output=getattr(usage, "output_tokens", 0) if usage else 0,
        raw={},
    )
