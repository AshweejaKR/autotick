# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 22:07:58 2026

@author: ashwe
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from autotick.interfaces.execution import ExecutionProvider
from autotick.models.order import Order, OrderStatus


class TradeManager:
    """Own normalized order lifecycle and broker reconciliation."""

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

    def create_order(self, order: Order) -> Order:
        """Validate, submit, and track one new order."""
        validated = self.update_order_state(order, OrderStatus.VALIDATED)
        submitted = self.execution.place_order(validated)
        self.track_order(submitted)
        return submitted

    def track_order(self, order: Order) -> None:
        """Track the latest normalized state for one order."""
        if order.order_id:
            self._orders[order.order_id] = order

    def modify_order(self, order: Order) -> Order:
        """Modify a tracked active order."""
        if order.order_id not in self._orders:
            raise KeyError(f"Unknown order_id: {order.order_id}")
        updated = self.execution.modify_order(order)
        updated.status = self._orders[order.order_id].status
        self.track_order(updated)
        return updated

    def cancel_order(self, order_id: str) -> bool:
        """Cancel one tracked active order."""
        if order_id not in self._orders:
            return False
        cancelled = self.execution.cancel_order(order_id)
        if cancelled:
            self.update_order_state(self._orders[order_id], OrderStatus.CANCELLED)
        return cancelled

    def update_order_state(self, order: Order, status: OrderStatus) -> Order:
        """Apply one valid, idempotent order-state transition."""
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
        """Refresh tracked orders from the execution provider."""
        for broker_order in self.execution.get_orders():
            current = self._orders.get(broker_order.order_id)
            if current is None:
                self.track_order(broker_order)
            elif current.status != broker_order.status:
                self.update_order_state(current, broker_order.status)
