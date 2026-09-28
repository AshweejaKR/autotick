from __future__ import annotations

import csv
from datetime import date, datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

import autotick.providers.brokers.angelone.session as angelone_session_module
from autotick.engine.expiry import expiry_cutoff, resolve_expiry_state
from autotick.engine.market_session import CalendarSessionManager
from autotick.engine.risk_manager import RiskManager
from autotick.engine.trade_manager import TradeManager
from autotick.main import _process_symbols
from autotick.models.market import ContractInfo, MarketBar, MarketTick
from autotick.models.order import Order, OrderIntent, OrderSide, OrderStatus
from autotick.models.position import PositionStatus, PositionType
from autotick.providers.brokers.angelone.session import AngelOneSession
from autotick.providers.session_pool import BrokerConnectionError
from autotick.providers.brokers.simulated import (
    SimulatedAccountProvider,
    SimulatedExecutionProvider,
    SimulatedMarketDataProvider,
    SimulatedSession,
)
from autotick.providers.factory import ProviderBundle, ProviderFactory


def _expiry_config(make_config) -> dict:
    config = make_config(capital=100_000, quantity=1, reports=True)
    config["market"] = {"exchange": "MCX", "symbols": ["GOLDPETAL30SEP26FUT"]}
    config["trade"]["expiry_exit"] = {
        "enabled": True,
        "trading_days_before": 1,
        "time": "23:00",
    }
    config["session"] = {
        "schedule_type": "DAILY",
        "timezone": "Asia/Kolkata",
        "trading_days": ["MON", "TUE", "WED", "THU", "FRI"],
        "closed_dates": [],
        "market_start": "09:15",
        "market_end": "23:30",
        "square_off_time": "23:20",
    }
    return config


def test_angelone_instrument_master_parses_derivative_expiry() -> None:
    contracts = AngelOneSession._parse_contracts([
        {
            "symbol": "GOLDPETAL30SEP26FUT",
            "expiry": "30SEP2026",
            "instrumenttype": "FUTCOM",
            "exch_seg": "MCX",
        },
        {
            "symbol": "INFY-EQ",
            "expiry": "",
            "instrumenttype": "",
            "exch_seg": "NSE",
        },
    ])

    contract = contracts[("GOLDPETAL30SEP26FUT", "MCX")]
    assert contract.expiry == date(2026, 9, 30)
    assert contract.instrument_type == "FUTCOM"
    assert ("INFY-EQ", "NSE") not in contracts


def test_instrument_master_outage_uses_retry_cooldown(monkeypatch) -> None:
    session = object.__new__(AngelOneSession)
    session._contracts = None
    session._contracts_retry_after = 0.0
    session.get_instrument = lambda symbol, exchange: (symbol, "123")
    attempts = []
    clock = [100.0]
    monkeypatch.setattr(angelone_session_module, "monotonic", lambda: clock[0])

    def unavailable():
        attempts.append(True)
        raise BrokerConnectionError("instrument master unavailable")

    session._load_contracts = unavailable
    with pytest.raises(BrokerConnectionError):
        session.get_contract("GOLDPETAL30SEP26FUT", "MCX")
    assert session.get_contract("GOLDPETAL30SEP26FUT", "MCX") is None
    assert len(attempts) == 1
    clock[0] = 401.0
    with pytest.raises(BrokerConnectionError):
        session.get_contract("GOLDPETAL30SEP26FUT", "MCX")
    assert len(attempts) == 2


def test_expiry_cutoff_skips_exchange_holiday(make_config) -> None:
    config = _expiry_config(make_config)
    config["session"]["closed_dates"] = ["2026-09-29"]
    calendar = CalendarSessionManager(config["session"])
    contract = ContractInfo(
        "GOLDPETAL30SEP26FUT", "MCX", "FUTCOM", date(2026, 9, 30)
    )

    cutoff = expiry_cutoff(
        contract,
        calendar,
        config["session"],
        config["trade"]["expiry_exit"],
    )

    assert cutoff == datetime(2026, 9, 28, 23, 0, tzinfo=ZoneInfo("Asia/Kolkata"))


def test_unknown_derivative_expiry_blocks_entry(make_config) -> None:
    config = _expiry_config(make_config)
    calendar = CalendarSessionManager(config["session"])
    now = datetime(2026, 9, 28, 12, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    market = SimpleNamespace(get_contract=lambda symbol: None)

    state = resolve_expiry_state(
        market,
        "GOLDPETAL30SEP26FUT",
        now,
        calendar,
        config,
    )

    assert state.is_derivative is True
    assert state.block_entry is True
    assert state.exit_due is False


def test_configured_expiry_fallback_and_broker_priority(make_config) -> None:
    config = _expiry_config(make_config)
    config["trade"]["expiry_exit"]["contracts"] = {
        "GOLDPETAL30SEP26FUT": "2026-09-30"
    }
    calendar = CalendarSessionManager(config["session"])
    now = datetime(2026, 9, 29, 23, 1, tzinfo=ZoneInfo("Asia/Kolkata"))

    def unavailable(symbol):
        raise BrokerConnectionError("instrument master unavailable")

    fallback = resolve_expiry_state(
        SimpleNamespace(get_contract=unavailable),
        "GOLDPETAL30SEP26FUT", now, calendar, config,
    )
    assert fallback.expiry == date(2026, 9, 30)
    assert fallback.exit_due

    broker = resolve_expiry_state(
        SimpleNamespace(get_contract=lambda symbol: ContractInfo(
            symbol, "MCX", "FUTCOM", date(2026, 10, 1)
        )),
        "GOLDPETAL30SEP26FUT", now, calendar, config,
    )
    assert broker.expiry == date(2026, 10, 1)
    assert not broker.exit_due


def test_process_symbols_closes_position_at_expiry_cutoff(make_config) -> None:
    config = _expiry_config(make_config)
    config["mode"] = "backtest"
    config["trade"]["expiry_exit"]["contracts"] = {
        "GOLDPETAL30SEP26FUT": "2026-09-30"
    }
    now = datetime(2026, 9, 29, 23, 1, tzinfo=ZoneInfo("Asia/Kolkata"))
    providers = ProviderFactory.create_bundle("backtest", config)
    market = providers.market_data
    market._bars[("GOLDPETAL30SEP26FUT", "1m")] = [MarketBar(
        "GOLDPETAL30SEP26FUT", "MCX", 15_000, 15_000, 15_000, 15_000, 1, now,
    )]
    market.update_time(now)
    providers.calendar_session.update_time(now)
    risk = RiskManager(config)
    trades = TradeManager(providers.execution, risk)
    trades.create_order(Order(
        "ENTRY-1",
        "GOLDPETAL30SEP26FUT",
        "MCX",
        OrderSide.BUY,
        1,
        position_type=PositionType.POSITIONAL,
    ))
    strategy = SimpleNamespace(
        context=SimpleNamespace(tick=None),
        on_tick=lambda tick: (_ for _ in ()).throw(AssertionError("entry evaluated")),
    )

    _process_symbols(
        providers,
        ["GOLDPETAL30SEP26FUT"],
        {"GOLDPETAL30SEP26FUT": strategy},
        trades,
        risk,
        {"GOLDPETAL30SEP26FUT"},
        PositionType.POSITIONAL,
        config,
    )

    position = trades.get_position("GOLDPETAL30SEP26FUT", "MCX")
    assert position.status == PositionStatus.CLOSED
    expiry_orders = [
        order for order in trades.get_orders() if order.intent == OrderIntent.EXIT
    ]
    assert len(expiry_orders) == 1
    assert expiry_orders[0].status == OrderStatus.FILLED
    assert expiry_orders[0].side == OrderSide.SELL
    with trades._audit.path.open(encoding="utf-8", newline="") as stream:
        events = list(csv.DictReader(stream))
    expiry_event = next(row for row in events if row["event"] == "EXPIRY_EXIT")
    assert expiry_event["details"].startswith(
        "expiry=2026-09-30;cutoff=2026-09-29T23:00:00+05:30"
    )


def test_open_derivative_without_expiry_alerts_and_blocks_entries(make_config, caplog) -> None:
    config = _expiry_config(make_config)
    now = datetime(2026, 9, 29, 12, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    calendar = CalendarSessionManager(config["session"])
    calendar.configure_mode("backtest")
    calendar.update_time(now)
    session = SimulatedSession()
    market = SimulatedMarketDataProvider(session, "MCX")
    market.set_tick(MarketTick("GOLDPETAL30SEP26FUT", "MCX", 15_000, 1, now))
    account = SimulatedAccountProvider(session, config["capital"])
    execution = SimulatedExecutionProvider(session, margin_pct=10)
    risk = RiskManager(config)
    trades = TradeManager(execution, risk)
    trades.create_order(Order(
        "ENTRY-1", "GOLDPETAL30SEP26FUT", "MCX", OrderSide.BUY, 1,
        position_type=PositionType.POSITIONAL,
    ))

    _process_symbols(
        ProviderBundle(market, account, execution, calendar),
        ["GOLDPETAL30SEP26FUT"], {}, trades, risk, set(),
        PositionType.POSITIONAL, config,
    )

    assert trades.get_position("GOLDPETAL30SEP26FUT", "MCX").status == PositionStatus.OPEN
    assert risk.kill_switch
    assert "Open derivative position GOLDPETAL30SEP26FUT has no expiry" in caplog.text
