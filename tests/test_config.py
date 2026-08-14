import pytest
from pydantic import ValidationError
from pytest import MonkeyPatch

from app.config import Settings


def test_settings_accept_environment_overrides(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("EXCHANGE_SERVICE_PORT", "9002")
    monkeypatch.setenv("INTERNAL_API_TOKEN", "test-internal-token")

    settings = Settings()

    assert settings.environment == "test"
    assert settings.exchange_service_port == 9002


def test_settings_ignore_unknown_environment_variables(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("EXCHANGE_UNKNOWN_SETTING", "ignored")
    monkeypatch.setenv("INTERNAL_API_TOKEN", "test-internal-token")

    settings = Settings()

    assert settings.app_name == "py-wallet-exchange-service"


def test_settings_require_internal_token(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("INTERNAL_API_TOKEN", raising=False)

    with pytest.raises(ValidationError, match="INTERNAL_API_TOKEN is required"):
        Settings()


def test_settings_reject_short_production_internal_token(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("INTERNAL_API_TOKEN", "too-short")

    with pytest.raises(ValidationError, match="at least 32 characters"):
        Settings()


def test_settings_require_https_binance_url_in_production(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("INTERNAL_API_TOKEN", "a" * 32)
    monkeypatch.setenv("BINANCE_BASE_URL", "http://binance.test")

    with pytest.raises(ValidationError, match="must use HTTPS"):
        Settings()
