"""Phase 3 skill tests — backend selection + transport stubs."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from xenia.skills.hubspot import HubspotGetContact
from xenia.skills.hubspot import all_skills as hubspot_all
from xenia.skills.jira import JiraCreateIssue
from xenia.skills.jira import all_skills as jira_all
from xenia.skills.ksenia import KseniaReadUser
from xenia.skills.mcp_skill import MCPSkill
from xenia.skills.slack import SlackNotifyChannel
from xenia.skills.slack import all_skills as slack_all


def test_hubspot_returns_mocks_when_env_unset(monkeypatch):
    monkeypatch.delenv("HUBSPOT_MCP_URL", raising=False)
    skills = hubspot_all()
    assert all(isinstance(s, HubspotGetContact.__bases__[0]) for s in skills)
    assert not any(isinstance(s, MCPSkill) for s in skills)


def test_hubspot_returns_mcp_when_env_set(monkeypatch):
    monkeypatch.setenv("HUBSPOT_MCP_URL", "https://hubspot-mcp.local/sse")
    monkeypatch.setenv("HUBSPOT_MCP_TOKEN", "tok")
    from xenia.security.secrets import reset_cache

    reset_cache()
    skills = hubspot_all()
    assert all(isinstance(s, MCPSkill) for s in skills)
    names = {s.name for s in skills}
    assert "hubspot.get_contact" in names


def test_slack_returns_mocks_when_env_unset(monkeypatch):
    monkeypatch.delenv("SLACK_MCP_URL", raising=False)
    skills = slack_all()
    assert any(isinstance(s, SlackNotifyChannel) for s in skills)


def test_jira_returns_mocks_when_env_unset(monkeypatch):
    monkeypatch.delenv("JIRA_MCP_URL", raising=False)
    skills = jira_all()
    assert any(isinstance(s, JiraCreateIssue) for s in skills)


@pytest.mark.asyncio
async def test_ksenia_fails_without_url(monkeypatch):
    monkeypatch.delenv("KSENIA_API_URL", raising=False)
    result = await KseniaReadUser().execute(user_id="u1")
    assert result.ok is False
    assert result.error_code == "NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_ksenia_calls_http_with_token(monkeypatch):
    monkeypatch.setenv("KSENIA_API_URL", "https://ksenia.test")
    monkeypatch.setenv("KSENIA_API_TOKEN", "abc")
    from xenia.security.secrets import reset_cache

    reset_cache()

    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"id": "u1", "name": "Maria"})

    transport = httpx.MockTransport(handler)

    real_async_client = httpx.AsyncClient

    def factory(*args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    with patch("xenia.skills.ksenia.httpx.AsyncClient", side_effect=factory):
        result = await KseniaReadUser().execute(user_id="u1")

    assert result.ok is True
    assert result.data == {"id": "u1", "name": "Maria"}
    assert captured["url"] == "https://ksenia.test/users/u1"
    assert captured["auth"] == "Bearer abc"


@pytest.mark.asyncio
async def test_mcp_skill_wraps_tool_response():
    skill = MCPSkill(
        name="x.do",
        description="d",
        input_schema={"type": "object"},
        server_url="https://mcp.test/sse",
        remote_tool="do",
        auth_header="Bearer abc",
    )

    fake_session = AsyncMock()
    fake_response = type(
        "R",
        (),
        {
            "isError": False,
            "content": [type("B", (), {"type": "text", "text": "ok"})()],
        },
    )()
    fake_session.call_tool = AsyncMock(return_value=fake_response)

    @asyncio_contextmanager
    async def fake_session_cm(self):  # type: ignore[no-untyped-def]
        yield fake_session

    with patch.object(MCPSkill, "_session", fake_session_cm):
        result = await skill.execute(arg="value")

    assert result.ok is True
    assert result.data is not None
    assert any(b.get("text") == "ok" for b in result.data["content"])


def asyncio_contextmanager(func):
    """Tiny replacement for `contextlib.asynccontextmanager` that wraps a
    plain async generator into the protocol expected by `async with`."""
    from contextlib import asynccontextmanager

    return asynccontextmanager(func)
