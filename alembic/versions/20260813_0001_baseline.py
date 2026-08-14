"""Establish the exchange service migration baseline.

Revision ID: 20260813_0001
Revises:
Create Date: 2026-08-13
"""

from collections.abc import Sequence

revision: str = "20260813_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Reserve a baseline before exchange-owned tables are introduced."""


def downgrade() -> None:
    """Remove the empty baseline."""
