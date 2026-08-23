"""Common market models for AutoTick."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class MarketData:
    """Normalized market data shared across providers and strategies."""

    symbol: str
    exchange: str
    price: float | None = None
    volume: int | None = None
    timestamp: datetime | None = None
