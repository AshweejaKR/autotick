# -*- coding: utf-8 -*-
"""
Created on Sun Aug 30 09:25:06 2026

@author: ashwe
"""

from __future__ import annotations

from autotick.models.market import MarketTick
from autotick.models.signal import Signal, SignalType
from autotick.strategy.base import Strategy
from autotick.utils.logger import get_logger

logger = get_logger(__name__)


class LiveVerificationStrategy(Strategy):
    """Trade the first buffered previous-day range breakout."""

    BREAKOUT_BUFFER_PCT = 0.15

    def __init__(self) -> None:
        super().__init__()
        self.long_trigger: float | None = None
        self.short_trigger: float | None = None

    def on_initial_setup(self) -> None:
        logger.debug("LIVE_VERIFY on_initial_setup entry")
        if self.context is None:
            raise RuntimeError("Strategy is not initialized")
        tick = self.context.tick or self.context.market_data.get_tick(
            self.context.symbol
        )
        if tick is None or tick.timestamp is None:
            raise RuntimeError(
                f"Current market timestamp is unavailable for {self.context.symbol}"
            )
        completed = [
            bar
            for bar in self.context.market_data.get_bars(
                self.context.symbol,
                "1d",
            )
            if bar.timestamp.date() < tick.timestamp.date()
        ]
        if not completed:
            raise RuntimeError(
                f"No completed historical daily bars available for {self.context.symbol}"
            )
        previous = max(completed, key=lambda bar: bar.timestamp)
        buffer = self.BREAKOUT_BUFFER_PCT / 100
        self.long_trigger = previous.high * (1 + buffer)
        self.short_trigger = previous.low * (1 - buffer)
        logger.info(
            "LIVE_VERIFY ready symbol=%s previous_high=%.2f previous_low=%.2f "
            "long_trigger=%.2f short_trigger=%.2f",
            self.context.symbol,
            previous.high,
            previous.low,
            self.long_trigger,
            self.short_trigger,
        )
        logger.debug("LIVE_VERIFY on_initial_setup exit")

    def on_tick(self, tick: MarketTick) -> Signal | None:
        if (
            tick.ltp is None
            or self.long_trigger is None
            or self.short_trigger is None
        ):
            return None
        logger.debug(
            "LIVE_VERIFY ENTRY RANGE symbol=%s low_trigger=%.2f <-- "
            "current=%.2f --> high_trigger=%.2f",
            tick.symbol,
            self.short_trigger,
            tick.ltp,
            self.long_trigger,
        )
        signal_type = None
        if tick.ltp > self.long_trigger:
            signal_type = SignalType.BUY
        elif tick.ltp < self.short_trigger:
            signal_type = SignalType.SELL
        signal = (
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
        if signal is not None:
            logger.warning(
                "LIVE_VERIFY %s TRIGGER symbol=%s ltp=%.2f buffer_pct=%.2f",
                signal.signal_type.value,
                tick.symbol,
                tick.ltp,
                self.BREAKOUT_BUFFER_PCT,
            )
        logger.debug(
            "LIVE_VERIFY on_tick exit symbol=%s signal=%s",
            tick.symbol,
            signal.signal_type.value if signal is not None else None,
        )
        return signal
