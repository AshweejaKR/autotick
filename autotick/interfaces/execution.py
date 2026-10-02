# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 18:23:38 2026

@author: ashwe
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from autotick.models.order import Order, OrderStatus
from autotick.models.position import Position
from autotick.models.trade import Trade


class ExecutionProvider(ABC):
    """Template contract for order execution providers."""

    @abstractmethod
    def place_order(self, order: Order) -> Order:
        """Submit an order and return its normalized state."""

    @abstractmethod
    def modify_order(self, order: Order) -> Order:
        """Modify an existing order."""

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel one order."""

    @abstractmethod
    def cancel_all(self) -> None:
        """Cancel all open orders."""

    @abstractmethod
    def get_order(self, order_id: str) -> Order | None:
        """Return one normalized order."""

    @abstractmethod
    def get_order_status(self, order_id: str) -> OrderStatus | None:
        """Return the current status for an order."""

    @abstractmethod
    def get_orders(self) -> list[Order]:
        """Return normalized orders."""

    @abstractmethod
    def get_positions(self) -> list[Position]:
        """Return normalized positions."""

    @abstractmethod
    def get_holdings(self) -> list[Position]:
        """Return normalized holdings."""

    @abstractmethod
    def get_trades(self) -> list[Trade]:
        """Return normalized trades."""

    @abstractmethod
    def get_pnl(self) -> float:
        """Return current profit and loss."""

    @abstractmethod
    def square_off(self) -> None:
        """Square off open positions."""
