"""Ksenia HTTP skills — Phase 3 stub.

Stubbed out so the import chain is clean; real HTTP calls land in Phase 3.
"""
from __future__ import annotations

from typing import Any

from xenia.skills.base import Skill, SkillResult


class KseniaReadUser(Skill):
    name = "ksenia.read_user"
    description = "Read a Ksenia user record (Axenya internal HTTP)."
    input_schema: dict[str, Any] = {
        "type": "object",
        "required": ["user_id"],
        "properties": {"user_id": {"type": "string"}},
    }
    idempotent = True

    async def execute(self, **kwargs: Any) -> SkillResult:
        return SkillResult(
            ok=False,
            error="ksenia.read_user not implemented in Phase 1",
            error_code="NOT_IMPLEMENTED",
        )


def all_skills() -> list[Skill]:
    return [KseniaReadUser()]
