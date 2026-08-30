# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 19:56:33 2026

@author: ashwe
"""

from __future__ import annotations

from autotick.interfaces.account import AccountProvider
from autotick.models.account import Account
from autotick.providers.brokers.simulated.session import SimulatedSession


class SimulatedAccountProvider(AccountProvider):
    """Simple in-memory account provider for simulated trading."""

    def __init__(
        self,
        session: SimulatedSession,
        configured_capital: float = 0.0,
    ) -> None:
        self.session = session
        self.session.state.initialize_account(configured_capital)

    @property
    def _account(self) -> Account:
        """Keep existing simulated-account access backed by session state."""
        return self.session.state.get_account()

    @_account.setter
    def _account(self, account: Account) -> None:
        self.session.state.set_account(account)

    def connect(self) -> None:
        self.session.login()

    def disconnect(self) -> None:
        pass

    def get_balance(self) -> float:
        return float(self._account.balance or 0.0)

    def get_margin(self) -> float:
        return float(self._account.available_margin or 0.0)

    def get_buying_power(self) -> float:
        return float(self._account.buying_power or 0.0)

    def get_profile(self) -> Account:
        return self._account
