# -*- coding: utf-8 -*-
"""
Created on Thu Aug 27 07:28:48 2026

@author: ashwe

In-memory market-data adapter for standalone simulation.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from autotick.interfaces.market_data import MarketDataProvider
from autotick.models.market import MarketBar, MarketTick
from autotick.providers.brokers.simulated.session import SimulatedSession


class SimulatedMarketDataProvider(MarketDataProvider):
    """Serve normalized ticks and bars from in-memory data."""

    def __init__(
        self,
        session: SimulatedSession,
        exchange: str = "NSE",
    ) -> None:
        self.session = session
        self.exchange = exchange.upper()
        self._lock = self.session.state.lock
        self._ticks = self.session.state.ticks
        self._bars = self.session.state.bars
        self._subscriptions = self.session.state.subscriptions
        self.session.set_market_data(self)

    def set_tick(self, tick: MarketTick) -> None:
        """Store the latest simulated tick."""
        if tick.exchange.upper() != self.exchange:
            raise ValueError(f"Expected exchange {self.exchange}, got {tick.exchange}")
        self.session.state.set_tick(tick)

    def set_bars(self, symbol: str, interval: str, bars: list[MarketBar]) -> None:
        """Store simulated bars for one symbol and interval."""
        if any(bar.exchange.upper() != self.exchange for bar in bars):
            raise ValueError(f"Expected exchange {self.exchange}")
        self.session.state.set_bars(symbol, interval, bars)

    def connect(self) -> None:
        self.session.login()

    def disconnect(self) -> None:
        self._subscriptions.clear()

    def subscribe(self, symbols: list[str]) -> None:
        self._subscriptions.update(symbol.upper() for symbol in symbols)

    def unsubscribe(self, symbols: list[str]) -> None:
        self._subscriptions.difference_update(symbol.upper() for symbol in symbols)

    def get_tick(self, symbol: str) -> MarketTick | None:
        return self.session.state.get_tick(symbol)

    def get_bars(
        self,
        symbol: str,
        interval: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[MarketBar]:
        bars = self.session.state.get_bars(symbol, interval)
        if not bars:
            return []

        end_date = end_date or datetime.now(bars[-1].timestamp.tzinfo)
        start_date = start_date or end_date - timedelta(days=30 if interval.lower() == "1d" else 5)
        if start_date > end_date:
            raise ValueError("start_date must not be after end_date")
        return [bar for bar in bars if start_date <= bar.timestamp <= end_date]
