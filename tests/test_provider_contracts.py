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
from autotick.providers.brokers.angelone.session import AngelOneSession
from autotick.providers.brokers.simulated import (
    SimulatedAccountProvider,
    SimulatedExecutionProvider,
    SimulatedMarketDataProvider,
    SimulatedSession,
)
from autotick.providers.factory import ProviderFactory
from autotick.providers.historical import HistoricalProvider
from autotick.providers.session_pool import (
    BrokerAuthenticationError,
    BrokerConnectionError,
)


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
    assert account.get_balance() == 1_020

    market.set_tick(MarketTick("INFY-EQ", "NSE", 100, 20, now))
    short = execution.place_order(Order("SELL-1", "INFY-EQ", "NSE", OrderSide.SELL, 1))
    assert short.status == OrderStatus.FILLED
    assert execution.get_positions()[0].quantity == -1
    assert account.get_balance() == 920

    market.set_tick(MarketTick("INFY-EQ", "NSE", 90, 20, now))
    execution.square_off()
    assert execution.get_positions()[0].quantity == 0
    assert execution.get_pnl() == 30
    assert account.get_balance() == 1_030
    assert execution.get_holdings() == []

    execution.cancel_all()
    market.unsubscribe(["INFY-EQ"])
    market.disconnect()
    account.disconnect()


class _FakeClient:
    def __init__(self) -> None:
        self.placed_orders: list[dict] = []
        self.margin_requests: list[dict] = []
        self.charge_requests: list[dict] = []

    def rmsLimit(self) -> dict:
        return {"status": True, "data": {"availablecash": "1000", "availablelimitmargin": "5000"}}

    def getMarginApi(self, params: dict) -> dict:
        self.margin_requests.append(params)
        quantity = params["positions"][0]["qty"]
        return {"status": True, "data": {"totalMarginRequired": quantity * 1450}}

    def estimateCharges(self, params: dict) -> dict:
        self.charge_requests.append(params)
        quantity = int(params["orders"][0]["quantity"])
        return {"status": True, "data": {"summary": {"total_charges": quantity * 10}}}

    def getProfile(self, refresh_token: str) -> dict:
        return {"status": True, "data": {"clientcode": "C1", "name": "Test"}}

    def ltpData(self, exchange: str, symbol: str, token: str) -> dict:
        return {"status": True, "data": {"ltp": 100, "tradeVolume": 10}}

    def getCandleData(self, params: dict) -> dict:
        return {"status": True, "data": [["2026-09-12T09:15:00+05:30", 99, 101, 98, 100, 1000]]}

    def placeOrderFullResponse(self, params: dict) -> dict:
        self.placed_orders.append(params)
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
    assert session.client.placed_orders[-1]["price"] == 0
    assert execution.modify_order(order).status == OrderStatus.SUBMITTED
    assert execution.cancel_order("A2") is True
    market.unsubscribe(["INFY-EQ"])
    market.disconnect()
    account.disconnect()


def test_angelone_trade_time_and_auth_classification() -> None:
    trade = AngelOneExecutionProvider._to_trade({
        "tradeid": "T1", "orderid": "A1", "tradingsymbol": "INFY-EQ",
        "exchange": "NSE", "transactiontype": "BUY", "quantity": "1",
        "fillprice": "100", "filltime": "09:16:00",
    })

    assert trade.timestamp.strftime("%H:%M:%S") == "09:16:00"
    assert AngelOneSession._is_auth_error({"status": False, "errorcode": "AG8001"})
    assert not AngelOneSession._is_auth_error(
        {"status": False, "message": "Invalid symbol token"}
    )


def test_angelone_entry_uses_broker_margin_and_charges() -> None:
    session = _FakeSession()
    execution = AngelOneExecutionProvider(session)

    order = execution.place_order(
        Order("", "GOLDPETAL30SEP26FUT", "MCX", OrderSide.BUY, 4, price=15_000)
    )

    assert order.status == OrderStatus.SUBMITTED
    assert order.quantity == 3
    assert session.client.placed_orders[-1]["quantity"] == 3
    assert session.client.margin_requests[-1]["positions"][0]["orderType"] == "MARKET"
    assert session.client.charge_requests[-1]["orders"][0]["symbol_name"] == "GOLDPETAL"


def test_simulated_margin_allows_goldpetal_paper_entry() -> None:
    session = SimulatedSession()
    market = SimulatedMarketDataProvider(session, "MCX")
    market.set_tick(MarketTick("GOLDPETAL", "MCX", 15_000, 1, datetime.now(timezone.utc)))
    account = SimulatedAccountProvider(session, 5_000)
    execution = SimulatedExecutionProvider(session, margin_pct=10)

    entry = execution.place_order(Order("MCX-1", "GOLDPETAL", "MCX", OrderSide.BUY, 1))
    assert entry.status == OrderStatus.FILLED
    assert account.get_balance() == 3_500

    execution.square_off()
    assert account.get_balance() == 5_000


class _FailedReadClient:
    def position(self) -> dict:
        return {"status": False, "message": "service unavailable", "data": None}


class _FailedReadSession:
    def __init__(self) -> None:
        self.client = _FailedReadClient()

    def call(self, function, *args, **kwargs):
        return function(*args, **kwargs)


class _EmptyReadClient:
    def orderBook(self) -> dict:
        return {"status": True, "message": "SUCCESS", "data": None}

    position = holding = tradeBook = orderBook


class _EmptyReadSession:
    def __init__(self) -> None:
        self.client = _EmptyReadClient()

    def call(self, function, *args, **kwargs):
        return function(*args, **kwargs)


class _NoneDataClient:
    def getProfile(self, refresh_token: str) -> dict:
        return {"status": True, "message": "SUCCESS", "data": None}

    def rmsLimit(self) -> dict:
        return {"status": True, "message": "SUCCESS", "data": None}

    def generateSession(self, client_id: str, password: str, totp: str) -> dict:
        return {"status": True, "message": "SUCCESS", "data": None}

    def generateToken(self, refresh_token: str) -> dict:
        return {"status": True, "message": "SUCCESS", "data": None}


class _NoneDataSession:
    def __init__(self) -> None:
        self.client = _NoneDataClient()
        self.refresh_token = "refresh"

    def call(self, function, *args, **kwargs):
        return function(*args, **kwargs)


def test_angelone_successful_empty_reads_return_empty_lists() -> None:
    execution = AngelOneExecutionProvider(_EmptyReadSession())

    assert execution.get_orders() == []
    assert execution.get_positions() == []
    assert execution.get_holdings() == []
    assert execution.get_trades() == []


def test_angelone_required_account_data_cannot_be_none() -> None:
    session = _NoneDataSession()
    account = AngelOneAccountProvider(session)

    with pytest.raises(BrokerConnectionError, match="profile read returned invalid data"):
        account.get_profile()
    with pytest.raises(BrokerConnectionError, match="RMS read returned invalid data"):
        account.get_balance()


def test_angelone_required_margin_data_cannot_be_none() -> None:
    execution = AngelOneExecutionProvider(_NoneDataSession())

    with pytest.raises(BrokerConnectionError, match="RMS margin read returned invalid data"):
        execution._available_margin()


@pytest.mark.parametrize("operation", ["login", "refresh"])
def test_angelone_session_data_cannot_be_none(operation: str) -> None:
    session = object.__new__(AngelOneSession)
    session.client = _NoneDataClient()
    session.client_id = "C1"
    session.password = "password"
    session.totp_secret = "JBSWY3DPEHPK3PXP"
    session.refresh_token = "refresh"
    session._connected = False
    session._throttle = lambda: None

    with pytest.raises(BrokerAuthenticationError, match="invalid session data"):
        getattr(session, operation)()
    assert session.is_connected() is False


def test_angelone_failed_position_read_does_not_look_empty() -> None:
    execution = AngelOneExecutionProvider(_FailedReadSession())

    with pytest.raises(BrokerConnectionError, match="positions read failed"):
        execution.get_positions()
