# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 18:23:38 2026

@author: ashwe
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from autotick.models.market import MarketData


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
    def get_tick(self, symbol: str) -> MarketData | None:
        """Return the latest normalized tick for a symbol."""

    @abstractmethod
    def get_bar(self, symbol: str, interval: str) -> MarketData | None:
        """Return the latest normalized bar for a symbol."""

    @abstractmethod
    def get_history(self, symbol: str, interval: str) -> list[MarketData]:
        """Return normalized historical market data."""
