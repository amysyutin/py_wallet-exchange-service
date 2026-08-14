import hashlib
import hmac
import time
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlencode

import httpx


@dataclass(frozen=True)
class SpotBalance:
    asset: str
    free: Decimal
    locked: Decimal

    @property
    def total(self) -> Decimal:
        return self.free + self.locked


class BinanceConnectorError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class BinanceConnector:
    def __init__(
        self,
        *,
        api_key: str,
        api_secret: str,
        base_url: str = "https://api.binance.com",
        timeout_seconds: float = 10,
        recv_window_ms: int = 5000,
        clock_ms: Callable[[], int] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._recv_window_ms = recv_window_ms
        self._clock_ms = clock_ms or (lambda: time.time_ns() // 1_000_000)
        self._transport = transport

    def fetch_spot_balances(self) -> tuple[SpotBalance, ...]:
        if not self._api_key or not self._api_secret:
            raise BinanceConnectorError("configuration_missing")

        params: list[tuple[str, str | int | float | bool | None]] = [
            ("omitZeroBalances", "true"),
            ("recvWindow", str(self._recv_window_ms)),
            ("timestamp", str(self._clock_ms())),
        ]
        signature_payload = urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            signature_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        signed_params = [*params, ("signature", signature)]

        try:
            with httpx.Client(
                base_url=self._base_url,
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = client.get(
                    "/api/v3/account",
                    params=signed_params,
                    headers={"X-MBX-APIKEY": self._api_key},
                )
        except httpx.TimeoutException as error:
            raise BinanceConnectorError("timeout") from error
        except httpx.HTTPError as error:
            raise BinanceConnectorError("transport_error") from error

        provider_code = self._read_provider_error_code(response)
        if response.status_code in {418, 429} or provider_code == -1003:
            raise BinanceConnectorError("rate_limited")
        if response.status_code in {401, 403} or provider_code in {-2014, -2015, -1022}:
            raise BinanceConnectorError("authentication_failed")
        if provider_code == -1021:
            raise BinanceConnectorError("timestamp_out_of_sync")
        if response.status_code >= 500:
            raise BinanceConnectorError("provider_unavailable")
        if response.status_code >= 400:
            raise BinanceConnectorError("provider_error")

        try:
            payload: Any = response.json()
        except ValueError as error:
            raise BinanceConnectorError("invalid_response") from error
        if not isinstance(payload, dict) or not isinstance(payload.get("balances"), list):
            raise BinanceConnectorError("invalid_response")

        balances: dict[str, SpotBalance] = {}
        for item in payload["balances"]:
            balance = self._parse_balance(item)
            if balance.total > 0:
                if balance.asset in balances:
                    raise BinanceConnectorError("invalid_response")
                balances[balance.asset] = balance
        return tuple(balances[asset] for asset in sorted(balances))

    @staticmethod
    def _read_provider_error_code(response: httpx.Response) -> int | None:
        if response.status_code < 400:
            return None
        try:
            payload: Any = response.json()
        except ValueError:
            return None
        code = payload.get("code") if isinstance(payload, dict) else None
        return code if isinstance(code, int) and not isinstance(code, bool) else None

    @staticmethod
    def _parse_balance(item: object) -> SpotBalance:
        if not isinstance(item, dict):
            raise BinanceConnectorError("invalid_response")
        asset = item.get("asset")
        if (
            not isinstance(asset, str)
            or not asset
            or len(asset) > 32
            or not asset.isascii()
            or not asset.isalnum()
        ):
            raise BinanceConnectorError("invalid_response")
        try:
            free = Decimal(str(item["free"]))
            locked = Decimal(str(item["locked"]))
        except (InvalidOperation, KeyError, ValueError) as error:
            raise BinanceConnectorError("invalid_response") from error
        if not free.is_finite() or not locked.is_finite() or free < 0 or locked < 0:
            raise BinanceConnectorError("invalid_response")
        return SpotBalance(asset=asset.upper(), free=free, locked=locked)
