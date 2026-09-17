# -*- coding: utf-8 -*-
"""
Created on Sat Sep 12 19:28:09 2026

@author: ashwe
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from autotick.engine.risk_manager import RiskManager
from autotick.engine.trade_manager import TradeManager
from autotick.main import _run_providers
from autotick.models.order import Order, OrderSide, OrderStatus
from autotick.models.position import Position, PositionStatus
from autotick.models.trade import Trade
from autotick.persistence.recovery import RecoveryManager
from autotick.providers.brokers.simulated import (
    SimulatedAccountProvider,
    SimulatedExecutionProvider,
    SimulatedSession,
)
from autotick.providers.factory import ProviderBundle
from autotick.providers.session_pool import BrokerAuthenticationError
from autotick.reports import ReportManager


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


class _FailingStartupMarket:
    def connect(self) -> None:
        raise BrokerAuthenticationError("expired")

    def disconnect(self) -> None:
        pass

    def unsubscribe(self, symbols: list[str]) -> None:
        pass


class _OpenCalendar:
    def now(self) -> datetime:
        return datetime(2026, 9, 12, 9, 15, tzinfo=timezone.utc)

    def is_market_open(self, value: datetime) -> bool:
        return True


class _BrokerSession:
    def logout(self) -> None:
        pass


class _RejectedStartupReconnect:
    def recover(self, error, reconcile):
        raise BrokerAuthenticationError("expired")


def test_startup_auth_failure_keeps_saved_recovery_state(
    monkeypatch, make_config
) -> None:
    config = make_config()
    config.update({
        "engine": {"loop_sleep_s": 1},
        "reconnect": {
            "enabled": True,
            "initial_delay_s": 1,
            "max_delay_s": 1,
            "auth_max_attempts": 1,
        },
        "session": {
            "schedule_type": "DAILY",
            "timezone": "Asia/Kolkata",
            "trading_days": ["MON", "TUE", "WED", "THU", "FRI"],
            "closed_dates": [],
            "market_start": "09:15",
            "market_end": "15:30",
            "square_off_time": "15:15",
            "only_market_hours": True,
            "replay_speed": 1,
        },
        "logging": {"enabled": False, "level": "INFO", "log_file": "", "timestamp": True},
    })
    config["persistence"]["enabled"] = True
    session = SimulatedSession()
    account = SimulatedAccountProvider(session, config["capital"])
    execution = SimulatedExecutionProvider(session)
    risk = RiskManager(config)
    seed = RecoveryManager(config, TradeManager(execution, risk), risk, account, execution)
    payload = {"saved": "state"}
    seed.store.save(seed.profile_key, payload)
    providers = ProviderBundle(
        _FailingStartupMarket(), account, execution, _OpenCalendar(), _BrokerSession()
    )
    monkeypatch.setattr(
        "autotick.main.ReconnectManager", lambda *args: _RejectedStartupReconnect()
    )

    _run_providers(providers, config)

    assert seed.store.load(seed.profile_key) == payload


@pytest.mark.parametrize("mode", ("backtest", "replay"))
def test_offline_profile_does_not_load_broker_secrets(mode, make_config) -> None:
    config = make_config(mode=mode)
    config["broker"] = "angelone"
    config["broker_config"] = {"angelone": {"credentials_file": "missing.env"}}
    session = SimulatedSession()
    account = SimulatedAccountProvider(session, config["capital"])
    execution = SimulatedExecutionProvider(session)
    risk = RiskManager(config)

    recovery = RecoveryManager(config, TradeManager(execution, risk), risk, account, execution)

    assert recovery.profile["account_id"] == ""
    assert ReportManager.context(config, execution)[2] == "user"
