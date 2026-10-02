# -*- coding: utf-8 -*-
"""
Created on Sat Sep 12 19:28:09 2026

@author: ashwe
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from autotick.engine.risk_manager import RiskManager
from autotick.engine.signal_validator import SignalValidationError, SignalValidator
from autotick.engine.trade_manager import TradeManager
from autotick.models.market import MarketTick
from autotick.models.order import Order, OrderIntent, OrderSide, OrderStatus
from autotick.models.position import PositionStatus
from autotick.models.signal import Signal, SignalType
from autotick.providers.brokers.simulated import (
    SimulatedAccountProvider,
    SimulatedExecutionProvider,
    SimulatedMarketDataProvider,
    SimulatedSession,
)


def _config() -> dict:
    return {
        "mode": "paper",
        "broker": "simulated",
        "strategy": "test",
        "capital": 100_000,
        "trade": {"quantity": 10, "max_position_value": 5_000},
        "risk": {
            "max_loss": -2_000,
            "max_trades_per_day": 2,
            "risk_per_trade_pct": 1,
            "stoploss_pct": 2,
            "target_pct": 5,
            "trailing_atr_period": 14,
            "trailing_atr_interval": "1d",
            "trailing_atr_multiplier": 0,
        },
        "reports": {"enabled": False},
    }


def test_signal_and_risk_rules() -> None:
    signal = Signal("INFY-EQ", "NSE", SignalType.BUY, price=100)
    SignalValidator.validate(signal)
    with pytest.raises(SignalValidationError):
        SignalValidator.validate(Signal("", "NSE", SignalType.BUY))

    risk = RiskManager(_config())
    assert risk.position_size(100) == 25
    assert risk.stop_loss(100, OrderSide.BUY) == 98
    assert risk.stop_loss(100, OrderSide.SELL) == 102
    assert risk.target(100, OrderSide.BUY) == 105
    assert risk.target(100, OrderSide.SELL) == 95
    risk.record_entry()
    risk.record_entry()
    assert risk.kill_switch is True


def test_trade_entry_target_exit_and_invalid_transition() -> None:
    session = SimulatedSession()
    market = SimulatedMarketDataProvider(session)
    SimulatedAccountProvider(session, 100_000)
    execution = SimulatedExecutionProvider(session)
    risk = RiskManager(_config())
    trades = TradeManager(execution, risk)
    now = datetime(2026, 9, 12, tzinfo=timezone.utc)
    market.set_tick(MarketTick("INFY-EQ", "NSE", 100, 10, now))

    entry = trades.create_order(
        Order("ENTRY-1", "INFY-EQ", "NSE", OrderSide.BUY, 10)
    )
    position = trades.get_position("INFY-EQ", "NSE")
    assert entry.status == OrderStatus.FILLED
    assert position is not None and position.quantity == 10
    assert risk.trade_count == 1

    market.set_tick(MarketTick("INFY-EQ", "NSE", 105, 20, now))
    result = trades.monitor_exit("INFY-EQ", "NSE", 105)
    position = trades.get_position("INFY-EQ", "NSE")
    assert result is not None and result[1] == "TARGET"
    assert result[0].intent == OrderIntent.EXIT
    assert position is not None and position.status == PositionStatus.CLOSED
    assert position.realized_pnl == 50

    with pytest.raises(ValueError):
        trades.update_order_state(
            Order("BAD-1", "INFY-EQ", "NSE", OrderSide.BUY, 1),
            OrderStatus.FILLED,
        )
