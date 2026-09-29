# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 18:15:19 2026

@author: ashwe
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class ContractInfo:
    """Expiry metadata for one exchange-traded derivative contract."""

    symbol: str
    exchange: str
    instrument_type: str
    expiry: date

    @property
    def is_derivative(self) -> bool:
        return self.instrument_type.upper().startswith(("FUT", "OPT"))


@dataclass(slots=True)
class MarketTick:
    """Latest normalized market tick."""

    symbol: str
    exchange: str
    ltp: float | None = None
    volume: int | None = None
    timestamp: datetime | None = None


@dataclass(slots=True)
class MarketBar:
    """Normalized historical OHLCV candle."""

    symbol: str
    exchange: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: datetime
