# -*- coding: utf-8 -*-
"""
Created on Wed Sep 17 2026

@author: ashwe
"""

from __future__ import annotations

from time import monotonic

from autotick.models.market import MarketTick
from autotick.models.signal import Signal, SignalType
from autotick.strategy.base import Strategy
from autotick.utils.logger import get_logger


logger = get_logger(__name__)


class MCXGoldPetalORBStrategy(Strategy):
    """Trade the first 0.15% breakout of the previous daily range."""

    BUFFER_PCT = 0.15
    STATUS_INTERVAL_S = 60.0

    def __init__(self) -> None:
        super().__init__()
        self.long_trigger: float | None = None
        self.short_trigger: float | None = None
        self._last_status_logged: float | None = None

    def on_initial_setup(self) -> None:
        if self.context is None:
            raise RuntimeError("Strategy is not initialized")
        tick = self.context.tick or self.context.market_data.get_tick(self.context.symbol)
        if tick is None:
            raise RuntimeError(f"Current market tick is unavailable for {self.context.symbol}")
        bars = self.context.market_data.get_bars(self.context.symbol, "1d")
        completed = [bar for bar in bars if bar.timestamp.date() < tick.timestamp.date()]
        if not completed:
            raise RuntimeError(f"No completed daily bar available for {self.context.symbol}")
        previous = max(completed, key=lambda bar: bar.timestamp)
        buffer = self.BUFFER_PCT / 100
        self.long_trigger = previous.high * (1 + buffer)
        self.short_trigger = previous.low * (1 - buffer)

    def on_tick(self, tick: MarketTick) -> Signal | None:
        if tick.ltp is None or self.long_trigger is None or self.short_trigger is None:
            return None
        now = monotonic()
        if (
            self._last_status_logged is None
            or now - self._last_status_logged >= self.STATUS_INTERVAL_S
        ):
            logger.console_only(
                "MCX_ORB_GOLDPETAL ENTRY RANGE symbol=%s low_trigger=%.2f <-- "
                "current=%.2f --> high_trigger=%.2f",
                tick.symbol,
                self.short_trigger,
                tick.ltp,
                self.long_trigger,
            )
            self._last_status_logged = now
        signal_type = (
            SignalType.BUY if tick.ltp > self.long_trigger
            else SignalType.SELL if tick.ltp < self.short_trigger
            else None
        )
        return (
            Signal(
                symbol=tick.symbol,
                exchange=tick.exchange,
                signal_type=signal_type,
                price=tick.ltp,
                timestamp=tick.timestamp,
            )
            if signal_type is not None
            else None
        )
