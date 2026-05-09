"""Ksenia HTTP skill — calls Axenya's internal Ksenia API.

Configured by `KSENIA_API_URL` and `KSENIA_API_TOKEN` (via Secret Manager
or env). Without those, returns NOT_IMPLEMENTED so agents that try to use
Ksenia in dev fail visibly rather than silently mocking real user data.
"""
from __future__ import annotations

import os
from typing import Any

import httpx

from xenia.security.secrets import read_secret
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
    timeout_seconds = 10

    async def execute(self, **kwargs: Any) -> SkillResult:
        user_id = kwargs.get("user_id")
        if not user_id:
            return SkillResult(
                ok=False, error="user_id required", error_code="BAD_INPUT"
            )

        base_url = os.environ.get("KSENIA_API_URL")
        if not base_url:
            return SkillResult(
                ok=False,
                error="KSENIA_API_URL not configured",
                error_code="NOT_CONFIGURED",
            )

        token = read_secret("ksenia_api_token")
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(
                    f"{base_url.rstrip('/')}/users/{user_id}",
                    headers=headers,
                )
        except httpx.HTTPError as exc:
            return SkillResult(
                ok=False, error=str(exc), error_code="KSENIA_UNAVAILABLE"
            )

        if response.status_code == 404:
            return SkillResult(
                ok=False, error=f"user {user_id} not found", error_code="NOT_FOUND"
            )
        if response.status_code >= 400:
            return SkillResult(
                ok=False,
                error=f"ksenia returned {response.status_code}: {response.text[:200]}",
                error_code="KSENIA_HTTP_ERROR",
            )
        return SkillResult(ok=True, data=response.json())


def all_skills() -> list[Skill]:
    return [KseniaReadUser()]
