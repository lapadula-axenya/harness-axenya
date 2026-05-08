"""OmniRouter LLM client.

Phase 1 assumes OmniRouter exposes an Anthropic-compatible API (per Q1
decision in the spec). It reuses the Anthropic SDK but points at a custom
base_url. If OmniRouter's surface diverges in Phase 3, override `complete` here.
"""
from __future__ import annotations

from typing import Any

from xenia.llm.anthropic_client import AnthropicClient
from xenia.llm.client import LLMMessage, LLMResponse


class OmniRouterClient:
    def __init__(self, api_key: str, base_url: str) -> None:
        if not base_url:
            raise ValueError("OmniRouter requires a base_url")
        self._inner = AnthropicClient(api_key=api_key, base_url=base_url)

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
        return await self._inner.complete(
            model=model,
            system=system,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
        )


def get_llm_client(provider: str, *, anthropic_api_key: str,
                   omnirouter_api_key: str, omnirouter_base_url: str) -> Any:
    """Factory selecting client by provider name."""
    if provider == "anthropic":
        return AnthropicClient(api_key=anthropic_api_key)
    if provider == "omnirouter":
        return OmniRouterClient(
            api_key=omnirouter_api_key, base_url=omnirouter_base_url
        )
    raise ValueError(f"unknown llm provider: {provider}")
