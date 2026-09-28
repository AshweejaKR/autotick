from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from autotick.engine.expiry import expiry_cutoff, resolve_expiry_state
from autotick.engine.market_session import CalendarSessionManager
from autotick.engine.risk_manager import RiskManager
from autotick.engine.trade_manager import TradeManager
from autotick.main import _process_symbols
from autotick.models.market import ContractInfo, MarketTick
from autotick.models.order import Order, OrderIntent, OrderSide, OrderStatus
from autotick.models.position import PositionStatus, PositionType
from autotick.providers.brokers.angelone.session import AngelOneSession
from autotick.providers.brokers.simulated import (
    SimulatedAccountProvider,
    SimulatedExecutionProvider,
    SimulatedMarketDataProvider,
    SimulatedSession,
)
from autotick.providers.factory import ProviderBundle


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


def test_process_symbols_closes_position_at_expiry_cutoff(make_config) -> None:
    config = _expiry_config(make_config)
    now = datetime(2026, 9, 29, 23, 1, tzinfo=ZoneInfo("Asia/Kolkata"))
    calendar = CalendarSessionManager(config["session"])
    calendar.configure_mode("backtest")
    calendar.update_time(now)
    session = SimulatedSession()
    market = SimulatedMarketDataProvider(session, "MCX")
    market.get_contract = lambda symbol: ContractInfo(
        symbol, "MCX", "FUTCOM", date(2026, 9, 30)
    )
    market.set_tick(MarketTick("GOLDPETAL30SEP26FUT", "MCX", 15_000, 1, now))
    account = SimulatedAccountProvider(session, config["capital"])
    execution = SimulatedExecutionProvider(session, margin_pct=10)
    risk = RiskManager(config)
    trades = TradeManager(execution, risk)
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
        ProviderBundle(market, account, execution, calendar),
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
    audit_path = (
        Path(config["reports"]["output_dir"])
        / "simulated_tester_test_paper_audit.csv"
    )
    with audit_path.open(encoding="utf-8", newline="") as stream:
        events = list(csv.DictReader(stream))
    expiry_event = next(row for row in events if row["event"] == "EXPIRY_EXIT")
    assert expiry_event["details"].startswith(
        "expiry=2026-09-30;cutoff=2026-09-29T23:00:00+05:30"
    )
