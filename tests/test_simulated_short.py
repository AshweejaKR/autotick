# -*- coding: utf-8 -*-
"""
Created on Sat Sep 12 19:28:09 2026

@author: ashwe
"""

from datetime import datetime, timezone

from autotick.models.market import MarketTick
from autotick.models.order import Order, OrderIntent, OrderSide, OrderStatus
from autotick.providers.brokers.simulated import (
    SimulatedAccountProvider,
    SimulatedExecutionProvider,
    SimulatedMarketDataProvider,
    SimulatedSession,
)


def test_simulated_short_entry_and_cover() -> None:
    now = datetime(2026, 9, 12, tzinfo=timezone.utc)
    session = SimulatedSession()
    market = SimulatedMarketDataProvider(session)
    account = SimulatedAccountProvider(session, 1_000)
    execution = SimulatedExecutionProvider(session)
    market.set_tick(MarketTick("INFY-EQ", "NSE", 100, 10, now))

    entry = execution.place_order(
        Order("SHORT-1", "INFY-EQ", "NSE", OrderSide.SELL, 2)
    )
    assert entry.status == OrderStatus.FILLED
    assert execution.get_positions()[0].quantity == -2
    assert account.get_balance() == 800

    market.set_tick(MarketTick("INFY-EQ", "NSE", 90, 10, now))
    exit_order = execution.place_order(
        Order(
            "COVER-1",
            "INFY-EQ",
            "NSE",
            OrderSide.BUY,
            2,
            intent=OrderIntent.EXIT,
        )
    )
    assert exit_order.status == OrderStatus.FILLED
    assert execution.get_positions()[0].quantity == 0
    assert execution.get_pnl() == 20
    assert account.get_balance() == 1_020


def test_simulated_short_loss_keeps_account_and_pnl_aligned() -> None:
    now = datetime(2026, 9, 12, tzinfo=timezone.utc)
    session = SimulatedSession()
    market = SimulatedMarketDataProvider(session)
    account = SimulatedAccountProvider(session, 1_000)
    execution = SimulatedExecutionProvider(session)
    market.set_tick(MarketTick("INFY-EQ", "NSE", 100, 10, now))
    execution.place_order(Order("SHORT-LOSS", "INFY-EQ", "NSE", OrderSide.SELL, 2))

    market.set_tick(MarketTick("INFY-EQ", "NSE", 700, 10, now))
    exit_order = execution.place_order(
        Order(
            "COVER-LOSS",
            "INFY-EQ",
            "NSE",
            OrderSide.BUY,
            2,
            intent=OrderIntent.EXIT,
        )
    )

    assert exit_order.status == OrderStatus.FILLED
    assert execution.get_pnl() == -1_200
    assert account.get_balance() == -200
