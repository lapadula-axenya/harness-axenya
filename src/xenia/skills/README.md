# Skills

Skills are atomic operations an agent can call as a tool. Each module
exposes `all_skills() -> list[Skill]` which the central registry pulls at
startup.

## Built-in skills

| Skill | Module | Backends |
|---|---|---|
| `hubspot.get_contact` | `hubspot.py` | MCP (`HUBSPOT_MCP_URL`) → mock |
| `hubspot.update_lead_stage` | `hubspot.py` | MCP → mock |
| `hubspot.add_note` | `hubspot.py` | MCP → mock |
| `slack.notify_channel` | `slack.py` | MCP (`SLACK_MCP_URL`) → mock |
| `slack.send_dm` | `slack.py` | MCP → mock |
| `jira.create_issue` | `jira.py` | MCP (`JIRA_MCP_URL`) → mock |
| `jira.update_issue` | `jira.py` | MCP → mock |
| `bigquery.query` | `bigquery.py` | google-cloud-bigquery (`BIGQUERY_PROJECT_ID`) → mock |
| `ksenia.read_user` | `ksenia.py` | HTTP (`KSENIA_API_URL`) → fails fast (no mock) |

## Adding a new skill

### Option A — wrap an MCP server tool

```python
# src/xenia/skills/myservice.py
from xenia.skills.mcp_skill import MCPSkill
from xenia.skills.base import Skill
import os
from xenia.security.secrets import read_secret

def all_skills() -> list[Skill]:
    server = os.environ.get("MYSERVICE_MCP_URL")
    if not server:
        return [_MyserviceMock()]   # define a mock fallback for dev/tests
    token = read_secret("myservice_mcp_token")
    return [
        MCPSkill(
            name="myservice.do_thing",
            description="...",
            input_schema={...},
            server_url=server,
            remote_tool="do_thing",
            auth_header=f"Bearer {token}" if token else None,
        ),
    ]
```

Then add `myservice` to `_register_builtins` in `base.py`.

### Option B — direct HTTP / Python client

Subclass `Skill` directly and call `httpx`/SDK in `execute`. Always:

* Validate inputs against `input_schema` (Pydantic does this if you pass
  the kwargs through a model).
* Wrap network calls in `httpx.AsyncClient(timeout=self.timeout_seconds)`.
* Map errors to `SkillResult` with a short `error_code` so retry policy
  can reason about them.

## Secrets

All skill secrets go through `xenia.security.secrets.read_secret(name)`.
In dev that reads `os.environ[name.upper()]`; in prod it reads from GCP
Secret Manager (when `GCP_PROJECT_ID` is set). Do NOT hardcode secrets in
YAML or `__init__`.

## BigQuery whitelist

`bigquery.query` rejects arbitrary SQL. Each authorized query lives in
`agents/queries/<name>.yaml`:

```yaml
name: similar_leads
description: ...
sql: |
  SELECT ...
params:
  empresa: STRING
```

Agents pass `query_name` + `params`; never raw SQL.
