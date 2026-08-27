# -*- coding: utf-8 -*-
"""
Created on Thu Aug 27 07:28:48 2026

@author: ashwe

In-memory broker session for simulated providers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autotick.providers.session_pool import BrokerSession

if TYPE_CHECKING:
    from autotick.interfaces.market_data import MarketDataProvider


class SimulatedSession(BrokerSession):
    """No-authentication session with the shared broker-session contract."""

    def __init__(self, credentials_file: str | None = None) -> None:
        self.credentials_file = credentials_file
        self.market_data: MarketDataProvider | None = None
        self._connected = False

    def set_market_data(self, market_data: MarketDataProvider) -> None:
        self.market_data = market_data

    def login(self) -> None:
        self._connected = True

    def logout(self) -> None:
        self._connected = False

    def refresh(self) -> None:
        self._connected = True

    def is_connected(self) -> bool:
        return self._connected
