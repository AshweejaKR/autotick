# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 18:15:19 2026

@author: ashwe
"""

from __future__ import annotations

"""Common market models for AutoTick."""

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
