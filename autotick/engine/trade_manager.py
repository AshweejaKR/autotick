# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 22:07:58 2026

@author: ashwe
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from uuid import uuid4

from autotick.engine.risk_manager import RiskManager
from autotick.interfaces.execution import ExecutionProvider
from autotick.models.order import Order, OrderIntent, OrderSide, OrderStatus
from autotick.models.position import Position, PositionStatus, PositionType
from autotick.models.trade import Trade


@dataclass(slots=True)
class _ExitLevels:
    stop_loss: float
    target: float
    highest_price: float
    trailing_stop: float | None = None


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

    def __init__(
        self,
        execution: ExecutionProvider,
        risk_manager: RiskManager | None = None,
    ) -> None:
        self.execution = execution
        self.risk_manager = risk_manager
        self._orders: dict[str, Order] = {}
        self._positions: dict[tuple[str, str], Position] = {}
        self._trades: dict[str, Trade] = {}
        self._exit_levels: dict[tuple[str, str], _ExitLevels] = {}

    def create_order(self, order: Order) -> Order:
        validated = self.update_order_state(order, OrderStatus.VALIDATED)
        provider_order = self.execution.place_order(validated)
        submitted = self.update_order_state(
            replace(provider_order, status=OrderStatus.VALIDATED),
            OrderStatus.SUBMITTED,
        )
        if provider_order.status == OrderStatus.SUBMITTED:
            return submitted
        return self.update_order_state(submitted, provider_order.status)

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
        if status == OrderStatus.FILLED:
            if updated.intent == OrderIntent.ENTRY:
                if self.risk_manager is not None:
                    self.risk_manager.record_entry()
                self._open_filled_entry(updated)
            else:
                self._close_filled_exit(updated)
        elif (
            updated.intent == OrderIntent.EXIT
            and status in {
                OrderStatus.REJECTED,
                OrderStatus.CANCELLED,
                OrderStatus.EXPIRED,
            }
        ):
            key = (updated.symbol, updated.exchange)
            position = self._positions.get(key)
            if position is not None and position.status == PositionStatus.EXIT_PENDING:
                self._positions[key] = replace(position, status=PositionStatus.OPEN)
        return updated

    def get_order(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    def get_orders(self) -> list[Order]:
        return list(self._orders.values())

    def reconcile_orders(self) -> list[Order]:
        pending = {
            order_id: order
            for order_id, order in self._orders.items()
            if order.status in {
                OrderStatus.SUBMITTED,
                OrderStatus.OPEN,
                OrderStatus.PARTIAL,
            }
        }
        if not pending:
            return []

        changed = []
        for broker_order in self.execution.get_orders():
            current = pending.get(broker_order.order_id)
            if current is None or current.status == broker_order.status:
                continue
            price = broker_order.price or current.price
            changed.append(
                self.update_order_state(
                    replace(current, price=price),
                    broker_order.status,
                )
            )
        return changed

    def monitor_exit(
        self,
        symbol: str,
        exchange: str,
        price: float,
    ) -> tuple[Order, str] | None:
        """Submit an exit when fixed or trailing protection is hit."""
        key = (symbol, exchange)
        position = self._positions.get(key)
        levels = self._exit_levels.get(key)
        if (
            price <= 0
            or position is None
            or position.status != PositionStatus.OPEN
            or levels is None
            or self.risk_manager is None
        ):
            return None

        reason = None
        if price <= levels.stop_loss:
            reason = "STOP_LOSS"
        elif levels.trailing_stop is not None:
            if price > levels.highest_price:
                levels.highest_price = price
                levels.trailing_stop = self.risk_manager.trailing_stop(price)
            if price <= levels.trailing_stop:
                reason = "TRAILING_STOP"
        elif price >= levels.target:
            if self.risk_manager.trailing_pct > 0:
                levels.highest_price = max(levels.highest_price, price)
                levels.trailing_stop = self.risk_manager.trailing_stop(
                    levels.highest_price
                )
                return None
            reason = "TARGET"

        if reason is None:
            return None
        return self._submit_exit(position, price), reason

    def _open_filled_entry(self, order: Order) -> None:
        price = float(order.price or 0)
        if price <= 0:
            return
        position = self.open_position(
            Position(
                symbol=order.symbol,
                exchange=order.exchange,
                quantity=order.quantity,
                average_price=price,
                position_type=order.position_type,
            )
        )
        if self.risk_manager is not None:
            self._exit_levels[self._position_key(position)] = _ExitLevels(
                stop_loss=self.risk_manager.stop_loss(price),
                target=self.risk_manager.target(price),
                highest_price=price,
            )

    def _close_filled_exit(self, order: Order) -> None:
        key = (order.symbol, order.exchange)
        if key in self._positions:
            self.close_position(*key)
        self._exit_levels.pop(key, None)

    def _submit_exit(self, position: Position, price: float) -> Order:
        order = self.create_order(
            Order(
                order_id=str(uuid4()),
                symbol=position.symbol,
                exchange=position.exchange,
                side=OrderSide.SELL if position.quantity > 0 else OrderSide.BUY,
                quantity=abs(position.quantity),
                price=price,
                intent=OrderIntent.EXIT,
                position_type=position.position_type,
            )
        )
        if order.status in {
            OrderStatus.SUBMITTED,
            OrderStatus.OPEN,
            OrderStatus.PARTIAL,
        }:
            key = self._position_key(position)
            self._positions[key] = replace(
                position,
                status=PositionStatus.EXIT_PENDING,
            )
        return order

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
                intent=OrderIntent.EXIT,
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
