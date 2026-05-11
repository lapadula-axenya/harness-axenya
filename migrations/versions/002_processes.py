"""processes (scheduled crons)

Revision ID: 002
Revises: 001
Create Date: 2026-05-11

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE process_status AS ENUM ('active', 'paused', 'archived')"
    )
    op.execute(
        "CREATE TYPE process_target_kind AS ENUM ('agent', 'mission', 'worker')"
    )
    op.execute(
        "CREATE TYPE process_last_status AS ENUM ('ok', 'partial', 'failed')"
    )

    op.create_table(
        "processes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("cron_expression", sa.Text(), nullable=False),
        sa.Column("schedule_human", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "target_kind",
            postgresql.ENUM(
                "agent",
                "mission",
                "worker",
                name="process_target_kind",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("target_ref", sa.Text(), nullable=False),
        sa.Column("target_label", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("owner_name", sa.Text(), nullable=False),
        sa.Column("owner_initials", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "status",
            postgresql.ENUM(
                "active", "paused", "archived", name="process_status", create_type=False
            ),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_run_status",
            postgresql.ENUM(
                "ok", "partial", "failed", name="process_last_status", create_type=False
            ),
            nullable=True,
        ),
        sa.Column(
            "last_run_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "success_rate_30d",
            sa.Numeric(5, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "runs_30d", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
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

    op.create_index(
        "processes_status_next_run_idx",
        "processes",
        ["status", "next_run_at"],
    )


def downgrade() -> None:
    op.drop_index("processes_status_next_run_idx", table_name="processes")
    op.drop_table("processes")
    op.execute("DROP TYPE process_last_status")
    op.execute("DROP TYPE process_target_kind")
    op.execute("DROP TYPE process_status")
