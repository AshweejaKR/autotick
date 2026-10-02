# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 00:19:15 2026

@author: ashwe

Mode-neutral runtime context exposed to strategies.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from autotick.interfaces.market_data import MarketDataProvider
from autotick.models.market import MarketBar, MarketTick


@dataclass(slots=True)
class StrategyContext:
    """Hold strategy dependencies, latest market inputs, and indicator values."""

    market_data: MarketDataProvider
    symbol: str
    tick: MarketTick | None = None
    bar: MarketBar | None = None
    indicators: dict[str, float | None] = field(default_factory=dict)
