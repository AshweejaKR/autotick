# -*- coding: utf-8 -*-
"""
Created on Thu Aug 27 07:28:48 2026

@author: ashwe

In-memory broker session for simulated providers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autotick.providers.brokers.simulated.state import SimulatedState
from autotick.providers.session_pool import BrokerSession
from autotick.utils.logger import get_logger

if TYPE_CHECKING:
    from autotick.interfaces.market_data import MarketDataProvider


logger = get_logger(__name__)


class SimulatedSession(BrokerSession):
    """No-authentication session with the shared broker-session contract."""

    def __init__(self, credentials_file: str | None = None) -> None:
        self.credentials_file = credentials_file
        self._state = SimulatedState()
        self.market_data: MarketDataProvider | None = None
        self._connected = False

    @property
    def state(self) -> SimulatedState:
        """Return the state shared by this session's simulated providers."""
        return self._state

    def set_market_data(self, market_data: MarketDataProvider) -> None:
        self.market_data = market_data

    def login(self) -> None:
        if self._connected:
            return
        self._connected = True
        logger.done("Simulated login completed")

    def logout(self) -> None:
        if not self._connected:
            return
        self._connected = False
        logger.done("Simulated logout completed")

    def refresh(self) -> None:
        self._connected = True
        logger.done("Simulated session refresh completed")

    def is_connected(self) -> bool:
        return self._connected
