from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.auth import require_internal_token
from app.config import Settings, get_settings
from app.connectors.binance import BinanceConnector
from app.db import get_db
from app.schemas.exchanges import ExchangeSnapshotCreate, ExchangeSnapshotResponse
from app.services.exchange_snapshots import ExchangeSnapshotService, ExchangeSnapshotSyncError

router = APIRouter(
    prefix="/internal/exchange-snapshots",
    tags=["internal exchange snapshots"],
    dependencies=[Depends(require_internal_token)],
)
DatabaseSession = Annotated[Session, Depends(get_db)]


def get_binance_connector(settings: Annotated[Settings, Depends(get_settings)]) -> BinanceConnector:
    return BinanceConnector(
        api_key=settings.binance_api_key,
        api_secret=settings.binance_api_secret,
        base_url=settings.binance_base_url,
        timeout_seconds=settings.binance_timeout_seconds,
        recv_window_ms=settings.binance_recv_window_ms,
    )


@router.post(
    "/binance",
    response_model=ExchangeSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
def sync_binance_snapshot(
    payload: ExchangeSnapshotCreate,
    database: DatabaseSession,
    connector: Annotated[BinanceConnector, Depends(get_binance_connector)],
) -> ExchangeSnapshotResponse:
    try:
        snapshot_run = ExchangeSnapshotService(database).sync_binance(
            user_id=payload.user_id,
            connector=connector,
        )
    except ExchangeSnapshotSyncError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "binance sync failed",
                "run_id": error.run_id,
                "error_code": error.code,
            },
        ) from error
    return ExchangeSnapshotResponse.model_validate(snapshot_run)


@router.get("/latest", response_model=ExchangeSnapshotResponse)
def latest_exchange_snapshot(
    database: DatabaseSession,
    user_id: Annotated[int, Query(gt=0)],
) -> ExchangeSnapshotResponse:
    snapshot_run = ExchangeSnapshotService(database).get_latest_successful(user_id=user_id)
    if snapshot_run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="exchange snapshot not found",
        )
    return ExchangeSnapshotResponse.model_validate(snapshot_run)
