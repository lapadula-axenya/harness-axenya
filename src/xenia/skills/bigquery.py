"""BigQuery skill — Phase 1 mock with whitelist enforcement.

Real `google-cloud-bigquery` calls land in Phase 3. The whitelist mechanic is
already in place so agents authored in Phase 1 stay forward-compatible.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from xenia.skills.base import Skill, SkillResult

_QUERY_DIR = Path("agents/queries")


class BigqueryQuery(Skill):
    name = "bigquery.query"
    description = (
        "Run a parameterised, whitelisted BigQuery query by name. The query_name "
        "must exist under agents/queries/. Arbitrary SQL is rejected."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "required": ["query_name"],
        "properties": {
            "query_name": {
                "type": "string",
                "description": "name of a whitelisted query (file in agents/queries/)",
            },
            "params": {
                "type": "object",
                "description": "named parameters passed to the query",
                "additionalProperties": True,
            },
        },
    }
    idempotent = True

    def __init__(self, query_dir: Path | None = None) -> None:
        self._query_dir = query_dir or _QUERY_DIR

    def _load_whitelist(self) -> dict[str, dict[str, Any]]:
        if not self._query_dir.exists():
            return {}
        out: dict[str, dict[str, Any]] = {}
        for path in self._query_dir.glob("*.yaml"):
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or "name" not in data:
                continue
            out[data["name"]] = data
        return out

    async def execute(self, **kwargs: Any) -> SkillResult:
        query_name = kwargs.get("query_name")
        params = kwargs.get("params") or {}
        if not query_name:
            return SkillResult(
                ok=False, error="query_name required", error_code="BAD_INPUT"
            )

        whitelist = self._load_whitelist()
        if query_name not in whitelist:
            return SkillResult(
                ok=False,
                error=f"query {query_name!r} not in whitelist",
                error_code="QUERY_NOT_WHITELISTED",
            )

        # Phase 1: return a deterministic mock instead of executing SQL.
        return SkillResult(
            ok=True,
            data={
                "query_name": query_name,
                "params": params,
                "rows": [
                    {"empresa": "Mock A", "stage": "sql", "score": 0.81},
                    {"empresa": "Mock B", "stage": "mql", "score": 0.62},
                ],
            },
        )


def all_skills() -> list[Skill]:
    return [BigqueryQuery()]
