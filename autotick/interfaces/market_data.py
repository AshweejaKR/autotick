# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 18:23:38 2026

@author: ashwe
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from autotick.models.market import MarketBar, MarketTick


class MarketDataProvider(ABC):
    """Template contract for normalized market-data providers."""

    @abstractmethod
    def connect(self) -> None:
        """Connect to the market-data source."""

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the market-data source."""

    @abstractmethod
    def subscribe(self, symbols: list[str]) -> None:
        """Subscribe to one or more symbols."""

    @abstractmethod
    def unsubscribe(self, symbols: list[str]) -> None:
        """Unsubscribe from one or more symbols."""

    @abstractmethod
    def get_tick(self, symbol: str) -> MarketTick | None:
        """Return the latest LTP and current volume for a symbol."""

    @abstractmethod
    def get_bars(
        self,
        symbol: str,
        interval: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[MarketBar]:
        """Return normalized OHLCV candles for the requested date range."""
