"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-08

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute(
        "CREATE TYPE run_status AS ENUM "
        "('queued', 'running', 'paused', 'done', 'failed', 'cancelled')"
    )

    op.create_table(
        "agents",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("yaml_hash", sa.String(64), nullable=False),
        sa.Column("yaml_content", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "agent_id",
            sa.String(64),
            sa.ForeignKey("agents.id"),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(name="run_status", create_type=False),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("input_payload", postgresql.JSONB(), nullable=False),
        sa.Column("output", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("error_class", sa.String(128), nullable=True),
        sa.Column(
            "steps_executed", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("tokens_input", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_output", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "cost_usd",
            sa.Numeric(10, 6),
            nullable=False,
            server_default="0",
        ),
        sa.Column("triggered_by", sa.String(32), nullable=False),
        sa.Column("trigger_source", sa.String(255), nullable=True),
        sa.Column(
            "parent_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("runs.id"),
            nullable=True,
        ),
        sa.Column("langfuse_trace_id", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timeout_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_runs_agent_id", "runs", ["agent_id"])
    op.create_index("idx_runs_status", "runs", ["status"])
    op.create_index(
        "idx_runs_created_at", "runs", [sa.text("created_at DESC")]
    )
    op.create_index(
        "idx_runs_status_timeout",
        "runs",
        ["status", "timeout_at"],
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )

    op.create_table(
        "run_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_run_events_run_id", "run_events", ["run_id", "created_at"])

    op.create_table(
        "webhook_secrets",
        sa.Column(
            "agent_id",
            sa.String(64),
            sa.ForeignKey("agents.id"),
            primary_key=True,
        ),
        sa.Column("secret_hash", sa.String(128), nullable=False),
        sa.Column(
            "secret_version", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("webhook_secrets")
    op.drop_index("idx_run_events_run_id", table_name="run_events")
    op.drop_table("run_events")
    op.drop_index("idx_runs_status_timeout", table_name="runs")
    op.drop_index("idx_runs_created_at", table_name="runs")
    op.drop_index("idx_runs_status", table_name="runs")
    op.drop_index("idx_runs_agent_id", table_name="runs")
    op.drop_table("runs")
    op.drop_table("agents")
    op.execute("DROP TYPE run_status")
