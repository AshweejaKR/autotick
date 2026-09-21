# -*- coding: utf-8 -*-
"""
Created on Wed Sep 17 2026

@author: ashwe
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from autotick.models.market import MarketBar, MarketTick
from autotick.models.signal import SignalType
from autotick.strategy.context import StrategyContext
from autotick.strategy.mcx_goldpetal_orb import MCXGoldPetalORBStrategy


class _Market:
    def __init__(self, bars: list[MarketBar]) -> None:
        self.bars = bars

    def get_bars(self, symbol: str, interval: str) -> list[MarketBar]:
        return self.bars

    def get_tick(self, symbol: str) -> None:
        return None


def test_mcx_goldpetal_orb_previous_day_breakout() -> None:
    now = datetime(2026, 9, 17, 9, 0, tzinfo=timezone.utc)
    market = _Market([
        MarketBar(
            "GOLDPETAL", "MCX", 100, 110, 90, 105, 1, now - timedelta(days=1)
        ),
    ])
    strategy = MCXGoldPetalORBStrategy()
    strategy.initialize(
        StrategyContext(
            market,
            "GOLDPETAL",
            MarketTick("GOLDPETAL", "MCX", 100, 1, now),
        )
    )
    strategy.on_initial_setup()

    assert (
        strategy.on_tick(MarketTick("GOLDPETAL", "MCX", 110.17, 1, now)).signal_type
        == SignalType.BUY
    )
    assert (
        strategy.on_tick(MarketTick("GOLDPETAL", "MCX", 89.86, 1, now)).signal_type
        == SignalType.SELL
    )
