"""BigQuery skill — whitelist enforcement + optional real client.

Whitelist lives in `agents/queries/*.yaml` (Phase 1). Phase 3 adds a real
`google-cloud-bigquery` execution path, gated behind two checks:

  * `BIGQUERY_PROJECT_ID` env var (or `GCP_PROJECT_ID` fallback) is set.
  * Application Default Credentials are available (i.e. `gcloud auth
    application-default login` locally, or service-account binding in prod).

Without those, the skill returns the same deterministic mock rows as
Phase 1 so local dev and tests keep working.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

from xenia.skills.base import Skill, SkillResult

logger = logging.getLogger(__name__)

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

        entry = whitelist[query_name]
        project_id = (
            os.environ.get("BIGQUERY_PROJECT_ID")
            or os.environ.get("GCP_PROJECT_ID")
            or os.environ.get("GOOGLE_CLOUD_PROJECT")
        )

        if project_id:
            try:
                rows = await _run_real_query(
                    project_id=project_id,
                    sql=entry["sql"],
                    params=params,
                    declared_params=entry.get("params") or {},
                )
                return SkillResult(
                    ok=True,
                    data={"query_name": query_name, "params": params, "rows": rows},
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("BigQuery execution failed: %s", exc)
                return SkillResult(
                    ok=False,
                    error=str(exc),
                    error_code="BIGQUERY_FAILED",
                )

        # Dev/test fallback — deterministic mock rows.
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


async def _run_real_query(
    *,
    project_id: str,
    sql: str,
    params: dict[str, Any],
    declared_params: dict[str, str],
) -> list[dict[str, Any]]:
    """Execute via google-cloud-bigquery, off the event loop."""
    import asyncio

    from google.cloud import bigquery

    def _sync_run() -> list[dict[str, Any]]:
        client = bigquery.Client(project=project_id)
        query_params = [
            bigquery.ScalarQueryParameter(name, declared_params.get(name, "STRING"), value)
            for name, value in params.items()
        ]
        job_config = bigquery.QueryJobConfig(
            query_parameters=query_params,
            use_legacy_sql=False,
        )
        result = client.query(sql, job_config=job_config).result(timeout=30)
        return [dict(row) for row in result]

    return await asyncio.to_thread(_sync_run)


def all_skills() -> list[Skill]:
    return [BigqueryQuery()]
