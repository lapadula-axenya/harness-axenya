"""Request/response Pydantic models for the HTTP API."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RunCreate(BaseModel):
    payload: dict[str, Any]
    triggered_by: Literal["webhook", "scheduler", "api"] = "api"
    trigger_source: str | None = None


class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: str
    status: str
    input_payload: dict[str, Any]
    output: str | None
    error: str | None
    steps_executed: int
    tokens_input: int
    tokens_output: int
    cost_usd: Decimal
    triggered_by: str
    trigger_source: str | None
    parent_run_id: UUID | None
    langfuse_trace_id: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class RunCreatedResponse(BaseModel):
    run_id: UUID
    status: str
    poll_url: str
    stream_url: str


class RunEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_type: str
    step_number: int
    payload: dict[str, Any]
    created_at: datetime


class AgentSummary(BaseModel):
    id: str
    nome: str
    descricao: str
    enabled: bool
    skills: list[str]
    model: str
    runs_24h: int = 0
    avg_duration_s: float = 0.0
    failure_rate: float = 0.0


class AgentDetail(AgentSummary):
    yaml_hash: str
    system_prompt: str
    input_schema: dict[str, Any]


class AgentToggleRequest(BaseModel):
    enabled: bool


class DashboardSummary(BaseModel):
    runs_today: int
    runs_running: int
    runs_failed_24h: int
    cost_usd_today: Decimal
    failure_rate_24h: float


class DashboardAgent(BaseModel):
    agent_id: str
    runs_24h: int
    cost_usd_24h: Decimal
    last_status: str | None


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None
    field_path: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    env: str = Field(default="dev")
