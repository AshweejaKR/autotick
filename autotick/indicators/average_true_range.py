# -*- coding: utf-8 -*-
"""
Created on Thu Sep 03 2026

@author: ashwe

Average true range indicator for AutoTick.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence

from autotick.indicators.base import Indicator
from autotick.models.market import MarketBar


class AverageTrueRange(Indicator):
    """Wilder average true range using normalized market bars."""

    def __init__(self, period: int = 14) -> None:
        if period <= 0:
            raise ValueError("period must be greater than zero")
        self.period = period
        self._ranges: deque[float] = deque(maxlen=period)
        self._previous_close: float | None = None
        self._value: float | None = None

    def calculate(self, bars: Sequence[MarketBar]) -> float | None:
        """Calculate Wilder ATR from chronological bars."""
        if len(bars) < self.warmup_period():
            return None
        ranges = [
            self._true_range(bar, previous.close)
            for previous, bar in zip(bars, bars[1:])
        ]
        value = sum(ranges[: self.period]) / self.period
        for true_range in ranges[self.period :]:
            value = (value * (self.period - 1) + true_range) / self.period
        return value

    def update(self, bar: MarketBar) -> float | None:
        """Add one bar and return Wilder ATR after warmup."""
        if self._previous_close is None:
            self._previous_close = bar.close
            return None
        true_range = self._true_range(bar, self._previous_close)
        self._previous_close = bar.close
        if self._value is None:
            self._ranges.append(true_range)
            if len(self._ranges) < self.period:
                return None
            self._value = sum(self._ranges) / self.period
        else:
            self._value = (
                self._value * (self.period - 1) + true_range
            ) / self.period
        return self._value

    def reset(self) -> None:
        """Clear accumulated ranges."""
        self._ranges.clear()
        self._previous_close = None
        self._value = None

    def warmup_period(self) -> int:
        """Return bars needed for the first ATR value."""
        return self.period + 1

    @staticmethod
    def _true_range(bar: MarketBar, previous_close: float) -> float:
        return max(
            bar.high - bar.low,
            abs(bar.high - previous_close),
            abs(bar.low - previous_close),
        )
