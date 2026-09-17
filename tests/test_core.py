# -*- coding: utf-8 -*-
"""
Created on Sat Sep 12 19:28:09 2026

@author: ashwe
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone

import pytest

from autotick.engine.dispatcher import EventDispatcher
from autotick.engine.risk_manager import RiskManager
from autotick.engine.signal_validator import SignalValidationError, SignalValidator
from autotick.engine.trade_manager import TradeManager
from autotick.engine.trading_engine import TradingEngine
from autotick.config.loader import _resolve_file_paths
from autotick.main import (
    _remove_closed_swing_symbols,
    _save_state,
    _square_off_if_due,
)
from autotick.models.event import EventType
from autotick.models.market import MarketTick
from autotick.models.order import Order, OrderIntent, OrderSide, OrderStatus
from autotick.models.position import Position, PositionStatus, PositionType
from autotick.persistence import PersistenceError
from autotick.models.signal import Signal, SignalType
from autotick.providers.brokers.simulated import (
    SimulatedAccountProvider,
    SimulatedExecutionProvider,
    SimulatedMarketDataProvider,
    SimulatedSession,
)
from autotick.providers.factory import ProviderBundle


def test_signal_and_risk_rules(make_config) -> None:
    signal = Signal("INFY-EQ", "NSE", SignalType.BUY, price=100)
    SignalValidator.validate(signal)
    with pytest.raises(SignalValidationError):
        SignalValidator.validate(Signal("", "NSE", SignalType.BUY))

    risk = RiskManager(
        make_config(capital=100_000, quantity=10, max_position_value=5_000)
    )
    assert risk.position_size(100) == 25
    assert risk.stop_loss(100, OrderSide.BUY) == 98
    assert risk.stop_loss(100, OrderSide.SELL) == 102
    assert risk.target(100, OrderSide.BUY) == 105
    assert risk.target(100, OrderSide.SELL) == 95
    risk.record_entry()
    risk.record_entry()
    assert risk.kill_switch is True


def test_margin_aware_risk_uses_broker_quantity_limit(make_config) -> None:
    config = make_config(capital=5_000, quantity=3, max_position_value=5_000)
    config["risk"]["risk_per_trade_pct"] = 100
    risk = RiskManager(config)

    assert risk.position_size(15_000) == 0
    assert risk.position_size(15_000, margin_aware=True) == 3

    config["trade"].pop("quantity")
    risk = RiskManager(config)
    assert risk.position_size(15_000, margin_aware=True) == 16


def test_trading_engine_dispatches_signal() -> None:
    session = SimulatedSession()
    market = SimulatedMarketDataProvider(session)
    account = SimulatedAccountProvider(session, 1_000)
    execution = SimulatedExecutionProvider(session)
    dispatcher = EventDispatcher()
    received = []
    dispatcher.register(EventType.SIGNAL, lambda event: received.append(event.data))
    engine = TradingEngine(ProviderBundle(market, account, execution), dispatcher)
    signal = Signal("INFY-EQ", "NSE", SignalType.BUY, price=100)

    event = engine.emit(EventType.SIGNAL, signal)

    assert event.data is signal
    assert received == [signal]


def test_trade_entry_target_exit_and_invalid_transition(make_config) -> None:
    session = SimulatedSession()
    market = SimulatedMarketDataProvider(session)
    SimulatedAccountProvider(session, 100_000)
    execution = SimulatedExecutionProvider(session)
    risk = RiskManager(
        make_config(capital=100_000, quantity=10, max_position_value=5_000)
    )
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


class _PartialExecution:
    def place_order(self, order: Order) -> Order:
        return replace(
            order,
            price=100,
            status=OrderStatus.PARTIAL,
            filled_quantity=2,
        )


def test_partial_entry_stays_managed_after_cancellation(make_config) -> None:
    risk = RiskManager(make_config())
    trades = TradeManager(_PartialExecution(), risk)

    order = trades.create_order(
        Order("PARTIAL-1", "INFY-EQ", "NSE", OrderSide.BUY, 5)
    )
    position = trades.get_position("INFY-EQ", "NSE")

    assert order.status == OrderStatus.PARTIAL
    assert order.filled_quantity == 2
    assert position is not None and position.quantity == 2
    assert trades.get_exit_prices("INFY-EQ", "NSE") is not None
    assert risk.trade_count == 1

    order = trades.update_order_state(
        replace(order, filled_quantity=4), OrderStatus.PARTIAL
    )
    assert order.filled_quantity == 4
    assert trades.get_position("INFY-EQ", "NSE").quantity == 4

    trades.update_order_state(order, OrderStatus.CANCELLED)

    assert trades.has_active_trade("INFY-EQ", "NSE") is True
    assert trades.get_position("INFY-EQ", "NSE").status == PositionStatus.OPEN


def test_daily_realized_loss_blocks_entries(make_config) -> None:
    config = make_config()
    config["risk"]["max_loss"] = -10
    session = SimulatedSession()
    market = SimulatedMarketDataProvider(session)
    SimulatedAccountProvider(session, config["capital"])
    execution = SimulatedExecutionProvider(session)
    risk = RiskManager(config)
    trades = TradeManager(execution, risk)
    now = datetime(2026, 9, 12, tzinfo=timezone.utc)
    market.set_tick(MarketTick("INFY-EQ", "NSE", 100, 10, now))
    trades.create_order(Order("LOSS-1", "INFY-EQ", "NSE", OrderSide.BUY, 5))

    market.set_tick(MarketTick("INFY-EQ", "NSE", 98, 10, now))
    order, reason = trades.monitor_exit("INFY-EQ", "NSE", 98) or (None, None)

    assert order is not None and reason == "STOP_LOSS"
    assert risk.daily_pnl == -10
    assert risk.kill_switch is True
    assert risk.can_trade(100) is False


class _SquareOffCalendar:
    def should_square_off(self, value: datetime) -> bool:
        return True


def test_square_off_due_closes_intraday_positions(make_config) -> None:
    config = make_config()
    session = SimulatedSession()
    market = SimulatedMarketDataProvider(session)
    account = SimulatedAccountProvider(session, config["capital"])
    execution = SimulatedExecutionProvider(session)
    risk = RiskManager(config)
    trades = TradeManager(execution, risk)
    now = datetime(2026, 9, 12, 15, 15, tzinfo=timezone.utc)
    market.set_tick(MarketTick("INFY-EQ", "NSE", 100, 10, now))
    trades.create_order(
        Order(
            "INTRADAY-1",
            "INFY-EQ",
            "NSE",
            OrderSide.BUY,
            5,
            position_type=PositionType.INTRADAY,
        )
    )
    providers = ProviderBundle(market, account, execution, _SquareOffCalendar())

    assert _square_off_if_due(providers, trades, PositionType.INTRADAY, now) is True
    assert trades.get_position("INFY-EQ", "NSE").status == PositionStatus.CLOSED
    assert trades.get_orders()[-1].position_type == PositionType.INTRADAY


class _FailingPersistence:
    def save(self, trading_date: date, last_processed_at=None) -> bool:
        raise PersistenceError("disk full")


def test_persistence_failure_stays_blocked_after_daily_reset(make_config) -> None:
    risk = RiskManager(make_config())

    _save_state(_FailingPersistence(), risk, date(2026, 9, 12))
    risk.reset_daily_state()

    assert risk.persistence_failed is True
    assert risk.kill_switch is True
    assert risk.can_trade(100) is False


def test_relative_log_path_resolves_from_config_file(tmp_path) -> None:
    config = {"logging": {"log_file": "logs/autotick.log"}}
    config_path = tmp_path / "config.yaml"

    _resolve_file_paths(config, config_path)

    assert config["logging"]["log_file"] == str(
        (tmp_path / "logs" / "autotick.log").resolve()
    )


def test_closed_swing_symbol_is_unsubscribed_after_reconciliation(make_config) -> None:
    session = SimulatedSession()
    market = SimulatedMarketDataProvider(session)
    execution = SimulatedExecutionProvider(session)
    risk = RiskManager(make_config())
    trades = TradeManager(execution, risk)
    trades.open_position(Position("INFY-EQ", "NSE", 1, 100))
    trades.close_position("INFY-EQ", "NSE")
    market.subscribe(["INFY-EQ"])
    providers = ProviderBundle(market, SimulatedAccountProvider(session, 1_000), execution)
    symbols = ["INFY-EQ"]
    strategies = {"INFY-EQ": object()}

    _remove_closed_swing_symbols(providers, symbols, strategies, trades, "NSE")

    assert symbols == []
    assert strategies == {}
    assert session.state.subscriptions == set()
