# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 19:56:33 2026

@author: ashwe
"""

from __future__ import annotations

import csv
from datetime import datetime

from autotick.interfaces.market_data import MarketDataProvider
from autotick.models.market import MarketBar, MarketTick


class HistoricalProvider(MarketDataProvider):
    """Shared normalized historical market-data provider."""

    def __init__(self, bars: dict[tuple[str, str], list[MarketBar]] | None = None) -> None:
        self._bars = bars or {}
        self._connected = False
        self._subscriptions: set[str] = set()
        self._current_time: datetime | None = None

    @classmethod
    def from_csv(cls, path: str) -> "HistoricalProvider":
        """Load normalized bars from a CSV historical-data file."""
        bars: dict[tuple[str, str], list[MarketBar]] = {}
        with open(path, newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                bar = MarketBar(
                    symbol=row["symbol"],
                    exchange=row["exchange"],
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=int(row["volume"]),
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                )
                bars.setdefault((bar.symbol, row["interval"]), []).append(bar)
        for items in bars.values():
            items.sort(key=lambda item: item.timestamp)
        return cls(bars)

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False
        self._subscriptions.clear()
        self._current_time = None

    def subscribe(self, symbols: list[str]) -> None:
        self._subscriptions.update(symbols)

    def unsubscribe(self, symbols: list[str]) -> None:
        self._subscriptions.difference_update(symbols)

    def update_time(self, value: datetime) -> None:
        """Set current simulated time for Backtest or Replay reads."""
        self._current_time = value

    def get_tick(self, symbol: str) -> MarketTick | None:
        if self._current_time is None:
            return None

        bars = [
            bar
            for (name, _), items in self._bars.items()
            if name == symbol
            for bar in items
            if bar.timestamp <= self._current_time
        ]
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
        bars = list(self._bars.get((symbol, interval), []))
        if self._current_time is None:
            return []
        return [bar for bar in bars if bar.timestamp <= self._current_time]
