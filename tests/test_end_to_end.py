# -*- coding: utf-8 -*-
"""
Created on Sat Sep 12 19:28:09 2026

@author: ashwe
"""

from __future__ import annotations

import csv
from datetime import date, datetime, timezone

from autotick.engine.risk_manager import RiskManager
from autotick.engine.trade_manager import TradeManager
from autotick.models.market import MarketTick
from autotick.models.order import Order, OrderSide
from autotick.models.position import PositionStatus
from autotick.persistence.recovery import RecoveryManager
from autotick.providers.brokers.simulated import (
    SimulatedAccountProvider,
    SimulatedExecutionProvider,
    SimulatedMarketDataProvider,
    SimulatedSession,
)


def _runtime(config: dict, timestamp: datetime):
    session = SimulatedSession()
    market = SimulatedMarketDataProvider(session)
    market.set_tick(MarketTick("INFY-EQ", "NSE", 100, 10, timestamp))
    account = SimulatedAccountProvider(session, config["capital"])
    execution = SimulatedExecutionProvider(session)
    risk = RiskManager(config)
    trades = TradeManager(execution, risk)
    recovery = RecoveryManager(config, trades, risk, account, execution)
    return market, account, trades, risk, recovery


def test_paper_restart_recovers_trade_then_writes_report(tmp_path, make_config) -> None:
    config = make_config(reports=True)
    now = datetime(2026, 9, 12, 9, 15, tzinfo=timezone.utc)
    trading_date = date(2026, 9, 12)

    _, account, trades, risk, recovery = _runtime(config, now)
    entry = trades.create_order(
        Order("ENTRY-1", "INFY-EQ", "NSE", OrderSide.BUY, 5)
    )
    assert entry.price == 100
    assert recovery.save(trading_date, now) is True

    market, account, trades, risk, recovery = _runtime(config, now)
    restored = recovery.recover(trading_date)
    position = trades.get_position("INFY-EQ", "NSE")
    assert restored.recovered is True
    assert restored.entered_symbols == frozenset({"INFY-EQ"})
    assert position is not None and position.status == PositionStatus.OPEN
    assert account.get_balance() == 500
    assert risk.trade_count == 1

    market.set_tick(MarketTick("INFY-EQ", "NSE", 105, 20, now))
    exit_order, reason = trades.monitor_exit("INFY-EQ", "NSE", 105) or (None, None)
    position = trades.get_position("INFY-EQ", "NSE")
    assert reason == "TARGET"
    assert exit_order is not None and exit_order.price == 105
    assert position is not None and position.status == PositionStatus.CLOSED
    assert position.realized_pnl == 25
    assert account.get_balance() == 1_025

    path = tmp_path / "reports" / "simulated_tester_test_paper_trades.csv"
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1 and rows[0]["pnl"] == "25.0"
