from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.enums import ExchangeName, ExchangeSnapshotStatus


class ExchangeSnapshotRun(Base):
    __tablename__ = "exchange_snapshot_runs"
    __table_args__ = (
        Index(
            "ix_exchange_snapshot_runs_user_exchange_created",
            "user_id",
            "exchange",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    exchange: Mapped[str] = mapped_column(
        String(32), index=True, default=ExchangeName.BINANCE.value
    )
    status: Mapped[str] = mapped_column(
        String(32), index=True, default=ExchangeSnapshotStatus.PENDING.value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(64))

    balances: Mapped[list["ExchangeBalance"]] = relationship(
        back_populates="snapshot_run",
        cascade="all, delete-orphan",
        order_by="ExchangeBalance.asset",
    )


class ExchangeBalance(Base):
    __tablename__ = "exchange_balances"
    __table_args__ = (
        UniqueConstraint("snapshot_run_id", "asset", name="uq_exchange_balances_run_asset"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_run_id: Mapped[int] = mapped_column(
        ForeignKey("exchange_snapshot_runs.id", ondelete="CASCADE"), index=True
    )
    asset: Mapped[str] = mapped_column(String(32), index=True)
    free: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    locked: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    total: Mapped[Decimal] = mapped_column(Numeric(38, 18))

    snapshot_run: Mapped[ExchangeSnapshotRun] = relationship(back_populates="balances")
