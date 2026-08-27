# -*- coding: utf-8 -*-
"""
Created on Fri Aug 28 00:30:00 2026

@author: ashwe

Manual AngelOne and simulated provider check.
"""

from __future__ import annotations

from pathlib import Path

from autotick.interfaces.account import AccountProvider
from autotick.interfaces.execution import ExecutionProvider
from autotick.interfaces.market_data import MarketDataProvider
from autotick.models.market import MarketBar, MarketTick
from autotick.models.order import Order, OrderIntent, OrderSide, OrderType
from autotick.models.position import PositionType
from autotick.providers.brokers.angelone import (
    AngelOneAccountProvider,
    AngelOneExecutionProvider,
    AngelOneMarketDataProvider,
    AngelOneSession,
)
from autotick.providers.brokers.simulated import (
    SimulatedAccountProvider,
    SimulatedExecutionProvider,
    SimulatedMarketDataProvider,
    SimulatedSession,
)
from autotick.providers.session_pool import BrokerSession


ROOT_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = ROOT_DIR / "config" / "angelone_keys.env"

EXCHANGE = "NSE"
SYMBOLS = ("INFY-EQ", "RELIANCE-EQ", "TCS-EQ")
BAR_INTERVAL = "1m"
SIMULATED_CAPITAL = 100_000.0

# WARNING: True sends real intraday market BUY and SELL orders.
PLACE_LIVE_ORDERS = False
ORDER_SYMBOL = "INFY-EQ"
ORDER_QUANTITY = 1


def new_order(order_id: str, side: OrderSide) -> Order:
    return Order(
        order_id=order_id,
        symbol=ORDER_SYMBOL,
        exchange=EXCHANGE,
        side=side,
        quantity=ORDER_QUANTITY,
        order_type=OrderType.MARKET,
        intent=OrderIntent.ENTRY if side == OrderSide.BUY else OrderIntent.EXIT,
        position_type=PositionType.INTRADAY,
    )


def print_account(account: AccountProvider) -> None:
    print("connect account:", account.connect())
    print("get_balance:", account.get_balance())
    print("get_margin:", account.get_margin())
    print("get_buying_power:", account.get_buying_power())
    print("get_profile:", account.get_profile())


def print_market_data(
    market_data: MarketDataProvider,
) -> tuple[dict[str, MarketTick], dict[tuple[str, str], list[MarketBar]]]:
    print("connect market data:", market_data.connect())
    ticks: dict[str, MarketTick] = {}
    bars: dict[tuple[str, str], list[MarketBar]] = {}

    for symbol in SYMBOLS:
        tick = market_data.get_tick(symbol)
        candle_data = market_data.get_bars(symbol, BAR_INTERVAL)
        print(f"get_tick {symbol}:", tick)
        print(f"get_bars {symbol}:", candle_data)
        if tick is not None:
            ticks[symbol] = tick
        bars[(symbol, BAR_INTERVAL)] = candle_data

    return ticks, bars


def print_execution(
    execution: ExecutionProvider,
    place_orders: bool,
    buy_order_id: str = "",
    sell_order_id: str = "",
) -> None:
    if place_orders:
        buy_order = execution.place_order(new_order(buy_order_id, OrderSide.BUY))
        sell_order = execution.place_order(new_order(sell_order_id, OrderSide.SELL))
        print("place_order BUY:", buy_order)
        print("place_order SELL:", sell_order)
        print("get_order_status BUY:", execution.get_order_status(buy_order.order_id))
        print("get_order_status SELL:", execution.get_order_status(sell_order.order_id))
    else:
        print("place_order BUY: disabled")
        print("place_order SELL: disabled")
        print("get_order_status: disabled")

    print("get_orders:", execution.get_orders())
    print("get_positions:", execution.get_positions())
    print("get_holdings:", execution.get_holdings())
    print("get_trades:", execution.get_trades())


def disconnect(
    account: AccountProvider,
    market_data: MarketDataProvider,
    session: BrokerSession,
) -> None:
    print("disconnect market data:", market_data.disconnect())
    print("disconnect account:", account.disconnect())
    print("logout session:", session.logout())


def run_angelone() -> tuple[
    dict[str, MarketTick],
    dict[tuple[str, str], list[MarketBar]],
]:
    print("..... AngelOne start .....")
    session = AngelOneSession(str(CREDENTIALS_FILE))
    account = AngelOneAccountProvider(session)
    market_data = AngelOneMarketDataProvider(session, EXCHANGE)
    execution = AngelOneExecutionProvider(session)

    try:
        print_account(account)
        ticks, bars = print_market_data(market_data)
        print_execution(execution, PLACE_LIVE_ORDERS)
        return ticks, bars
    finally:
        disconnect(account, market_data, session)
        print("..... AngelOne end .....")


def run_simulated(
    ticks: dict[str, MarketTick],
    bars: dict[tuple[str, str], list[MarketBar]],
) -> None:
    print("..... Simulated start .....")
    session = SimulatedSession()
    account = SimulatedAccountProvider(session, SIMULATED_CAPITAL)
    market_data = SimulatedMarketDataProvider(session, EXCHANGE)
    execution = SimulatedExecutionProvider(session)

    for tick in ticks.values():
        print(f"set_tick {tick.symbol}:", market_data.set_tick(tick))
    for (symbol, interval), candle_data in bars.items():
        print(f"set_bars {symbol}:", market_data.set_bars(symbol, interval, candle_data))

    try:
        print_account(account)
        print_market_data(market_data)
        print_execution(
            execution,
            place_orders=ORDER_SYMBOL in ticks,
            buy_order_id="SIM-BUY",
            sell_order_id="SIM-SELL",
        )
    finally:
        disconnect(account, market_data, session)
        print("..... Simulated end .....")


def main() -> None:
    print("..... main start .....")
    ticks, bars = run_angelone()
    run_simulated(ticks, bars)
    print("..... main end .....")


if __name__ == "__main__":
    main()
