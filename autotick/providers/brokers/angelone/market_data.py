# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 19:56:33 2026

@author: ashwe
"""

from __future__ import annotations

from datetime import datetime, timedelta

from autotick.interfaces.market_data import MarketDataProvider
from autotick.models.market import MarketBar, MarketTick
from autotick.providers.brokers.angelone.session import AngelOneSession


class AngelOneMarketDataProvider(MarketDataProvider):
    """AngelOne SmartAPI market-data adapter."""

    _INTERVALS = {
        "1m": "ONE_MINUTE",
        "3m": "THREE_MINUTE",
        "5m": "FIVE_MINUTE",
        "10m": "TEN_MINUTE",
        "15m": "FIFTEEN_MINUTE",
        "30m": "THIRTY_MINUTE",
        "1h": "ONE_HOUR",
        "1d": "ONE_DAY",
    }

    def __init__(self, session: AngelOneSession, exchange: str = "NSE") -> None:
        self.session = session
        self.exchange = exchange.upper()
        self._subscriptions: set[str] = set()

    def connect(self) -> None:
        if not self.session.is_connected():
            self.session.login()

    def disconnect(self) -> None:
        self._subscriptions.clear()

    def subscribe(self, symbols: list[str]) -> None:
        for symbol in symbols:
            self.session.get_token(symbol, self.exchange)
            self._subscriptions.add(symbol.upper())

    def unsubscribe(self, symbols: list[str]) -> None:
        self._subscriptions.difference_update(symbol.upper() for symbol in symbols)

    def get_tick(self, symbol: str) -> MarketTick | None:
        token = self.session.get_token(symbol, self.exchange)
        response = self.session.client.ltpData(self.exchange, symbol, token)
        data = response.get("data") if response.get("status") else None
        if not data:
            return None
        return MarketTick(
            symbol=symbol,
            exchange=self.exchange,
            ltp=float(data.get("ltp", 0.0)),
            volume=int(data.get("tradeVolume", 0) or 0),
            timestamp=datetime.now(),
        )

    def get_bars(self, symbol: str, interval: str) -> list[MarketBar]:
        api_interval = self._INTERVALS.get(interval.lower())
        if api_interval is None:
            raise ValueError(f"Unsupported AngelOne interval: {interval}")

        now = datetime.now()
        start = now - timedelta(days=30 if interval.lower() == "1d" else 5)
        response = self.session.client.getCandleData(
            {
                "exchange": self.exchange,
                "symboltoken": self.session.get_token(symbol, self.exchange),
                "interval": api_interval,
                "fromdate": start.strftime("%Y-%m-%d %H:%M"),
                "todate": now.strftime("%Y-%m-%d %H:%M"),
            }
        )
        return [
            MarketBar(
                symbol=symbol,
                exchange=self.exchange,
                timestamp=datetime.fromisoformat(str(row[0])),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=int(row[5]),
            )
            for row in (response.get("data") or [])
        ]
