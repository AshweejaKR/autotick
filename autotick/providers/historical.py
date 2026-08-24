# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 19:56:33 2026

@author: ashwe
"""

from __future__ import annotations

from autotick.interfaces.market_data import MarketDataProvider
from autotick.models.market import MarketBar, MarketTick


class HistoricalProvider(MarketDataProvider):
    """Shared normalized historical market-data provider."""

    def __init__(self, bars: dict[tuple[str, str], list[MarketBar]] | None = None) -> None:
        self._bars = bars or {}
        self._connected = False
        self._subscriptions: set[str] = set()

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False
        self._subscriptions.clear()

    def subscribe(self, symbols: list[str]) -> None:
        self._subscriptions.update(symbols)

    def unsubscribe(self, symbols: list[str]) -> None:
        self._subscriptions.difference_update(symbols)

    def get_tick(self, symbol: str) -> MarketTick | None:
        bars = [bar for (name, _), items in self._bars.items() if name == symbol for bar in items]
        if not bars:
            return None

        bar = max(bars, key=lambda item: item.timestamp)
        return MarketTick(
            symbol=bar.symbol,
            exchange=bar.exchange,
            ltp=bar.close,
            volume=bar.volume,
            timestamp=bar.timestamp,
        )

    def get_bars(self, symbol: str, interval: str) -> list[MarketBar]:
        return list(self._bars.get((symbol, interval), []))
