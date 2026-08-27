# -*- coding: utf-8 -*-
"""
Created on Thu Aug 27 07:28:48 2026

@author: ashwe

In-memory broker session for simulated providers.
"""

from __future__ import annotations

from autotick.providers.session_pool import BrokerSession


class SimulatedSession(BrokerSession):
    """No-authentication session with the shared broker-session contract."""

    def __init__(self) -> None:
        self._connected = False

    def login(self) -> None:
        self._connected = True

    def logout(self) -> None:
        self._connected = False

    def refresh(self) -> None:
        self._connected = True

    def is_connected(self) -> bool:
        return self._connected
