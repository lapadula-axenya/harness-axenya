"""Integration test: run + run_events persisted correctly."""
from __future__ import annotations

import pytest

from xenia.executor.executor import run_agent
from xenia.llm.client import LLMResponse, ToolUse
from xenia.skills.base import SkillRegistry
from xenia.skills.hubspot import HubspotGetContact
from xenia.storage.repositories import RunEventRepository, RunRepository

pytestmark = pytest.mark.integration


class _StubLLM:
    def __init__(self, responses):
        self._r = list(responses)

    async def complete(self, **kwargs):
        return self._r.pop(0)


async def test_run_persists_with_events(db_session):
    # Persist a queued run via the repository
    from xenia.storage.db import get_sessionmaker
    from xenia.storage.models import RunStatus

    sm = get_sessionmaker()
    async with sm() as session:
        # Ensure agent row exists
        from xenia.storage.repositories import AgentRepository

        await AgentRepository(session).upsert(
            agent_id="exemplo_eco",
            nome="Exemplo Echo",
            descricao="seed",
            yaml_hash="x",
            yaml_content="x",
        )
        run = await RunRepository(session).create(
            agent_id="exemplo_eco",
            input_payload={"foo": "bar"},
            triggered_by="api",
            trigger_source=None,
            timeout_seconds=60,
        )
        await session.commit()
        run_id = run.id

    # Build agent definition + skills + LLM stub
    from xenia.agents.definition import AgentDefinition, ExecutionConfig, LLMConfig

    definition = AgentDefinition(
        id="exemplo_eco",
        nome="Exemplo Echo",
        descricao="seed",
        webhook_secret_env="WEBHOOK_SECRET_EXEMPLO_ECO",
        input_schema={"type": "object", "required": ["foo"], "properties": {"foo": {"type": "string"}}},
        llm=LLMConfig(provider="anthropic", model="claude-sonnet-4-6"),
        skills=["hubspot.get_contact"],
        system_prompt="x",
        execution=ExecutionConfig(max_steps=3, timeout_seconds=10),
    )

    skills = SkillRegistry()
    skills.register(HubspotGetContact())

    llm = _StubLLM(
        [
            LLMResponse(
                tool_uses=[
                    ToolUse(
                        id="tu_1",
                        name="hubspot.get_contact",
                        input={"contact_id": "c1"},
                    )
                ],
                stop_reason="tool_use",
                tokens_input=10,
                tokens_output=2,
            ),
            LLMResponse(text="done", stop_reason="end_turn", tokens_input=5, tokens_output=1),
        ]
    )

    outcome = await run_agent(
        run_id=run_id,
        definition=definition,
        payload={"foo": "bar"},
        llm_client=llm,
        skill_registry=skills,
    )
    assert outcome.error is None
    assert outcome.output == "done"

    async with sm() as session:
        run = await RunRepository(session).get(run_id)
        assert run is not None
        assert run.status == RunStatus.done
        assert run.output == "done"
        events = await RunEventRepository(session).list_for_run(run_id)
        types = [e.event_type for e in events]
        assert "step_start" in types
        assert "tool_call" in types
        assert "tool_result" in types
        assert "llm_response" in types
        assert "completed" in types
