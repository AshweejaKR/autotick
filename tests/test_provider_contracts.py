# -*- coding: utf-8 -*-
"""
Created on Sat Sep 12 19:28:09 2026

@author: ashwe
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from autotick.models.account import Account
from autotick.models.market import MarketBar, MarketTick
from autotick.models.order import Order, OrderSide, OrderStatus, OrderType
from autotick.models.position import Position
from autotick.models.trade import Trade
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
from autotick.providers.factory import ProviderFactory
from autotick.providers.historical import HistoricalProvider


def _bar(timestamp: datetime, close: float) -> MarketBar:
    return MarketBar("INFY-EQ", "NSE", close - 1, close + 1, close - 2, close, 100, timestamp)


@pytest.mark.parametrize(
    ("mode", "market", "account", "execution", "timing"),
    [
        ("live", "broker", "broker", "broker", "realtime"),
        ("paper", "broker", "simulated", "simulated", "realtime"),
        ("backtest", "historical", "simulated", "simulated", "fast"),
        ("replay", "historical", "simulated", "simulated", "replay"),
    ],
)
def test_mode_contract(mode: str, market: str, account: str, execution: str, timing: str) -> None:
    mapping = ProviderFactory.resolve_mode(mode)
    assert (mapping.market_data, mapping.account, mapping.execution, mapping.session_timing) == (
        market,
        account,
        execution,
        timing,
    )


def test_historical_market_data_contract() -> None:
    start = datetime(2026, 9, 11, 9, 15, tzinfo=timezone.utc)
    bars = [_bar(start, 100), _bar(start + timedelta(minutes=1), 101)]
    provider = HistoricalProvider({("INFY-EQ", "1m"): bars})
    provider.connect()
    provider.subscribe(["INFY-EQ"])
    provider.update_time(bars[-1].timestamp)

    tick = provider.get_tick("INFY-EQ")
    assert isinstance(tick, MarketTick) and tick.ltp == 101
    assert provider.get_bars("INFY-EQ", "1m") == bars
    provider.unsubscribe(["INFY-EQ"])
    provider.disconnect()


def test_simulated_provider_contracts() -> None:
    now = datetime(2026, 9, 12, tzinfo=timezone.utc)
    session = SimulatedSession()
    market = SimulatedMarketDataProvider(session)
    account = SimulatedAccountProvider(session, 1_000)
    execution = SimulatedExecutionProvider(session)
    market.connect()
    account.connect()
    market.subscribe(["INFY-EQ"])
    market.set_tick(MarketTick("INFY-EQ", "NSE", 100, 10, now))
    market.set_bars("INFY-EQ", "1m", [_bar(now, 100)])

    assert isinstance(market.get_tick("INFY-EQ"), MarketTick)
    assert isinstance(market.get_bars("INFY-EQ", "1m", now, now)[0], MarketBar)
    assert isinstance(account.get_profile(), Account)
    assert account.get_balance() == 1_000

    filled = execution.place_order(Order("BUY-1", "INFY-EQ", "NSE", OrderSide.BUY, 2))
    assert filled.status == OrderStatus.FILLED
    assert isinstance(execution.get_positions()[0], Position)
    assert isinstance(execution.get_trades()[0], Trade)
    assert account.get_balance() == 800

    pending = execution.place_order(
        Order("LIMIT-1", "INFY-EQ", "NSE", OrderSide.BUY, 1, OrderType.LIMIT, 90)
    )
    assert execution.modify_order(replace(pending, price=91)).price == 91
    assert execution.cancel_order("LIMIT-1") is True
    assert execution.get_order_status("LIMIT-1") == OrderStatus.CANCELLED

    market.set_tick(MarketTick("INFY-EQ", "NSE", 110, 20, now))
    execution.square_off()
    assert execution.get_pnl() == 20
    assert execution.get_holdings() == []
    execution.cancel_all()
    market.unsubscribe(["INFY-EQ"])
    market.disconnect()
    account.disconnect()


class _FakeClient:
    def rmsLimit(self) -> dict:
        return {"status": True, "data": {"availablecash": "1000", "availablelimitmargin": "800"}}

    def getProfile(self, refresh_token: str) -> dict:
        return {"status": True, "data": {"clientcode": "C1", "name": "Test"}}

    def ltpData(self, exchange: str, symbol: str, token: str) -> dict:
        return {"status": True, "data": {"ltp": 100, "tradeVolume": 10}}

    def getCandleData(self, params: dict) -> dict:
        return {"status": True, "data": [["2026-09-12T09:15:00+05:30", 99, 101, 98, 100, 1000]]}

    def placeOrderFullResponse(self, params: dict) -> dict:
        return {"status": True, "data": {"orderid": "A2"}}

    def modifyOrder(self, params: dict) -> dict:
        return {"status": True}

    def cancelOrder(self, order_id: str, variety: str) -> dict:
        return {"status": True}

    def orderBook(self) -> dict:
        return {"status": True, "data": [{
            "orderid": "A1", "tradingsymbol": "INFY-EQ", "exchange": "NSE",
            "transactiontype": "BUY", "quantity": "1", "averageprice": "100",
            "orderstatus": "complete", "producttype": "DELIVERY",
        }]}

    def position(self) -> dict:
        return {"status": True, "data": [{
            "tradingsymbol": "INFY-EQ", "exchange": "NSE", "netqty": "1",
            "averageprice": "100", "realised": "5", "unrealised": "2",
            "producttype": "DELIVERY",
        }]}

    def holding(self) -> dict:
        return self.position()

    def tradeBook(self) -> dict:
        return {"status": True, "data": [{
            "tradeid": "T1", "orderid": "A1", "tradingsymbol": "INFY-EQ",
            "exchange": "NSE", "transactiontype": "BUY", "quantity": "1",
            "fillprice": "100", "filltime": "2026-09-12T09:16:00",
        }]}


class _FakeSession:
    def __init__(self) -> None:
        self.client = _FakeClient()
        self.refresh_token = "refresh"
        self.connected = False

    def call(self, function, *args, **kwargs):
        return function(*args, **kwargs)

    def call_once(self, function, *args, **kwargs):
        return function(*args, **kwargs)

    def login(self) -> None:
        self.connected = True

    def is_connected(self) -> bool:
        return self.connected

    def get_instrument(self, symbol: str, exchange: str) -> tuple[str, str]:
        return symbol, "123"

    def get_token(self, symbol: str, exchange: str) -> str:
        return "123"


def test_angelone_provider_contracts_offline() -> None:
    session = _FakeSession()
    account = AngelOneAccountProvider(session, 1_000)
    market = AngelOneMarketDataProvider(session)
    execution = AngelOneExecutionProvider(session)
    account.connect()
    market.connect()
    market.subscribe(["INFY-EQ"])

    assert isinstance(account.get_profile(), Account)
    assert account.get_balance() == 1_000
    assert isinstance(market.get_tick("INFY-EQ"), MarketTick)
    assert isinstance(market.get_bars("INFY-EQ", "1m")[0], MarketBar)
    assert isinstance(execution.get_orders()[0], Order)
    assert isinstance(execution.get_positions()[0], Position)
    assert isinstance(execution.get_holdings()[0], Position)
    assert isinstance(execution.get_trades()[0], Trade)
    assert execution.get_pnl() == 7

    order = Order("", "INFY-EQ", "NSE", OrderSide.BUY, 1)
    assert execution.place_order(order).status == OrderStatus.SUBMITTED
    assert execution.modify_order(order).status == OrderStatus.SUBMITTED
    assert execution.cancel_order("A2") is True
    market.unsubscribe(["INFY-EQ"])
    market.disconnect()
    account.disconnect()
