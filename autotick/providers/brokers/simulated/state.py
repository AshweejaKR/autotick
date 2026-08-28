# -*- coding: utf-8 -*-
"""
Created on Fri Aug 28 02:00:00 2026

@author: ashwe

Shared in-memory state for simulated broker providers.
"""

from __future__ import annotations

from dataclasses import replace
from threading import RLock

from autotick.models.account import Account
from autotick.models.market import MarketBar, MarketTick


class SimulatedState:
    """Store account and market data shared through one simulated session."""

    def __init__(self) -> None:
        self.lock = RLock()
        self.account: Account | None = None
        self.ticks: dict[str, MarketTick] = {}
        self.bars: dict[tuple[str, str], list[MarketBar]] = {}
        self.subscriptions: set[str] = set()

    def initialize_account(self, configured_capital: float) -> Account:
        """Create the simulated account once for this session."""
        with self.lock:
            if self.account is None:
                capital = float(configured_capital)
                self.account = Account(
                    configured_capital=capital,
                    balance=capital,
                    available_margin=capital,
                    buying_power=capital,
                    account_id="SIMULATED",
                    name="Simulated Account",
                )
            return replace(self.account)

    def get_account(self) -> Account:
        """Return a copy of the current simulated account."""
        with self.lock:
            if self.account is None:
                return self.initialize_account(0.0)
            return replace(self.account)

    def set_account(self, account: Account) -> None:
        """Replace the current simulated account."""
        if not isinstance(account, Account):
            raise TypeError("account must be an Account")
        with self.lock:
            self.account = replace(account)

    def set_tick(self, tick: MarketTick) -> None:
        """Store one latest tick."""
        with self.lock:
            self.ticks[tick.symbol.upper()] = replace(tick)

    def get_tick(self, symbol: str) -> MarketTick | None:
        """Return a copy of one latest tick."""
        with self.lock:
            tick = self.ticks.get(symbol.upper())
            return replace(tick) if tick is not None else None

    def set_bars(self, symbol: str, interval: str, bars: list[MarketBar]) -> None:
        """Store copies of bars for one symbol and interval."""
        with self.lock:
            self.bars[(symbol.upper(), interval.lower())] = [
                replace(bar) for bar in bars
            ]

    def get_bars(self, symbol: str, interval: str) -> list[MarketBar]:
        """Return copied bars for one symbol and interval."""
        with self.lock:
            bars = self.bars.get((symbol.upper(), interval.lower()), [])
            return [replace(bar) for bar in bars]
