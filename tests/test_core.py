# -*- coding: utf-8 -*-
"""
Created on Sat Sep 12 19:28:09 2026

@author: ashwe
"""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from autotick.engine.dispatcher import EventDispatcher
from autotick.engine.market_session import CalendarSessionManager
from autotick.engine.risk_manager import RiskManager
from autotick.engine.signal_validator import SignalValidationError, SignalValidator
from autotick.engine.trade_manager import TradeManager
from autotick.engine.trading_engine import TradingEngine
from autotick.config.loader import _resolve_file_paths
from autotick.main import (
    _exit_status_last_logged,
    _log_exit_status,
    _process_symbols,
    _remove_closed_swing_symbols,
    _save_state,
    _square_off_if_due,
    _startup_wait_seconds,
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
from autotick.utils.logger import configure_logging, get_logger


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


def test_startup_wait_is_limited_to_final_pre_market_window() -> None:
    calendar = CalendarSessionManager({
        "schedule_type": "DAILY",
        "timezone": "Asia/Kolkata",
        "trading_days": ["MON", "TUE", "WED", "THU", "FRI"],
        "market_start": "09:15",
        "market_end": "15:30",
        "square_off_time": "15:15",
    })
    config = {"session": {"startup_wait_minutes": 30}}
    near_open = datetime(2026, 9, 21, 8, 45, tzinfo=calendar.now().tzinfo)
    too_early = datetime(2026, 9, 21, 8, 44, tzinfo=calendar.now().tzinfo)

    assert _startup_wait_seconds(calendar, config, near_open) == 1_800
    assert _startup_wait_seconds(calendar, config, too_early) is None


def test_exit_status_is_throttled_to_once_per_minute(monkeypatch) -> None:
    messages = []
    times = iter((100.0, 159.9, 160.0))
    _exit_status_last_logged.clear()
    monkeypatch.setattr("autotick.main.monotonic", lambda: next(times))
    monkeypatch.setattr(
        "autotick.main.logger.console_only",
        lambda *args, **kwargs: messages.append((args, kwargs)),
    )

    for _ in range(3):
        _log_exit_status("GOLDPETAL", "MCX", 98.0, 100.0, 105.0)

    assert len(messages) == 2
    _exit_status_last_logged.clear()


def test_console_only_message_is_not_written_to_file(tmp_path, capsys) -> None:
    root_logger = logging.getLogger()
    previous_handlers = list(root_logger.handlers)
    previous_level = root_logger.level
    log_path = tmp_path / "autotick.log"
    try:
        configure_logging(level="INFO", log_file=log_path)
        test_logger = get_logger("tests.console_only")
        test_logger.console_only("active exit range")
        test_logger.info("saved event")
        for handler in root_logger.handlers:
            handler.flush()

        assert "active exit range" in capsys.readouterr().err
        file_text = log_path.read_text(encoding="utf-8")
        assert "active exit range" not in file_text
        assert "saved event" in file_text
    finally:
        for handler in root_logger.handlers:
            handler.close()
        root_logger.handlers[:] = previous_handlers
        root_logger.setLevel(previous_level)


def test_margin_aware_risk_uses_broker_quantity_limit(make_config) -> None:
    config = make_config(capital=5_000, quantity=3, max_position_value=5_000)
    config["risk"]["risk_per_trade_pct"] = 100
    risk = RiskManager(config)

    assert risk.position_size(15_000) == 0
    assert risk.position_size(15_000, margin_aware=True) == 3

    config["trade"].pop("quantity")
    risk = RiskManager(config)
    assert risk.position_size(15_000, margin_aware=True) == 0


def test_margin_aware_risk_honors_max_position_value(make_config) -> None:
    config = make_config(capital=100_000, max_position_value=5_000)
    config["trade"].pop("quantity")
    risk = RiskManager(config)

    assert risk.position_size(100, margin_aware=True) == 50


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


def test_invalid_tick_skips_strategy(make_config) -> None:
    session = SimulatedSession()
    market = SimulatedMarketDataProvider(session)
    market.set_tick(MarketTick("INFY-EQ", "NSE", 0, 1, datetime.now(timezone.utc)))
    account = SimulatedAccountProvider(session, 1_000)
    trades = TradeManager(SimulatedExecutionProvider(session), RiskManager(make_config()))
    strategy = SimpleNamespace(context=SimpleNamespace(tick=None))

    _process_symbols(
        ProviderBundle(market, account, trades.execution),
        ["INFY-EQ"],
        {"INFY-EQ": strategy},
        trades,
        trades.risk_manager,
        set(),
        PositionType.POSITIONAL,
        make_config(),
    )

    assert trades.get_orders() == []


def test_filled_order_without_exit_levels_blocks_new_entries(make_config) -> None:
    class _MissingFillPrice:
        def place_order(self, order: Order) -> Order:
            return replace(order, price=None, status=OrderStatus.FILLED)

    session = SimulatedSession()
    market = SimulatedMarketDataProvider(session)
    now = datetime.now(timezone.utc)
    market.set_tick(MarketTick("INFY-EQ", "NSE", 100, 1, now))
    account = SimulatedAccountProvider(session, 1_000)
    risk = RiskManager(make_config())
    trades = TradeManager(_MissingFillPrice(), risk)
    strategy = SimpleNamespace(
        context=SimpleNamespace(tick=None),
        on_tick=lambda tick: Signal(tick.symbol, tick.exchange, SignalType.BUY, price=tick.ltp),
    )

    _process_symbols(
        ProviderBundle(market, account, trades.execution),
        ["INFY-EQ"],
        {"INFY-EQ": strategy},
        trades,
        risk,
        set(),
        PositionType.POSITIONAL,
        make_config(),
    )

    assert risk.kill_switch is True


def test_reconcile_orders_does_not_adopt_unknown_broker_orders(make_config) -> None:
    known = Order("KNOWN", "INFY-EQ", "NSE", OrderSide.BUY, 1, status=OrderStatus.SUBMITTED)
    manual = Order("MANUAL", "TCS-EQ", "NSE", OrderSide.BUY, 1, status=OrderStatus.OPEN)
    execution = SimpleNamespace(get_orders=lambda: [known, manual])
    trades = TradeManager(execution, RiskManager(make_config()))
    trades.track_order(known)

    trades.reconcile_orders()

    assert trades.get_order("MANUAL") is None


def test_close_position_removes_exit_levels(make_config) -> None:
    session = SimulatedSession()
    market = SimulatedMarketDataProvider(session)
    now = datetime.now(timezone.utc)
    market.set_tick(MarketTick("INFY-EQ", "NSE", 100, 1, now))
    SimulatedAccountProvider(session, 1_000)
    execution = SimulatedExecutionProvider(session)
    trades = TradeManager(execution, RiskManager(make_config()))

    trades.create_order(Order("ENTRY-1", "INFY-EQ", "NSE", OrderSide.BUY, 1))
    assert trades.get_exit_prices("INFY-EQ", "NSE") is not None
    trades.close_position("INFY-EQ", "NSE")

    assert trades.get_exit_prices("INFY-EQ", "NSE") is None


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
