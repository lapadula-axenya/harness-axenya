"""Unit tests for built-in skills + registry."""
from __future__ import annotations

from pathlib import Path

import pytest

from xenia.skills.base import SkillRegistry, get_skill_registry, reset_skill_registry
from xenia.skills.bigquery import BigqueryQuery
from xenia.skills.hubspot import HubspotGetContact, HubspotUpdateLeadStage


def test_global_registry_has_builtins():
    reset_skill_registry()
    registry = get_skill_registry()
    names = registry.names()
    for expected in [
        "hubspot.get_contact",
        "hubspot.update_lead_stage",
        "hubspot.add_note",
        "slack.notify_channel",
        "slack.send_dm",
        "bigquery.query",
    ]:
        assert expected in names


def test_register_duplicate_raises():
    registry = SkillRegistry()
    registry.register(HubspotGetContact())
    with pytest.raises(ValueError):
        registry.register(HubspotGetContact())


async def test_hubspot_get_contact_returns_mock_payload():
    skill = HubspotGetContact()
    result = await skill.execute(contact_id="123")
    assert result.ok is True
    assert result.data is not None
    assert result.data["id"] == "123"


async def test_hubspot_update_lead_stage_echoes_input():
    skill = HubspotUpdateLeadStage()
    result = await skill.execute(contact_id="42", stage="sql")
    assert result.ok and result.data == {
        "contact_id": "42",
        "stage": "sql",
        "updated": True,
    }


async def test_bigquery_rejects_unknown_query(tmp_path: Path):
    skill = BigqueryQuery(query_dir=tmp_path)
    result = await skill.execute(query_name="nonexistent")
    assert result.ok is False
    assert result.error_code == "QUERY_NOT_WHITELISTED"


async def test_bigquery_rejects_missing_query_name(tmp_path: Path):
    skill = BigqueryQuery(query_dir=tmp_path)
    result = await skill.execute()
    assert result.ok is False
    assert result.error_code == "BAD_INPUT"


async def test_bigquery_accepts_whitelisted_query(tmp_path: Path):
    (tmp_path / "demo.yaml").write_text(
        "name: demo\ndescription: x\nsql: 'SELECT 1'\nparams: {}\n",
        encoding="utf-8",
    )
    skill = BigqueryQuery(query_dir=tmp_path)
    result = await skill.execute(query_name="demo", params={"empresa": "Acme"})
    assert result.ok is True
    assert result.data is not None
    assert result.data["query_name"] == "demo"


def test_tool_schema_shape():
    skill = HubspotGetContact()
    schema = skill.to_tool_schema()
    assert schema["name"] == "hubspot.get_contact"
    assert "input_schema" in schema
    assert schema["input_schema"]["type"] == "object"


def test_registry_tools_for_returns_subset():
    reset_skill_registry()
    registry = get_skill_registry()
    tools = registry.tools_for(["hubspot.get_contact", "slack.notify_channel"])
    assert {t["name"] for t in tools} == {
        "hubspot.get_contact",
        "slack.notify_channel",
    }
