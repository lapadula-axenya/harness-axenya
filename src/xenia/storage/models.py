"""SQLAlchemy 2.0 ORM models — schema mirrors migration 001."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class RunStatus(enum.StrEnum):
    queued = "queued"
    running = "running"
    paused = "paused"
    done = "done"
    failed = "failed"
    cancelled = "cancelled"


# Postgres-side type matches the enum created in migration 001. We disable
# CREATE/DROP here because the migration owns the type lifecycle.
_run_status_pg = ENUM(
    RunStatus,
    name="run_status",
    create_type=False,
    values_callable=lambda enum_cls: [m.value for m in enum_cls],
)


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    yaml_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    yaml_content: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    runs: Mapped[list[Run]] = relationship(back_populates="agent")


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("agents.id"), nullable=False, index=True
    )
    status: Mapped[RunStatus] = mapped_column(
        _run_status_pg, nullable=False, default=RunStatus.queued
    )
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    output: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_class: Mapped[str | None] = mapped_column(String(128), nullable=True)
    steps_executed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_input: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_output: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, default=Decimal("0")
    )
    triggered_by: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id"), nullable=True
    )
    langfuse_trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    timeout_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    agent: Mapped[Agent] = relationship(back_populates="runs")
    events: Mapped[list[RunEvent]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class RunEvent(Base):
    __tablename__ = "run_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    run: Mapped[Run] = relationship(back_populates="events")


class ProcessStatus(enum.StrEnum):
    active = "active"
    paused = "paused"
    archived = "archived"


class ProcessTargetKind(enum.StrEnum):
    agent = "agent"
    mission = "mission"
    worker = "worker"


class ProcessLastStatus(enum.StrEnum):
    ok = "ok"
    partial = "partial"
    failed = "failed"


_process_status_pg = ENUM(
    ProcessStatus,
    name="process_status",
    create_type=False,
    values_callable=lambda enum_cls: [m.value for m in enum_cls],
)

_process_target_kind_pg = ENUM(
    ProcessTargetKind,
    name="process_target_kind",
    create_type=False,
    values_callable=lambda enum_cls: [m.value for m in enum_cls],
)

_process_last_status_pg = ENUM(
    ProcessLastStatus,
    name="process_last_status",
    create_type=False,
    values_callable=lambda enum_cls: [m.value for m in enum_cls],
)


class Process(Base):
    __tablename__ = "processes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    cron_expression: Mapped[str] = mapped_column(Text, nullable=False)
    schedule_human: Mapped[str] = mapped_column(Text, nullable=False, default="")
    target_kind: Mapped[ProcessTargetKind] = mapped_column(
        _process_target_kind_pg, nullable=False
    )
    target_ref: Mapped[str] = mapped_column(Text, nullable=False)
    target_label: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    owner_name: Mapped[str] = mapped_column(Text, nullable=False)
    owner_initials: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[ProcessStatus] = mapped_column(
        _process_status_pg, nullable=False, default=ProcessStatus.active
    )
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_run_status: Mapped[ProcessLastStatus | None] = mapped_column(
        _process_last_status_pg, nullable=True
    )
    last_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    success_rate_30d: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0")
    )
    runs_30d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class WebhookSecret(Base):
    __tablename__ = "webhook_secrets"

    agent_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("agents.id"), primary_key=True
    )
    secret_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    secret_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    rotated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
