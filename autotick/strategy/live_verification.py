# -*- coding: utf-8 -*-
"""
Created on Sun Aug 30 09:25:06 2026

@author: ashwe
"""

from __future__ import annotations

from autotick.models.market import MarketTick
from autotick.models.signal import Signal, SignalType
from autotick.strategy.simple_strategy import SimpleStrategy
from autotick.utils.logger import get_logger

logger = get_logger(__name__)


class LiveVerificationStrategy(SimpleStrategy):
    """One-entry strategy for end-to-end Live verification."""

    ENTRY_THRESHOLD_PCT = 0.05

    def on_initial_setup(self) -> None:
        logger.debug("LIVE_VERIFY on_initial_setup entry")
        super().on_initial_setup()
        logger.info(
            "LIVE_VERIFY ready symbol=%s previous_close=%.2f entry_trigger=%.2f",
            self.context.symbol,
            self.previous_close,
            self.previous_close * (1 + self.ENTRY_THRESHOLD_PCT / 100),
        )
        logger.debug("LIVE_VERIFY on_initial_setup exit")

    def on_tick(self, tick: MarketTick) -> Signal | None:
        trigger = (
            self.previous_close * (1 + self.ENTRY_THRESHOLD_PCT / 100)
            if self.previous_close is not None
            else None
        )
        logger.debug(
            "LIVE_VERIFY on_tick entry symbol=%s ltp=%s previous_close=%s trigger=%s",
            tick.symbol,
            tick.ltp,
            self.previous_close,
            trigger,
        )
        signal = super().on_tick(tick)
        if signal is not None:
            logger.warning(
                "LIVE_VERIFY ENTRY TRIGGER symbol=%s ltp=%.2f threshold_pct=%.3f",
                tick.symbol,
                tick.ltp,
                self.ENTRY_THRESHOLD_PCT,
            )
        logger.debug(
            "LIVE_VERIFY on_tick exit symbol=%s signal=%s",
            tick.symbol,
            signal.signal_type.value if signal is not None else None,
        )
        return signal
