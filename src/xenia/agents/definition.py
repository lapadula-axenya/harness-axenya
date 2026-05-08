"""Pydantic models that describe an agent definition (parsed from YAML)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

LLMProvider = Literal["anthropic", "omnirouter"]
NodeType = Literal["llm_call", "tool_call", "human_input", "branch"]


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: LLMProvider = "anthropic"
    model: str
    max_tokens: int = Field(default=1024, gt=0, le=200_000)
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)


class ExecutionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_steps: int = Field(default=10, ge=1, le=100)
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
    retry_on_failure: int = Field(default=2, ge=0, le=10)
    retry_backoff_seconds: int = Field(default=30, ge=0, le=600)


class GraphNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: NodeType
    prompt: str | None = None
    tool: str | None = None
    condition: str | None = None


class GraphEdge(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    from_: str = Field(alias="from")
    to: str
    condition: str | None = None


class GraphConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nodes: list[GraphNode]
    edges: list[GraphEdge]


class AgentDefinition(BaseModel):
    """In-memory representation of one agents/*.yaml file."""

    model_config = ConfigDict(extra="forbid")

    id: str
    nome: str
    descricao: str
    webhook_secret_env: str
    input_schema: dict[str, Any]
    llm: LLMConfig
    skills: list[str] = Field(default_factory=list)
    system_prompt: str
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    graph: GraphConfig | None = None
    enabled: bool = True

    @field_validator("id")
    @classmethod
    def _id_snake_case(cls, v: str) -> str:
        if not v or not all(c.islower() or c.isdigit() or c == "_" for c in v):
            raise ValueError(f"agent id must be snake_case: {v!r}")
        return v

    @field_validator("input_schema")
    @classmethod
    def _input_schema_is_object(cls, v: dict[str, Any]) -> dict[str, Any]:
        if v.get("type") != "object":
            raise ValueError("input_schema must be a JSON Schema with type=object")
        return v
