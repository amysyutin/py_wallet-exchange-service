import hashlib
import hmac
from decimal import Decimal

import httpx
import pytest

from app.connectors.binance import BinanceConnector, BinanceConnectorError


def test_connector_signs_request_and_returns_non_zero_balances() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-MBX-APIKEY"] == "api-key"
        unsigned_query = "omitZeroBalances=true&recvWindow=5000&timestamp=1700000000000"
        expected_signature = hmac.new(
            b"api-secret",
            unsigned_query.encode(),
            hashlib.sha256,
        ).hexdigest()
        assert request.url.params["signature"] == expected_signature
        assert request.url.params["omitZeroBalances"] == "true"
        return httpx.Response(
            200,
            json={
                "balances": [
                    {"asset": "ETH", "free": "1.25", "locked": "0.50"},
                    {"asset": "BTC", "free": "0", "locked": "0"},
                    {"asset": "usdt", "free": "10", "locked": "2"},
                ]
            },
        )

    connector = BinanceConnector(
        api_key="api-key",
        api_secret="api-secret",
        clock_ms=lambda: 1_700_000_000_000,
        transport=httpx.MockTransport(handler),
    )

    balances = connector.fetch_spot_balances()

    assert [(item.asset, item.total) for item in balances] == [
        ("ETH", Decimal("1.75")),
        ("USDT", Decimal("12")),
    ]


@pytest.mark.parametrize(
    ("status_code", "expected_code"),
    [
        (401, "authentication_failed"),
        (403, "authentication_failed"),
        (418, "rate_limited"),
        (429, "rate_limited"),
        (500, "provider_unavailable"),
        (400, "provider_error"),
    ],
)
def test_connector_maps_provider_errors(status_code: int, expected_code: str) -> None:
    connector = BinanceConnector(
        api_key="api-key",
        api_secret="api-secret",
        clock_ms=lambda: 1_700_000_000_000,
        transport=httpx.MockTransport(lambda _request: httpx.Response(status_code)),
    )

    with pytest.raises(BinanceConnectorError) as error:
        connector.fetch_spot_balances()

    assert error.value.code == expected_code


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"balances": "not-a-list"},
        {"balances": [{"asset": "BTC", "free": "NaN", "locked": "0"}]},
        {"balances": [{"asset": "BTC", "free": "-1", "locked": "0"}]},
        {"balances": [{"asset": "", "free": "1", "locked": "0"}]},
        {"balances": [{"asset": "B TC", "free": "1", "locked": "0"}]},
    ],
)
def test_connector_rejects_invalid_responses(payload: object) -> None:
    connector = BinanceConnector(
        api_key="api-key",
        api_secret="api-secret",
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, json=payload)),
    )

    with pytest.raises(BinanceConnectorError, match="invalid_response"):
        connector.fetch_spot_balances()


@pytest.mark.parametrize(
    ("provider_code", "expected_code"),
    [
        (-1003, "rate_limited"),
        (-1021, "timestamp_out_of_sync"),
        (-1022, "authentication_failed"),
        (-2014, "authentication_failed"),
        (-2015, "authentication_failed"),
    ],
)
def test_connector_maps_binance_error_codes(provider_code: int, expected_code: str) -> None:
    connector = BinanceConnector(
        api_key="api-key",
        api_secret="api-secret",
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(400, json={"code": provider_code, "msg": "hidden"})
        ),
    )

    with pytest.raises(BinanceConnectorError) as error:
        connector.fetch_spot_balances()

    assert error.value.code == expected_code


def test_connector_rejects_duplicate_normalized_assets() -> None:
    connector = BinanceConnector(
        api_key="api-key",
        api_secret="api-secret",
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                json={
                    "balances": [
                        {"asset": "btc", "free": "1", "locked": "0"},
                        {"asset": "BTC", "free": "2", "locked": "0"},
                    ]
                },
            )
        ),
    )

    with pytest.raises(BinanceConnectorError, match="invalid_response"):
        connector.fetch_spot_balances()


def test_connector_requires_credentials() -> None:
    connector = BinanceConnector(api_key="", api_secret="")

    with pytest.raises(BinanceConnectorError, match="configuration_missing"):
        connector.fetch_spot_balances()


@pytest.mark.parametrize(
    "expected_code",
    [
        "timeout",
        "transport_error",
    ],
)
def test_connector_maps_transport_errors(expected_code: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if expected_code == "timeout":
            raise httpx.ReadTimeout("timed out", request=request)
        raise httpx.ConnectError("offline", request=request)

    connector = BinanceConnector(
        api_key="api-key",
        api_secret="api-secret",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(BinanceConnectorError) as error:
        connector.fetch_spot_balances()

    assert error.value.code == expected_code
