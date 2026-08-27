# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 19:56:33 2026

@author: ashwe
"""

from __future__ import annotations

from dataclasses import replace

from autotick.interfaces.execution import ExecutionProvider
from autotick.models.order import Order, OrderStatus, OrderType
from autotick.models.position import Position
from autotick.models.trade import Trade
from autotick.providers.brokers.simulated.session import SimulatedSession


class SimulatedExecutionProvider(ExecutionProvider):
    """Simple in-memory execution provider for simulated trading."""

    def __init__(self, session: SimulatedSession) -> None:
        self.session = session
        self._orders: dict[str, Order] = {}
        self._positions: list[Position] = []
        self._holdings: list[Position] = []
        self._trades: list[Trade] = []
        self._pnl = 0.0

    def place_order(self, order: Order) -> Order:
        market_data = self.session.market_data
        if order.order_type == OrderType.MARKET and market_data is not None:
            tick = market_data.get_tick(order.symbol)
            if tick is None or tick.ltp is None or tick.ltp <= 0:
                raise RuntimeError(f"No market price for {order.symbol}")
            submitted = replace(order, price=float(tick.ltp), status=OrderStatus.FILLED)
        else:
            submitted = replace(order, status=OrderStatus.SUBMITTED)
        self._orders[submitted.order_id] = submitted
        return submitted

    def modify_order(self, order: Order) -> Order:
        if order.order_id not in self._orders:
            raise KeyError(f"Unknown order_id: {order.order_id}")
        self._orders[order.order_id] = order
        return order

    def cancel_order(self, order_id: str) -> bool:
        order = self._orders.get(order_id)
        if order is None or order.status == OrderStatus.FILLED:
            return False
        self._orders[order_id] = replace(order, status=OrderStatus.CANCELLED)
        return True

    def cancel_all(self) -> None:
        for order_id in list(self._orders):
            self.cancel_order(order_id)

    def get_order(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    def get_order_status(self, order_id: str) -> OrderStatus | None:
        order = self.get_order(order_id)
        return order.status if order else None

    def get_orders(self) -> list[Order]:
        return list(self._orders.values())

    def get_positions(self) -> list[Position]:
        return list(self._positions)

    def get_holdings(self) -> list[Position]:
        return list(self._holdings)

    def get_trades(self) -> list[Trade]:
        return list(self._trades)

    def get_pnl(self) -> float:
        return self._pnl

    def square_off(self) -> None:
        self._positions.clear()
