"""Integration test: webhook -> run -> status."""
from __future__ import annotations

import os
import time
from typing import Any
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from xenia.api.main import app
from xenia.llm.client import LLMResponse
from xenia.security.hmac_verify import compute_signature

pytestmark = pytest.mark.integration


def _agent_secret(agent_id: str) -> str:
    """Read the HMAC secret from the same env var the server reads.

    Must be evaluated at call-time, not import-time, because pytest plugins
    or CI may set the var after this module is imported.
    """
    name = f"WEBHOOK_SECRET_{agent_id.upper()}"
    return os.environ[name]


@pytest.fixture(autouse=True)
async def _seed_agents():
    """Webhook flow needs an `agents` row so the FK on `runs.agent_id` is satisfied.

    Async fixture so we reuse pytest-asyncio's event loop — running
    `asyncio.run(...)` here would close the loop our cached SQLAlchemy
    engine is bound to and break the next test with `Event loop is closed`.
    """
    from xenia.agents.registry import get_registry
    from xenia.storage.db import reset_engine, session_scope
    from xenia.storage.repositories import AgentRepository

    registry = get_registry()
    async with session_scope() as session:
        repo = AgentRepository(session)
        for definition in registry.list_all():
            await repo.upsert(
                agent_id=definition.id,
                nome=definition.nome,
                descricao=definition.descricao,
                yaml_hash=registry.yaml_hash(definition.id),
                yaml_content=registry.yaml_content(definition.id),
            )
    yield
    await reset_engine()


class _FakeLLM:
    def __init__(self, response: LLMResponse) -> None:
        self.response = response

    async def complete(self, **kwargs: Any) -> LLMResponse:
        return self.response


@pytest.fixture
def fake_llm():
    return _FakeLLM(
        LLMResponse(
            text="echoing payload",
            stop_reason="end_turn",
            tokens_input=12,
            tokens_output=4,
        )
    )


async def test_webhook_rejects_missing_signature():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/webhooks/exemplo_eco",
            content=b'{"foo":"bar"}',
            headers={"Content-Type": "application/json"},
        )
    assert resp.status_code == 401


async def test_webhook_rejects_unknown_agent():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        body = b'{"foo":"bar"}'
        ts = str(int(time.time()))
        sig = compute_signature(body, ts, _agent_secret("exemplo_eco"))
        resp = await client.post(
            "/v1/webhooks/does_not_exist",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Xenia-Signature": sig,
                "X-Xenia-Timestamp": ts,
            },
        )
    assert resp.status_code == 404


async def test_webhook_rejects_invalid_payload():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        body = b'{"wrong_field":"x"}'
        ts = str(int(time.time()))
        sig = compute_signature(body, ts, _agent_secret("exemplo_eco"))
        resp = await client.post(
            "/v1/webhooks/exemplo_eco",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Xenia-Signature": sig,
                "X-Xenia-Timestamp": ts,
            },
        )
    assert resp.status_code == 422


async def test_webhook_full_flow_creates_run(fake_llm):
    """Successful webhook returns 202 + run_id, executor runs, status becomes 'done'."""
    transport = ASGITransport(app=app)

    body = b'{"foo":"hello"}'
    ts = str(int(time.time()))
    sig = compute_signature(body, ts, _agent_secret("exemplo_eco"))

    # Phase 2 moved LLM client construction into the worker codepath.
    # InProcessDispatcher runs `_run_agent_async`, which builds the client
    # via xenia.executor.tasks.get_llm_client — that's the patch site.
    with patch(
        "xenia.executor.tasks.get_llm_client",
        return_value=fake_llm,
    ):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/webhooks/exemplo_eco",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Xenia-Signature": sig,
                    "X-Xenia-Timestamp": ts,
                },
            )
            assert resp.status_code == 202, resp.text
            run_id = resp.json()["run_id"]
            assert resp.json()["status"] == "queued"

            # Background task runs after the response in TestClient/httpx; poll.
            for _ in range(20):
                detail = await client.get(
                    f"/v1/runs/{run_id}",
                    headers=_engineer_auth(),
                )
                if detail.status_code == 200 and detail.json()["status"] in (
                    "done",
                    "failed",
                ):
                    break
                import asyncio

                await asyncio.sleep(0.1)

    final = detail.json()
    assert final["status"] == "done", final
    assert final["output"] == "echoing payload"
    assert final["tokens_input"] == 12
    assert final["tokens_output"] == 4


def _engineer_auth() -> dict[str, str]:
    from xenia.config import get_settings
    from xenia.security.jwt_auth import issue_token

    token = issue_token(
        sub="tester",
        principal_type="engineer",
        scopes=["runs:read", "runs:create", "runs:cancel", "agents:reload", "dashboard:read"],
        secret=get_settings().jwt_secret,
    )
    return {"Authorization": f"Bearer {token}"}
