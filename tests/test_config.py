from pytest import MonkeyPatch

from app.config import Settings


def test_settings_accept_environment_overrides(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("EXCHANGE_SERVICE_PORT", "9002")

    settings = Settings()

    assert settings.environment == "test"
    assert settings.exchange_service_port == 9002


def test_settings_ignore_unknown_environment_variables(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("EXCHANGE_UNKNOWN_SETTING", "ignored")

    settings = Settings()

    assert settings.app_name == "py-wallet-exchange-service"
