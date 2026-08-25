# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 19:56:33 2026

@author: ashwe
"""

from __future__ import annotations

from typing import Any

from autotick.interfaces.account import AccountProvider
from autotick.providers.brokers.angelone.session import AngelOneSession


class AngelOneAccountProvider(AccountProvider):
    """AngelOne SmartAPI account adapter."""

    def __init__(self, session: AngelOneSession) -> None:
        self.session = session

    def connect(self) -> None:
        self.session.login()

    def disconnect(self) -> None:
        pass

    def get_balance(self) -> float:
        return self._rms_value("availablecash")

    def get_margin(self) -> float:
        return self._rms_value("availablelimitmargin")

    def get_buying_power(self) -> float:
        return self._rms_value("availablecash")

    def get_profile(self) -> dict[str, Any]:
        if not self.session.refresh_token:
            raise RuntimeError("AngelOne session is not connected")
        response = self.session.call(
            self.session.client.getProfile,
            self.session.refresh_token,
        ) or {}
        if not response.get("status"):
            raise RuntimeError(f"AngelOne profile failed: {response.get('message', 'unknown error')}")
        return response.get("data") or {}

    def _rms_value(self, key: str) -> float:
        response = self.session.call(self.session.client.rmsLimit) or {}
        if not response.get("status"):
            raise RuntimeError(f"AngelOne RMS failed: {response.get('message', 'unknown error')}")
        return float((response.get("data") or {}).get(key, 0.0))
