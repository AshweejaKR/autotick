# -*- coding: utf-8 -*-
"""
Created on Thu Aug 27 07:28:48 2026

@author: ashwe

In-memory market-data adapter for standalone simulation and tests.
"""

from __future__ import annotations

from autotick.interfaces.market_data import MarketDataProvider
from autotick.models.market import MarketBar, MarketTick
from autotick.providers.brokers.simulated.session import SimulatedSession


class SimulatedMarketDataProvider(MarketDataProvider):
    """Serve normalized ticks and bars from in-memory data."""

    def __init__(
        self,
        session: SimulatedSession,
        ticks: dict[str, MarketTick] | None = None,
        bars: dict[tuple[str, str], list[MarketBar]] | None = None,
    ) -> None:
        self.session = session
        self._ticks = {symbol.upper(): tick for symbol, tick in (ticks or {}).items()}
        self._bars = {
            (symbol.upper(), interval.lower()): list(items)
            for (symbol, interval), items in (bars or {}).items()
        }
        self._subscriptions: set[str] = set()

    def connect(self) -> None:
        self.session.login()

    def disconnect(self) -> None:
        self._subscriptions.clear()

    def subscribe(self, symbols: list[str]) -> None:
        self._subscriptions.update(symbol.upper() for symbol in symbols)

    def unsubscribe(self, symbols: list[str]) -> None:
        self._subscriptions.difference_update(symbol.upper() for symbol in symbols)

    def get_tick(self, symbol: str) -> MarketTick | None:
        return self._ticks.get(symbol.upper())

    def get_bars(self, symbol: str, interval: str) -> list[MarketBar]:
        return list(self._bars.get((symbol.upper(), interval.lower()), []))
