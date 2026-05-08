"""Slack skills — Phase 1 in-memory mocks."""
from __future__ import annotations

from typing import Any

from xenia.skills.base import Skill, SkillResult


class SlackNotifyChannel(Skill):
    name = "slack.notify_channel"
    description = "Post a message to a Slack channel."
    input_schema: dict[str, Any] = {
        "type": "object",
        "required": ["channel", "message"],
        "properties": {
            "channel": {"type": "string", "description": "channel name with #"},
            "message": {"type": "string"},
        },
    }
    idempotent = False

    async def execute(self, **kwargs: Any) -> SkillResult:
        return SkillResult(
            ok=True,
            data={
                "channel": kwargs.get("channel"),
                "ts": "1730000000.000100",
                "delivered": True,
            },
        )


class SlackSendDM(Skill):
    name = "slack.send_dm"
    description = "Send a direct message to a Slack user."
    input_schema: dict[str, Any] = {
        "type": "object",
        "required": ["user_id", "message"],
        "properties": {
            "user_id": {"type": "string"},
            "message": {"type": "string"},
        },
    }
    idempotent = False

    async def execute(self, **kwargs: Any) -> SkillResult:
        return SkillResult(
            ok=True,
            data={"user_id": kwargs.get("user_id"), "delivered": True},
        )


def all_skills() -> list[Skill]:
    return [SlackNotifyChannel(), SlackSendDM()]
