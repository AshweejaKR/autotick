# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 00:19:15 2026

@author: ashwe

Base contract for AutoTick indicators.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from autotick.models.market import MarketBar


class Indicator(ABC):
    """Common contract for stateful and batch indicators."""

    @abstractmethod
    def calculate(self, bars: Sequence[MarketBar]) -> float | None:
        """Calculate the indicator value from historical bars."""

    @abstractmethod
    def update(self, bar: MarketBar) -> float | None:
        """Update indicator state with one new market bar."""

    @abstractmethod
    def reset(self) -> None:
        """Clear accumulated indicator state."""

    @abstractmethod
    def warmup_period(self) -> int:
        """Return minimum bars required before a value is available."""
