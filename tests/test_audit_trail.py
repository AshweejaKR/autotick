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


def test_audit_records_order_states_and_recovery(tmp_path) -> None:
    config = {
        "mode": "paper",
        "broker": "simulated",
        "strategy": "test",
        "capital": 1_000,
        "market": {"exchange": "NSE", "symbols": ["INFY-EQ"]},
        "trade": {"quantity": 5, "position_type": "POSITIONAL"},
        "risk": {
            "max_loss": -100,
            "max_trades_per_day": 2,
            "risk_per_trade_pct": 10,
            "stoploss_pct": 2,
            "target_pct": 5,
            "trailing_atr_period": 14,
            "trailing_atr_interval": "1d",
            "trailing_atr_multiplier": 0,
        },
        "persistence": {"state_path": str(tmp_path / "state.db")},
        "reports": {
            "enabled": True,
            "output_dir": str(tmp_path / "reports"),
            "user_id": "tester",
        },
    }
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
