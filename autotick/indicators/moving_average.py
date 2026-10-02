# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 00:19:15 2026

@author: ashwe

Simple moving average indicator for AutoTick.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence

from autotick.indicators.base import Indicator
from autotick.models.market import MarketBar


class SimpleMovingAverage(Indicator):
    """Simple moving average using market-bar close prices."""

    def __init__(self, period: int = 20) -> None:
        if period <= 0:
            raise ValueError("period must be greater than zero")

        self.period = period
        self._values: deque[float] = deque(maxlen=period)

    def calculate(self, bars: Sequence[MarketBar]) -> float | None:
        """Calculate SMA from the latest configured number of bars."""
        if len(bars) < self.period:
            return None

        closes = [bar.close for bar in bars[-self.period :]]
        return sum(closes) / self.period

    def update(self, bar: MarketBar) -> float | None:
        """Add one close price and return SMA after warmup."""
        self._values.append(bar.close)
        if len(self._values) < self.period:
            return None
        return sum(self._values) / self.period

    def reset(self) -> None:
        """Clear accumulated close prices."""
        self._values.clear()

    def warmup_period(self) -> int:
        """Return number of bars required for the first SMA value."""
        return self.period
