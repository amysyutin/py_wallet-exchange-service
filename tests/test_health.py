from collections.abc import Generator
from typing import cast

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db import get_db
from app.main import app


def test_liveness_does_not_require_database(client: TestClient) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "py-wallet-exchange-service"
    assert payload["version"] == "0.1.0"
    assert payload["build_sha"] == "unknown"
    assert payload["database"] is None


def test_readiness_checks_database(client: TestClient) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["database"] == "ok"


def test_health_alias_checks_database(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["database"] == "ok"


def test_readiness_returns_503_when_database_is_unavailable() -> None:
    class UnavailableSession:
        def execute(self, _statement: object) -> None:
            raise OperationalError("SELECT 1", {}, RuntimeError("offline"))

    def unavailable_database() -> Generator[Session, None, None]:
        yield cast(Session, UnavailableSession())

    app.dependency_overrides[get_db] = unavailable_database
    try:
        with TestClient(app) as test_client:
            response = test_client.get("/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "database unavailable"}
