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
from autotick.persistence.recovery import RecoveryManager
from autotick.providers.brokers.simulated import (
    SimulatedAccountProvider,
    SimulatedExecutionProvider,
    SimulatedMarketDataProvider,
    SimulatedSession,
)


def test_audit_records_order_states_and_recovery(tmp_path, make_config) -> None:
    config = make_config(reports=True)
    now = datetime(2026, 9, 13, 9, 15, tzinfo=timezone.utc)
    session = SimulatedSession()
    market = SimulatedMarketDataProvider(session)
    market.set_tick(MarketTick("INFY-EQ", "NSE", 100, 10, now))
    account = SimulatedAccountProvider(session, config["capital"])
    execution = SimulatedExecutionProvider(session)
    risk = RiskManager(config)
    trades = TradeManager(execution, risk)
    recovery = RecoveryManager(config, trades, risk, account, execution)

    trades.create_order(Order("ENTRY-1", "INFY-EQ", "NSE", OrderSide.BUY, 5))
    recovery.recover(date(2026, 9, 13))

    path = tmp_path / "reports" / "simulated_tester_test_paper_audit.csv"
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert [row["status"] for row in rows[:3]] == ["VALIDATED", "SUBMITTED", "FILLED"]
    assert rows[-1]["event"] == "RECOVERY"
    assert rows[-1]["details"] == "recovered=False;changed_orders=0;unresolved_orders=0"
