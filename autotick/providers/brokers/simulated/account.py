# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 19:56:33 2026

@author: ashwe
"""

from __future__ import annotations

from autotick.interfaces.account import AccountProvider
from autotick.models.account import Account


class SimulatedAccountProvider(AccountProvider):
    """Simple in-memory account provider for simulated trading."""

    def __init__(self, capital: float) -> None:
        capital = float(capital)
        self._account = Account(
            configured_capital=capital,
            balance=capital,
            available_margin=capital,
            buying_power=capital,
            account_id="SIMULATED",
            name="Simulated Account",
        )
        self._connected = False

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def get_balance(self) -> float:
        return float(self._account.balance or 0.0)

    def get_margin(self) -> float:
        return float(self._account.available_margin or 0.0)

    def get_buying_power(self) -> float:
        return float(self._account.buying_power or 0.0)

    def get_profile(self) -> Account:
        return self._account
