# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 19:56:33 2026

@author: ashwe
"""

from __future__ import annotations

from datetime import datetime

from autotick.interfaces.execution import ExecutionProvider
from autotick.models.order import Order, OrderSide, OrderStatus, OrderType
from autotick.models.position import Position
from autotick.models.trade import Trade
from autotick.providers.brokers.angelone.session import AngelOneSession


class AngelOneExecutionProvider(ExecutionProvider):
    """AngelOne SmartAPI execution adapter."""

    def __init__(self, session: AngelOneSession) -> None:
        self.session = session

    def place_order(self, order: Order) -> Order:
        order_id = self.session.client.placeOrder(self._order_params(order))
        if not order_id:
            order.status = OrderStatus.REJECTED
            return order
        order.order_id = str(order_id)
        order.status = OrderStatus.SUBMITTED
        return order

    def modify_order(self, order: Order) -> Order:
        params = self._order_params(order)
        params["orderid"] = order.order_id
        response = self.session.client.modifyOrder(params)
        if response and response.get("status"):
            order.status = OrderStatus.SUBMITTED
        return order

    def cancel_order(self, order_id: str) -> bool:
        response = self.session.client.cancelOrder(order_id, "NORMAL")
        return bool(response and response.get("status"))

    def cancel_all(self) -> None:
        for order in self.get_orders():
            if order.status in {OrderStatus.SUBMITTED, OrderStatus.OPEN, OrderStatus.PARTIAL}:
                self.cancel_order(order.order_id)

    def get_order(self, order_id: str) -> Order | None:
        return next((order for order in self.get_orders() if order.order_id == order_id), None)

    def get_order_status(self, order_id: str) -> OrderStatus | None:
        order = self.get_order(order_id)
        return order.status if order else None

    def get_orders(self) -> list[Order]:
        response = self.session.client.orderBook()
        return [self._to_order(item) for item in (response.get("data") or [])]

    def get_positions(self) -> list[Position]:
        response = self.session.client.position()
        return [self._to_position(item) for item in (response.get("data") or [])]

    def get_holdings(self) -> list[Position]:
        response = self.session.client.holding()
        return [self._to_position(item) for item in (response.get("data") or [])]

    def get_trades(self) -> list[Trade]:
        response = self.session.client.tradeBook()
        return [self._to_trade(item) for item in (response.get("data") or [])]

    def get_pnl(self) -> float:
        return sum(position.realized_pnl + position.unrealized_pnl for position in self.get_positions())

    def square_off(self) -> None:
        for position in self.get_positions():
            if position.quantity == 0:
                continue
            self.place_order(
                Order(
                    order_id="",
                    symbol=position.symbol,
                    exchange=position.exchange,
                    side=OrderSide.SELL if position.quantity > 0 else OrderSide.BUY,
                    quantity=abs(position.quantity),
                )
            )

    def _order_params(self, order: Order) -> dict[str, object]:
        return {
            "variety": "NORMAL",
            "tradingsymbol": order.symbol,
            "symboltoken": self.session.get_token(order.symbol, order.exchange),
            "transactiontype": order.side.value,
            "exchange": order.exchange,
            "ordertype": order.order_type.value,
            "producttype": "DELIVERY" if order.exchange.upper() in {"NSE", "BSE"} else "CARRYFORWARD",
            "duration": "DAY",
            "price": order.price if order.order_type == OrderType.LIMIT else None,
            "quantity": order.quantity,
        }

    @staticmethod
    def _to_order(item: dict) -> Order:
        status = str(item.get("orderstatus") or item.get("status") or "").lower()
        status_map = {
            "complete": OrderStatus.FILLED,
            "filled": OrderStatus.FILLED,
            "rejected": OrderStatus.REJECTED,
            "cancelled": OrderStatus.CANCELLED,
            "canceled": OrderStatus.CANCELLED,
            "open": OrderStatus.OPEN,
            "partial": OrderStatus.PARTIAL,
        }
        return Order(
            order_id=str(item.get("orderid", "")),
            symbol=str(item.get("tradingsymbol", "")),
            exchange=str(item.get("exchange", "")),
            side=OrderSide(str(item.get("transactiontype", "BUY")).upper()),
            quantity=int(item.get("quantity", 0) or 0),
            order_type=OrderType.LIMIT if str(item.get("ordertype", "")).upper() == "LIMIT" else OrderType.MARKET,
            price=float(item.get("price", 0) or 0) or None,
            status=status_map.get(status, OrderStatus.SUBMITTED),
        )

    @staticmethod
    def _to_position(item: dict) -> Position:
        return Position(
            symbol=str(item.get("tradingsymbol", "")),
            exchange=str(item.get("exchange", "")),
            quantity=int(item.get("netqty", item.get("quantity", 0)) or 0),
            average_price=float(item.get("averageprice", item.get("buyavgprice", 0)) or 0),
            realized_pnl=float(item.get("realised", item.get("realized", 0)) or 0),
            unrealized_pnl=float(item.get("unrealised", item.get("pnl", 0)) or 0),
        )

    @staticmethod
    def _to_trade(item: dict) -> Trade:
        timestamp = str(item.get("filltime") or item.get("updatetime") or "")
        try:
            parsed_time = datetime.fromisoformat(timestamp)
        except ValueError:
            parsed_time = datetime.now()
        return Trade(
            trade_id=str(item.get("tradeid", item.get("orderid", ""))),
            order_id=str(item.get("orderid", "")),
            symbol=str(item.get("tradingsymbol", "")),
            exchange=str(item.get("exchange", "")),
            side=OrderSide(str(item.get("transactiontype", "BUY")).upper()),
            quantity=int(item.get("quantity", 0) or 0),
            price=float(item.get("fillprice", item.get("price", 0)) or 0),
            timestamp=parsed_time,
        )
