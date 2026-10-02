# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 00:19:15 2026

@author: ashwe

Mode-neutral Strategy base and lifecycle callbacks for AutoTick.
"""

from __future__ import annotations

from autotick.models.market import MarketBar, MarketTick
from autotick.models.order import Order
from autotick.models.signal import Signal
from autotick.strategy.context import StrategyContext


class Strategy:
    """Base strategy contract shared by every trading mode."""

    def __init__(self) -> None:
        self.context: StrategyContext | None = None

    def initialize(self, context: StrategyContext) -> None:
        """Attach the runtime context before strategy callbacks begin."""
        self.context = context

    def on_market_open(self) -> None:
        """Handle market-open lifecycle event."""

    def on_initial_setup(self) -> None:
        """Perform strategy setup after market open."""

    def on_tick(self, tick: MarketTick) -> Signal | None:
        """Handle one normalized market tick."""
        return None

    def on_bar(self, bar: MarketBar) -> Signal | None:
        """Handle one normalized market bar."""
        return None

    def on_order_filled(self, order: Order) -> None:
        """Handle a filled order."""

    def on_market_close(self) -> None:
        """Handle market-close lifecycle event."""
