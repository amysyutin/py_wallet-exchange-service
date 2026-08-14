from enum import StrEnum


class ExchangeName(StrEnum):
    BINANCE = "binance"


class ExchangeSnapshotStatus(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
