from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api.internal_exchange_snapshots import get_binance_connector
from app.connectors.binance import BinanceConnectorError, SpotBalance
from app.main import app
from app.models.exchanges import ExchangeSnapshotRun

INTERNAL_HEADERS = {"X-Internal-Token": "test-internal-token"}


class SuccessfulBinanceConnector:
    def fetch_spot_balances(self) -> tuple[SpotBalance, ...]:
        return (
            SpotBalance(asset="BTC", free=Decimal("0.5"), locked=Decimal("0.25")),
            SpotBalance(asset="USDT", free=Decimal("125"), locked=Decimal("0")),
        )


class FailingBinanceConnector:
    def fetch_spot_balances(self) -> tuple[SpotBalance, ...]:
        raise BinanceConnectorError("rate_limited")


@pytest.mark.parametrize("headers", [{}, {"X-Internal-Token": "wrong-token"}])
def test_internal_endpoints_require_token(
    client: TestClient,
    headers: dict[str, str],
) -> None:
    response = client.get(
        "/internal/exchange-snapshots/latest",
        headers=headers,
        params={"user_id": 7},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid internal token"}


def test_sync_persists_balances_and_latest_is_user_scoped(client: TestClient) -> None:
    app.dependency_overrides[get_binance_connector] = SuccessfulBinanceConnector

    created = client.post(
        "/internal/exchange-snapshots/binance",
        headers=INTERNAL_HEADERS,
        json={"user_id": 7},
    )
    latest = client.get(
        "/internal/exchange-snapshots/latest",
        headers=INTERNAL_HEADERS,
        params={"user_id": 7},
    )
    missing = client.get(
        "/internal/exchange-snapshots/latest",
        headers=INTERNAL_HEADERS,
        params={"user_id": 8},
    )

    assert created.status_code == 201
    assert created.json()["exchange"] == "binance"
    assert created.json()["status"] == "success"
    assert created.json()["balances"] == [
        {"asset": "BTC", "free": "0.5", "locked": "0.25", "total": "0.75"},
        {"asset": "USDT", "free": "125", "locked": "0", "total": "125"},
    ]
    assert latest.status_code == 200
    assert latest.json()["id"] == created.json()["id"]
    assert missing.status_code == 404


def test_failed_sync_is_persisted_without_provider_message(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    app.dependency_overrides[get_binance_connector] = FailingBinanceConnector

    response = client.post(
        "/internal/exchange-snapshots/binance",
        headers=INTERNAL_HEADERS,
        json={"user_id": 9},
    )

    assert response.status_code == 502
    assert response.json()["detail"]["message"] == "binance sync failed"
    assert response.json()["detail"]["error_code"] == "rate_limited"
    with session_factory() as database:
        snapshot_run = database.scalar(select(ExchangeSnapshotRun))
        assert snapshot_run is not None
        assert snapshot_run.status == "failed"
        assert snapshot_run.error_code == "rate_limited"


def test_internal_api_rejects_invalid_user_id(client: TestClient) -> None:
    response = client.post(
        "/internal/exchange-snapshots/binance",
        headers=INTERNAL_HEADERS,
        json={"user_id": 0},
    )

    assert response.status_code == 422
