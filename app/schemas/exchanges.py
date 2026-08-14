from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExchangeSnapshotCreate(BaseModel):
    user_id: int = Field(gt=0)


class ExchangeBalanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset: str
    free: Decimal
    locked: Decimal
    total: Decimal


class ExchangeSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    exchange: Literal["binance"]
    status: Literal["success"]
    created_at: datetime
    completed_at: datetime
    balances: list[ExchangeBalanceResponse]
