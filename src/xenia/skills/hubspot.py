"""HubSpot skills — Phase 1 in-memory mocks.

Real MCP-backed implementations land in Phase 3. The mocks return deterministic
shapes so end-to-end webhook tests can exercise the full agent loop.
"""
from __future__ import annotations

from typing import Any

from xenia.skills.base import Skill, SkillResult


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


def all_skills() -> list[Skill]:
    return [HubspotGetContact(), HubspotUpdateLeadStage(), HubspotAddNote()]
