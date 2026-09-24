# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 19:56:33 2026

@author: ashwe
"""

from __future__ import annotations

from autotick.interfaces.account import AccountProvider
from autotick.models.account import Account
from autotick.providers.brokers.angelone.session import AngelOneSession
from autotick.providers.session_pool import (
    BrokerAuthenticationError,
    BrokerConnectionError,
)


class AngelOneAccountProvider(AccountProvider):
    """AngelOne SmartAPI account adapter."""

    def __init__(self, session: AngelOneSession, configured_capital: float = 0.0) -> None:
        self.session = session
        self.configured_capital = float(configured_capital)

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

    def get_profile(self) -> Account:
        if not self.session.refresh_token:
            raise BrokerAuthenticationError("AngelOne session is not connected")
        response = self.session.call(
            self.session.client.getProfile,
            self.session.refresh_token,
        ) or {}
        if not response.get("status"):
            raise BrokerConnectionError(
                f"AngelOne profile read failed: {response.get('message', 'unknown error')}"
            )
        profile = response.get("data")
        if not isinstance(profile, dict):
            raise BrokerConnectionError("AngelOne profile read returned invalid data")
        rms = self._rms_data()
        return Account(
            configured_capital=self.configured_capital,
            balance=float(rms.get("availablecash", 0.0)),
            available_margin=float(rms.get("availablelimitmargin", 0.0)),
            buying_power=float(rms.get("availablecash", 0.0)),
            account_id=self._text(profile.get("clientcode")),
            name=self._text(profile.get("name")),
            email=self._text(profile.get("email")),
            phone=self._text(profile.get("mobileno")),
        )

    def _rms_value(self, key: str) -> float:
        return float(self._rms_data().get(key, 0.0))

    def _rms_data(self) -> dict:
        response = self.session.call(self.session.client.rmsLimit) or {}
        if not response.get("status"):
            raise BrokerConnectionError(
                f"AngelOne RMS read failed: {response.get('message', 'unknown error')}"
            )
        data = response.get("data")
        if not isinstance(data, dict):
            raise BrokerConnectionError("AngelOne RMS read returned invalid data")
        return data

    @staticmethod
    def _text(value: object) -> str | None:
        return str(value) if value else None
