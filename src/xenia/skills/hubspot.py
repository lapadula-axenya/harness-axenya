"""HubSpot skills.

Two modes selected by env:

  * `HUBSPOT_MCP_URL` set → MCP-backed skills against the HubSpot MCP
    server (production path).
  * Unset → in-memory mocks (Phase 1 dev path, kept so local + tests
    work without external creds).

Phase 1 acceptance and Phase 3 acceptance both call `all_skills()` —
the function transparently picks the mode at registration time.
"""
from __future__ import annotations

import os
from typing import Any

from xenia.security.secrets import read_secret
from xenia.skills.base import Skill, SkillResult
from xenia.skills.mcp_skill import MCPSkill

# ── Mocks ────────────────────────────────────────────────────────────────


class HubspotGetContact(Skill):
    name = "hubspot.get_contact"
    description = "Read a HubSpot contact by id."
    input_schema: dict[str, Any] = {
        "type": "object",
        "required": ["contact_id"],
        "properties": {
            "contact_id": {"type": "string", "description": "HubSpot contact id"},
        },
    }
    idempotent = True

    async def execute(self, **kwargs: Any) -> SkillResult:
        contact_id = kwargs.get("contact_id")
        if not contact_id:
            return SkillResult(
                ok=False, error="contact_id required", error_code="BAD_INPUT"
            )
        return SkillResult(
            ok=True,
            data={
                "id": contact_id,
                "empresa": "Mock Co.",
                "setor": "saude",
                "stage": "lead",
            },
        )


class HubspotUpdateLeadStage(Skill):
    name = "hubspot.update_lead_stage"
    description = "Update the lifecycle stage of a HubSpot contact."
    input_schema: dict[str, Any] = {
        "type": "object",
        "required": ["contact_id", "stage"],
        "properties": {
            "contact_id": {"type": "string"},
            "stage": {
                "type": "string",
                "enum": ["lead", "mql", "sql", "opportunity", "customer"],
            },
        },
    }
    idempotent = True

    async def execute(self, **kwargs: Any) -> SkillResult:
        return SkillResult(
            ok=True,
            data={
                "contact_id": kwargs.get("contact_id"),
                "stage": kwargs.get("stage"),
                "updated": True,
            },
        )


class HubspotAddNote(Skill):
    name = "hubspot.add_note"
    description = "Append a note to a HubSpot contact."
    input_schema: dict[str, Any] = {
        "type": "object",
        "required": ["contact_id", "note"],
        "properties": {
            "contact_id": {"type": "string"},
            "note": {"type": "string"},
        },
    }
    idempotent = False

    async def execute(self, **kwargs: Any) -> SkillResult:
        return SkillResult(
            ok=True,
            data={"contact_id": kwargs.get("contact_id"), "note_added": True},
        )


# ── Real (MCP) ───────────────────────────────────────────────────────────


def _mcp_skills(server_url: str, token: str | None) -> list[Skill]:
    auth = f"Bearer {token}" if token else None
    return [
        MCPSkill(
            name="hubspot.get_contact",
            description=HubspotGetContact.description,
            input_schema=HubspotGetContact.input_schema,
            server_url=server_url,
            remote_tool="get_contact",
            auth_header=auth,
            idempotent=True,
        ),
        MCPSkill(
            name="hubspot.update_lead_stage",
            description=HubspotUpdateLeadStage.description,
            input_schema=HubspotUpdateLeadStage.input_schema,
            server_url=server_url,
            remote_tool="update_lifecycle_stage",
            auth_header=auth,
            idempotent=True,
        ),
        MCPSkill(
            name="hubspot.add_note",
            description=HubspotAddNote.description,
            input_schema=HubspotAddNote.input_schema,
            server_url=server_url,
            remote_tool="add_note",
            auth_header=auth,
        ),
    ]


def all_skills() -> list[Skill]:
    server_url = os.environ.get("HUBSPOT_MCP_URL")
    if server_url:
        token = read_secret("hubspot_mcp_token")
        return _mcp_skills(server_url, token)
    return [HubspotGetContact(), HubspotUpdateLeadStage(), HubspotAddNote()]
