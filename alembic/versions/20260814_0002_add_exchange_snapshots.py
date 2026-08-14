"""Add exchange snapshot runs and balances.

Revision ID: 20260814_0002
Revises: 20260813_0001
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260814_0002"
down_revision: str | None = "20260813_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "exchange_snapshot_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("exchange", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_exchange_snapshot_runs_created_at",
        "exchange_snapshot_runs",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_exchange_snapshot_runs_exchange",
        "exchange_snapshot_runs",
        ["exchange"],
        unique=False,
    )
    op.create_index(
        "ix_exchange_snapshot_runs_status",
        "exchange_snapshot_runs",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_exchange_snapshot_runs_user_exchange_created",
        "exchange_snapshot_runs",
        ["user_id", "exchange", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_exchange_snapshot_runs_user_id",
        "exchange_snapshot_runs",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "exchange_balances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("snapshot_run_id", sa.Integer(), nullable=False),
        sa.Column("asset", sa.String(length=32), nullable=False),
        sa.Column("free", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("locked", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("total", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.ForeignKeyConstraint(
            ["snapshot_run_id"],
            ["exchange_snapshot_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "snapshot_run_id",
            "asset",
            name="uq_exchange_balances_run_asset",
        ),
    )
    op.create_index(
        "ix_exchange_balances_asset",
        "exchange_balances",
        ["asset"],
        unique=False,
    )
    op.create_index(
        "ix_exchange_balances_snapshot_run_id",
        "exchange_balances",
        ["snapshot_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_exchange_balances_snapshot_run_id", table_name="exchange_balances")
    op.drop_index("ix_exchange_balances_asset", table_name="exchange_balances")
    op.drop_table("exchange_balances")
    op.drop_index("ix_exchange_snapshot_runs_user_id", table_name="exchange_snapshot_runs")
    op.drop_index(
        "ix_exchange_snapshot_runs_user_exchange_created",
        table_name="exchange_snapshot_runs",
    )
    op.drop_index("ix_exchange_snapshot_runs_status", table_name="exchange_snapshot_runs")
    op.drop_index("ix_exchange_snapshot_runs_exchange", table_name="exchange_snapshot_runs")
    op.drop_index("ix_exchange_snapshot_runs_created_at", table_name="exchange_snapshot_runs")
    op.drop_table("exchange_snapshot_runs")
