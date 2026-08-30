# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 18:23:38 2026

@author: ashwe
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from autotick.models.account import Account


class AccountProvider(ABC):
    """Template contract for account providers."""

    @abstractmethod
    def connect(self) -> None:
        """Connect to the account source."""

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the account source."""

    @abstractmethod
    def get_balance(self) -> float:
        """Return account balance."""

    @abstractmethod
    def get_margin(self) -> float:
        """Return available margin."""

    @abstractmethod
    def get_buying_power(self) -> float:
        """Return current buying power."""

    @abstractmethod
    def get_profile(self) -> Account:
        """Return normalized account profile information."""
