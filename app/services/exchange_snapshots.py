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

        snapshot_run.balances = [
            ExchangeBalance(
                asset=balance.asset,
                free=balance.free,
                locked=balance.locked,
                total=balance.total,
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
