# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 22:07:58 2026

@author: ashwe
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from uuid import uuid4

from autotick.interfaces.execution import ExecutionProvider
from autotick.models.order import Order, OrderSide, OrderStatus
from autotick.models.position import Position, PositionStatus, PositionType
from autotick.models.trade import Trade


class TradeManager:
    """Own normalized order and position lifecycle."""

    _TRANSITIONS = {
        OrderStatus.NEW: {OrderStatus.VALIDATED},
        OrderStatus.VALIDATED: {OrderStatus.SUBMITTED, OrderStatus.REJECTED},
        OrderStatus.SUBMITTED: {
            OrderStatus.OPEN,
            OrderStatus.PARTIAL,
            OrderStatus.FILLED,
            OrderStatus.REJECTED,
            OrderStatus.CANCELLED,
            OrderStatus.EXPIRED,
        },
        OrderStatus.OPEN: {
            OrderStatus.PARTIAL,
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.EXPIRED,
        },
        OrderStatus.PARTIAL: {
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.EXPIRED,
        },
    }

    def __init__(self, execution: ExecutionProvider) -> None:
        self.execution = execution
        self._orders: dict[str, Order] = {}
        self._positions: dict[tuple[str, str], Position] = {}
        self._trades: dict[str, Trade] = {}

    def create_order(self, order: Order) -> Order:
        validated = self.update_order_state(order, OrderStatus.VALIDATED)
        submitted = self.execution.place_order(validated)
        self.track_order(submitted)
        return submitted

    def track_order(self, order: Order) -> None:
        if order.order_id:
            self._orders[order.order_id] = order

    def modify_order(self, order: Order) -> Order:
        if order.order_id not in self._orders:
            raise KeyError(f"Unknown order_id: {order.order_id}")
        updated = self.execution.modify_order(order)
        updated.status = self._orders[order.order_id].status
        self.track_order(updated)
        return updated

    def cancel_order(self, order_id: str) -> bool:
        if order_id not in self._orders:
            return False
        cancelled = self.execution.cancel_order(order_id)
        if cancelled:
            self.update_order_state(self._orders[order_id], OrderStatus.CANCELLED)
        return cancelled

    def update_order_state(self, order: Order, status: OrderStatus) -> Order:
        if order.status == status:
            return order
        if status not in self._TRANSITIONS.get(order.status, set()):
            raise ValueError(f"Invalid order transition: {order.status} -> {status}")
        updated = replace(order, status=status, status_updated_at=datetime.now())
        self.track_order(updated)
        return updated

    def get_order(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    def get_orders(self) -> list[Order]:
        return list(self._orders.values())

    def reconcile_orders(self) -> None:
        for broker_order in self.execution.get_orders():
            current = self._orders.get(broker_order.order_id)
            if current is None:
                self.track_order(broker_order)
            elif current.status != broker_order.status:
                self.update_order_state(current, broker_order.status)

    @staticmethod
    def _position_key(position: Position) -> tuple[str, str]:
        return position.symbol, position.exchange

    def open_position(self, position: Position) -> Position:
        opened = replace(position, status=PositionStatus.OPEN)
        self._positions[self._position_key(opened)] = opened
        return opened

    def update_position(self, position: Position) -> Position:
        if position.quantity == 0:
            position = replace(position, unrealized_pnl=0.0, status=PositionStatus.CLOSED)
        else:
            position = replace(position, status=PositionStatus.OPEN)
        self._positions[self._position_key(position)] = position
        return position

    def close_position(self, symbol: str, exchange: str) -> Position:
        key = (symbol, exchange)
        position = self._positions.get(key)
        if position is None:
            raise KeyError(f"Unknown position: {symbol}:{exchange}")
        closed = replace(position, quantity=0, unrealized_pnl=0.0, status=PositionStatus.CLOSED)
        self._positions[key] = closed
        return closed

    def square_off_intraday(self) -> list[Order]:
        """Submit exit orders only for open intraday positions."""
        orders = []
        for key, position in list(self._positions.items()):
            if position.quantity == 0 or position.position_type != PositionType.INTRADAY:
                continue
            self._positions[key] = replace(position, status=PositionStatus.EXIT_PENDING)
            orders.append(self.create_order(Order(
                order_id=str(uuid4()),
                symbol=position.symbol,
                exchange=position.exchange,
                side=OrderSide.SELL if position.quantity > 0 else OrderSide.BUY,
                quantity=abs(position.quantity),
            )))
        return orders

    def get_positions(self) -> list[Position]:
        return list(self._positions.values())

    def get_trades(self) -> list[Trade]:
        return list(self._trades.values())

    def realized_pnl(self) -> float:
        return sum(position.realized_pnl for position in self._positions.values())

    def unrealized_pnl(self) -> float:
        return sum(position.unrealized_pnl for position in self._positions.values())

    def total_exposure(self) -> float:
        return sum(abs(position.quantity * position.average_price) for position in self._positions.values())

    def reconcile_positions(self) -> None:
        broker_positions = self.execution.get_positions()
        active_keys = set()

        for position in broker_positions:
            self.update_position(position)
            if position.quantity != 0:
                active_keys.add(self._position_key(position))

        for key, position in list(self._positions.items()):
            if position.status == PositionStatus.OPEN and key not in active_keys:
                self.close_position(*key)

        self._trades = {trade.trade_id: trade for trade in self.execution.get_trades()}
