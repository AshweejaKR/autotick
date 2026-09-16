# -*- coding: utf-8 -*-
"""
Created on Sat Sep 12 19:28:09 2026

@author: ashwe
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from autotick.engine.risk_manager import RiskManager
from autotick.engine.trade_manager import TradeManager
from autotick.models.order import Order, OrderSide, OrderStatus
from autotick.models.position import Position, PositionStatus
from autotick.models.trade import Trade
from autotick.persistence.recovery import RecoveryManager
from autotick.providers.brokers.simulated import SimulatedAccountProvider, SimulatedSession


class _FakeLiveExecution:
    def __init__(self, orders: list[Order], positions: list[Position], trades: list[Trade]) -> None:
        self.orders = orders
        self.positions = positions
        self.trades = trades

    def get_orders(self) -> list[Order]:
        return self.orders

    def get_positions(self) -> list[Position]:
        return self.positions

    def get_holdings(self) -> list[Position]:
        return []

    def get_trades(self) -> list[Trade]:
        return self.trades


def test_fake_live_reconciliation_updates_known_and_blocks_manual_state(tmp_path, make_config) -> None:
    now = datetime(2026, 9, 12, 9, 15, tzinfo=timezone.utc)
    known = Order(
        "KNOWN-1", "INFY-EQ", "NSE", OrderSide.BUY, 5,
        price=100, status=OrderStatus.SUBMITTED,
    )
    provider_order = Order(
        "KNOWN-1", "INFY-EQ", "NSE", OrderSide.BUY, 5,
        price=100, status=OrderStatus.FILLED,
    )
    manual_order = Order(
        "MANUAL-1", "TCS-EQ", "NSE", OrderSide.BUY, 1,
        price=200, status=OrderStatus.FILLED,
    )
    known_position = Position("INFY-EQ", "NSE", 5, 100)
    manual_position = Position("TCS-EQ", "NSE", 1, 200)
    provider_trade = Trade(
        "TRADE-1", "KNOWN-1", "INFY-EQ", "NSE", OrderSide.BUY, 5, 100, now
    )
    execution = _FakeLiveExecution(
        [provider_order, manual_order],
        [known_position, manual_position],
        [provider_trade],
    )
    config = make_config(mode="live")
    risk = RiskManager(config)
    trades = TradeManager(execution, risk)
    trades.track_order(known)
    account = SimulatedAccountProvider(SimulatedSession(), config["capital"])
    recovery = RecoveryManager(config, trades, risk, account, execution)

    result = recovery.reconcile(date(2026, 9, 12))
    known_position = trades.get_position("INFY-EQ", "NSE")
    assert trades.get_order("KNOWN-1").status == OrderStatus.FILLED
    assert known_position is not None and known_position.status == PositionStatus.OPEN
    assert result.entered_symbols == frozenset({"INFY-EQ"})
    assert result.blocked_symbols == frozenset({"TCS-EQ"})
    assert trades.get_position("TCS-EQ", "NSE") is None
    assert risk.kill_switch is False
