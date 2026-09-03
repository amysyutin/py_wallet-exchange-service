"""Add timestamped USD valuations to exchange balances.

Revision ID: 20260903_0003
Revises: 20260814_0002
Create Date: 2026-09-03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260903_0003"
down_revision: str | None = "20260814_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "exchange_balances",
        sa.Column("price_usd", sa.Numeric(precision=38, scale=18), nullable=True),
    )
    op.add_column(
        "exchange_balances",
        sa.Column("usd_value", sa.Numeric(precision=38, scale=18), nullable=True),
    )
    op.add_column(
        "exchange_balances",
        sa.Column("price_source", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("exchange_balances", "price_source")
    op.drop_column("exchange_balances", "usd_value")
    op.drop_column("exchange_balances", "price_usd")
