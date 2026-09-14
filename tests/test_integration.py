# -*- coding: utf-8 -*-
"""
Created on Sat Sep 12 19:28:09 2026

@author: ashwe
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from autotick.engine.risk_manager import RiskManager
from autotick.engine.trade_manager import TradeManager
from autotick.main import _process_symbols
from autotick.models.market import MarketBar, MarketTick
from autotick.models.order import OrderIntent, OrderSide, OrderStatus
from autotick.models.position import PositionStatus, PositionType
from autotick.models.signal import Signal, SignalType
from autotick.providers.brokers.angelone import (
    AngelOneAccountProvider,
    AngelOneExecutionProvider,
    AngelOneMarketDataProvider,
)
from autotick.providers.brokers.simulated import (
    SimulatedAccountProvider,
    SimulatedExecutionProvider,
    SimulatedMarketDataProvider,
    SimulatedSession,
)
from autotick.providers.factory import ProviderBundle, ProviderFactory
from autotick.providers.historical import HistoricalProvider
from autotick.strategy.base import Strategy
from autotick.strategy.context import StrategyContext


class _BuyStrategy(Strategy):
    def on_tick(self, tick: MarketTick) -> Signal:
        return Signal(tick.symbol, tick.exchange, SignalType.BUY, price=tick.ltp)


def _historical_market(start: datetime) -> HistoricalProvider:
    bars = [
        MarketBar("INFY-EQ", "NSE", 100, 102, 99, 101, 10, start),
        MarketBar("INFY-EQ", "NSE", 101, 108, 100, 107, 20, start + timedelta(minutes=1)),
    ]
    return HistoricalProvider({("INFY-EQ", "1m"): bars})


def _run_trade_flow(mode: str, config: dict) -> tuple:
    start = datetime(2026, 9, 12, 9, 15, tzinfo=timezone.utc)
    session = SimulatedSession()
    if mode == "paper":
        market = SimulatedMarketDataProvider(session)
        market.set_tick(MarketTick("INFY-EQ", "NSE", 101, 10, start))
    else:
        market = _historical_market(start)
        market.update_time(start)
        session.set_market_data(market)

    account = SimulatedAccountProvider(session, 100_000)
    execution = SimulatedExecutionProvider(session)
    providers = ProviderBundle(market, account, execution)
    risk = RiskManager(config)
    trades = TradeManager(execution, risk)
    strategy = _BuyStrategy()
    strategy.initialize(StrategyContext(market, "INFY-EQ"))
    strategies = {"INFY-EQ": strategy}
    entered: set[str] = set()

    market.connect()
    account.connect()
    market.subscribe(["INFY-EQ"])
    _process_symbols(
        providers, ["INFY-EQ"], strategies, trades, risk, entered,
        PositionType.POSITIONAL, config,
    )
    _process_symbols(
        providers, ["INFY-EQ"], strategies, trades, risk, entered,
        PositionType.POSITIONAL, config,
    )
    assert len(trades.get_orders()) == 1

    if mode == "paper":
        market.set_tick(MarketTick("INFY-EQ", "NSE", 107, 20, start))
    else:
        market.update_time(start + timedelta(minutes=1))
    _process_symbols(
        providers, ["INFY-EQ"], strategies, trades, risk, entered,
        PositionType.POSITIONAL, config,
    )

    position = trades.get_position("INFY-EQ", "NSE")
    orders = tuple(
        (order.side, order.quantity, order.status, order.intent)
        for order in trades.get_orders()
    )
    return orders, position.status, position.realized_pnl, account.get_balance(), risk.trade_count


def test_paper_backtest_replay_trade_flow_parity(make_config) -> None:
    results = {
        mode: _run_trade_flow(
            mode, make_config(mode, capital=100_000, quantity=10, max_trades=5)
        )
        for mode in ("paper", "backtest", "replay")
    }
    expected_orders = (
        (OrderSide.BUY, 10, OrderStatus.FILLED, OrderIntent.ENTRY),
        (OrderSide.SELL, 10, OrderStatus.FILLED, OrderIntent.EXIT),
    )
    assert results == {
        mode: (expected_orders, PositionStatus.CLOSED, 60, 100_060, 1)
        for mode in results
    }


def test_live_provider_wiring_is_offline(
    monkeypatch: pytest.MonkeyPatch, make_config
) -> None:
    session = object()
    monkeypatch.setattr(
        ProviderFactory,
        "_broker_session",
        classmethod(lambda cls, config: ("angelone", session)),
    )
    config = make_config("live", capital=100_000, quantity=10, max_trades=5) | {
        "market": {"exchange": "NSE"},
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
    }

    providers = ProviderFactory.create_bundle("live", config)
    assert isinstance(providers.market_data, AngelOneMarketDataProvider)
    assert isinstance(providers.account, AngelOneAccountProvider)
    assert isinstance(providers.execution, AngelOneExecutionProvider)
    assert providers.broker_session is session
