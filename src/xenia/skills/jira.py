"""Jira (Atlassian) skills — MCP-backed when JIRA_MCP_URL is set."""
from __future__ import annotations

import os
from typing import Any

from xenia.security.secrets import read_secret
from xenia.skills.base import Skill, SkillResult
from xenia.skills.mcp_skill import MCPSkill


class JiraCreateIssue(Skill):
    name = "jira.create_issue"
    description = "Create a Jira issue."
    input_schema: dict[str, Any] = {
        "type": "object",
        "required": ["project_key", "summary"],
        "properties": {
            "project_key": {"type": "string"},
            "summary": {"type": "string"},
            "description": {"type": "string"},
            "issue_type": {"type": "string", "default": "Task"},
        },
    }
    idempotent = False

    async def execute(self, **kwargs: Any) -> SkillResult:
        # Mock fallback for environments without the Jira MCP server.
        return SkillResult(
            ok=True,
            data={
                "key": f"{kwargs.get('project_key', 'DEMO')}-9999",
                "summary": kwargs.get("summary"),
                "created": True,
            },
        )


class JiraUpdateIssue(Skill):
    name = "jira.update_issue"
    description = "Update an existing Jira issue."
    input_schema: dict[str, Any] = {
        "type": "object",
        "required": ["issue_key"],
        "properties": {
            "issue_key": {"type": "string"},
            "status": {"type": "string"},
            "comment": {"type": "string"},
        },
    }
    idempotent = True

    async def execute(self, **kwargs: Any) -> SkillResult:
        return SkillResult(
            ok=True,
            data={"issue_key": kwargs.get("issue_key"), "updated": True},
        )


def _mcp_skills(server_url: str, token: str | None) -> list[Skill]:
    auth = f"Bearer {token}" if token else None
    return [
        MCPSkill(
            name="jira.create_issue",
            description=JiraCreateIssue.description,
            input_schema=JiraCreateIssue.input_schema,
            server_url=server_url,
            remote_tool="create_issue",
            auth_header=auth,
        ),
        MCPSkill(
            name="jira.update_issue",
            description=JiraUpdateIssue.description,
            input_schema=JiraUpdateIssue.input_schema,
            server_url=server_url,
            remote_tool="update_issue",
            auth_header=auth,
            idempotent=True,
        ),
    ]


def all_skills() -> list[Skill]:
    server_url = os.environ.get("JIRA_MCP_URL")
    if server_url:
        token = read_secret("jira_mcp_token")
        return _mcp_skills(server_url, token)
    return [JiraCreateIssue(), JiraUpdateIssue()]
