# -*- coding: utf-8 -*-
"""
Created on Thu Aug 27 07:28:48 2026

@author: ashwe

Provider signature and normalized-return parity tests.
"""

from __future__ import annotations

import inspect
import unittest
from datetime import datetime

from autotick.interfaces.account import AccountProvider
from autotick.interfaces.execution import ExecutionProvider
from autotick.interfaces.market_data import MarketDataProvider
from autotick.models.account import Account
from autotick.models.market import MarketBar, MarketTick
from autotick.providers.brokers.angelone import (
    AngelOneAccountProvider,
    AngelOneExecutionProvider,
    AngelOneMarketDataProvider,
    AngelOneSession,
)
from autotick.providers.brokers.simulated import (
    SimulatedAccountProvider,
    SimulatedExecutionProvider,
    SimulatedMarketDataProvider,
    SimulatedSession,
)
from autotick.providers.factory import ProviderFactory
from autotick.providers.historical import HistoricalProvider
from autotick.providers.session_pool import BrokerSession


class _FakeClient:
    def getProfile(self, refresh_token: str) -> dict:
        return {
            "status": True,
            "data": {
                "clientcode": "A123",
                "name": "Test User",
                "email": "test@example.com",
                "mobileno": "9999999999",
            },
        }

    def rmsLimit(self) -> dict:
        return {
            "status": True,
            "data": {"availablecash": "90000", "availablelimitmargin": "80000"},
        }


class _FakeAngelSession:
    refresh_token = "refresh-token"

    def __init__(self) -> None:
        self.client = _FakeClient()

    @staticmethod
    def call(function, *args):
        return function(*args)


class ProviderContractTests(unittest.TestCase):
    def assert_contract(self, contract: type, implementations: tuple[type, ...]) -> None:
        for name in contract.__abstractmethods__:
            expected = inspect.signature(getattr(contract, name))
            for implementation in implementations:
                self.assertEqual(expected, inspect.signature(getattr(implementation, name)))

    def test_provider_method_signatures_match(self) -> None:
        self.assert_contract(
            AccountProvider,
            (AngelOneAccountProvider, SimulatedAccountProvider),
        )
        self.assert_contract(
            MarketDataProvider,
            (AngelOneMarketDataProvider, SimulatedMarketDataProvider),
        )
        self.assert_contract(
            ExecutionProvider,
            (AngelOneExecutionProvider, SimulatedExecutionProvider),
        )

    def test_session_method_signatures_match(self) -> None:
        for name in ("login", "logout", "refresh", "is_connected"):
            expected = inspect.signature(getattr(BrokerSession, name))
            self.assertEqual(expected, inspect.signature(getattr(AngelOneSession, name)))
            self.assertEqual(expected, inspect.signature(getattr(SimulatedSession, name)))

    def test_account_profiles_are_normalized(self) -> None:
        angelone = AngelOneAccountProvider(_FakeAngelSession(), 100000)
        simulated = SimulatedAccountProvider(100000)

        for profile in (angelone.get_profile(), simulated.get_profile()):
            self.assertIsInstance(profile, Account)
            self.assertIsInstance(profile.configured_capital, float)
            self.assertIsInstance(profile.balance, float)

    def test_simulated_market_data_returns_normalized_models(self) -> None:
        timestamp = datetime(2026, 8, 27, 9, 15)
        tick = MarketTick("INFY-EQ", "NSE", 1500.0, 100, timestamp)
        bar = MarketBar("INFY-EQ", "NSE", 1490.0, 1510.0, 1480.0, 1500.0, 1000, timestamp)
        provider = SimulatedMarketDataProvider(
            SimulatedSession(),
            ticks={"INFY-EQ": tick},
            bars={("INFY-EQ", "1m"): [bar]},
        )

        provider.connect()
        self.assertIsInstance(provider.get_tick("INFY-EQ"), MarketTick)
        self.assertTrue(all(
            isinstance(item, MarketBar)
            for item in provider.get_bars("INFY-EQ", "1m")
        ))

    def test_historical_mode_mapping_is_unchanged(self) -> None:
        bundle = ProviderFactory.create_bundle(
            "backtest",
            {"capital": 100000, "session": {}, "backtest": {"csv": {}}},
        )

        self.assertIsInstance(bundle.market_data, HistoricalProvider)
        self.assertIsInstance(bundle.account, SimulatedAccountProvider)
        self.assertIsInstance(bundle.execution, SimulatedExecutionProvider)


if __name__ == "__main__":
    unittest.main()
