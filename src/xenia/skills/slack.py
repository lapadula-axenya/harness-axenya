"""Slack skills — MCP-backed when SLACK_MCP_URL is set, mock otherwise."""
from __future__ import annotations

import os
from typing import Any

from xenia.security.secrets import read_secret
from xenia.skills.base import Skill, SkillResult
from xenia.skills.mcp_skill import MCPSkill


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


def _mcp_skills(server_url: str, token: str | None) -> list[Skill]:
    auth = f"Bearer {token}" if token else None
    return [
        MCPSkill(
            name="slack.notify_channel",
            description=SlackNotifyChannel.description,
            input_schema=SlackNotifyChannel.input_schema,
            server_url=server_url,
            remote_tool="post_message",
            auth_header=auth,
        ),
        MCPSkill(
            name="slack.send_dm",
            description=SlackSendDM.description,
            input_schema=SlackSendDM.input_schema,
            server_url=server_url,
            remote_tool="send_dm",
            auth_header=auth,
        ),
    ]


def all_skills() -> list[Skill]:
    server_url = os.environ.get("SLACK_MCP_URL")
    if server_url:
        token = read_secret("slack_mcp_token")
        return _mcp_skills(server_url, token)
    return [SlackNotifyChannel(), SlackSendDM()]
