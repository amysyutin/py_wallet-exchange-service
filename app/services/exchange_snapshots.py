from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.connectors.binance import BinanceConnector, BinanceConnectorError
from app.enums import ExchangeName, ExchangeSnapshotStatus
from app.models.exchanges import ExchangeBalance, ExchangeSnapshotRun


class ExchangeSnapshotSyncError(RuntimeError):
    def __init__(self, *, run_id: int, code: str) -> None:
        super().__init__(code)
        self.run_id = run_id
        self.code = code


class ExchangeSnapshotService:
    def __init__(self, database: Session) -> None:
        self.database = database

    def sync_binance(self, *, user_id: int, connector: BinanceConnector) -> ExchangeSnapshotRun:
        snapshot_run = ExchangeSnapshotRun(
            user_id=user_id,
            exchange=ExchangeName.BINANCE.value,
            status=ExchangeSnapshotStatus.PENDING.value,
        )
        self.database.add(snapshot_run)
        self.database.commit()
        self.database.refresh(snapshot_run)

        try:
            balances = connector.fetch_spot_balances()
        except BinanceConnectorError as error:
            snapshot_run.status = ExchangeSnapshotStatus.FAILED.value
            snapshot_run.completed_at = datetime.now(UTC)
            snapshot_run.error_code = error.code
            self.database.commit()
            raise ExchangeSnapshotSyncError(run_id=snapshot_run.id, code=error.code) from error

        try:
            prices = connector.fetch_usdt_prices(tuple(balance.asset for balance in balances))
        except BinanceConnectorError:
            prices = {}

        snapshot_run.balances = [
            ExchangeBalance(
                asset=balance.asset,
                free=balance.free,
                locked=balance.locked,
                total=balance.total,
                price_usd=prices.get(balance.asset),
                usd_value=(
                    balance.total * prices[balance.asset] if balance.asset in prices else None
                ),
                price_source=("binance_usdt" if balance.asset in prices else None),
            )
            for balance in balances
        ]
        snapshot_run.status = ExchangeSnapshotStatus.SUCCESS.value
        snapshot_run.completed_at = datetime.now(UTC)
        self.database.commit()
        return self.get_run(snapshot_run.id)

    def get_run(self, run_id: int) -> ExchangeSnapshotRun:
        snapshot_run = self.database.scalar(
            select(ExchangeSnapshotRun)
            .options(selectinload(ExchangeSnapshotRun.balances))
            .where(ExchangeSnapshotRun.id == run_id)
        )
        if snapshot_run is None:
            raise LookupError("exchange snapshot run not found")
        return snapshot_run

    def get_latest_successful(self, *, user_id: int) -> ExchangeSnapshotRun | None:
        return self.database.scalar(
            select(ExchangeSnapshotRun)
            .options(selectinload(ExchangeSnapshotRun.balances))
            .where(
                ExchangeSnapshotRun.user_id == user_id,
                ExchangeSnapshotRun.exchange == ExchangeName.BINANCE.value,
                ExchangeSnapshotRun.status == ExchangeSnapshotStatus.SUCCESS.value,
            )
            .order_by(ExchangeSnapshotRun.created_at.desc(), ExchangeSnapshotRun.id.desc())
            .limit(1)
        )

    def get_history(
        self,
        *,
        user_id: int,
        since: datetime,
        limit: int,
    ) -> list[ExchangeSnapshotRun]:
        seed = self.database.scalar(
            select(ExchangeSnapshotRun)
            .options(selectinload(ExchangeSnapshotRun.balances))
            .where(
                ExchangeSnapshotRun.user_id == user_id,
                ExchangeSnapshotRun.exchange == ExchangeName.BINANCE.value,
                ExchangeSnapshotRun.status == ExchangeSnapshotStatus.SUCCESS.value,
                ExchangeSnapshotRun.completed_at < since,
            )
            .order_by(
                ExchangeSnapshotRun.completed_at.desc(),
                ExchangeSnapshotRun.id.desc(),
            )
            .limit(1)
        )
        row_limit = limit - 1 if seed is not None else limit
        rows = list(
            self.database.scalars(
                select(ExchangeSnapshotRun)
                .options(selectinload(ExchangeSnapshotRun.balances))
                .where(
                    ExchangeSnapshotRun.user_id == user_id,
                    ExchangeSnapshotRun.exchange == ExchangeName.BINANCE.value,
                    ExchangeSnapshotRun.status == ExchangeSnapshotStatus.SUCCESS.value,
                    ExchangeSnapshotRun.completed_at >= since,
                )
                .order_by(
                    ExchangeSnapshotRun.completed_at.desc(),
                    ExchangeSnapshotRun.id.desc(),
                )
                .limit(row_limit)
            )
        )
        rows.reverse()
        return ([seed] if seed is not None else []) + rows
