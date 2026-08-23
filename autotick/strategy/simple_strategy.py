# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 00:19:15 2026

@author: ashwe

Simple long-only previous-close breakout strategy for AutoTick.
"""

from __future__ import annotations

from autotick.models.market import MarketTick
from autotick.models.signal import Signal, SignalType
from autotick.strategy.base import Strategy


class SimpleStrategy(Strategy):
    """Generate BUY when LTP is more than 0.5% above previous close."""

    ENTRY_THRESHOLD_PCT = 0.5

    def __init__(self) -> None:
        super().__init__()
        self.previous_close: float | None = None

    def on_initial_setup(self) -> None:
        """Load the latest completed daily close before processing ticks."""
        if self.context is None:
            raise RuntimeError("Strategy is not initialized")

        reference_tick = self.context.tick or self.context.market_data.get_tick(self.context.symbol)
        if reference_tick is None or reference_tick.timestamp is None:
            raise RuntimeError(
                f"Current market timestamp is unavailable for {self.context.symbol}"
            )

        bars = self.context.market_data.get_bars(self.context.symbol, "1d")
        completed_bars = [
            bar
            for bar in bars
            if bar.timestamp.date() < reference_tick.timestamp.date()
        ]
        if not completed_bars:
            raise RuntimeError(
                f"No completed historical daily bars available for {self.context.symbol}"
            )

        self.previous_close = max(completed_bars, key=lambda bar: bar.timestamp).close

    def on_tick(self, tick: MarketTick) -> Signal | None:
        """Generate a long BUY signal when the breakout condition is met."""
        if self.previous_close is None or tick.ltp is None:
            return None

        entry_price = self.previous_close * (1 + self.ENTRY_THRESHOLD_PCT / 100)
        if tick.ltp <= entry_price:
            return None

        return Signal(
            symbol=tick.symbol,
            exchange=tick.exchange,
            signal_type=SignalType.BUY,
            price=tick.ltp,
            timestamp=tick.timestamp,
        )
