# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 19:56:33 2026

@author: ashwe
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from autotick.interfaces.execution import ExecutionProvider
from autotick.models.order import Order, OrderIntent, OrderSide, OrderStatus, OrderType
from autotick.models.position import Position, PositionType
from autotick.models.trade import Trade
from autotick.providers.brokers.angelone.session import AngelOneSession
from autotick.providers.session_pool import BrokerConnectionError
from autotick.utils.logger import get_logger

logger = get_logger(__name__)


class AngelOneExecutionProvider(ExecutionProvider):
    """AngelOne SmartAPI execution adapter."""

    uses_broker_margin = True

    def __init__(self, session: AngelOneSession) -> None:
        self.session = session

    def place_order(self, order: Order) -> Order:
        if order.intent == OrderIntent.ENTRY:
            order = self._fit_to_available_margin(order)
            if order.quantity <= 0:
                return replace(order, status=OrderStatus.REJECTED)
        logger.warning(
            "AngelOne PLACE ORDER side=%s symbol=%s exchange=%s qty=%s type=%s product=%s price=%s",
            order.side.value,
            order.symbol,
            order.exchange,
            order.quantity,
            order.order_type.value,
            order.position_type.value,
            order.price,
        )
        response = self.session.call_once(
            self.session.client.placeOrderFullResponse,
            self._order_params(order),
        )
        order_id = (
            (response.get("data") or {}).get("orderid")
            if isinstance(response, dict) and response.get("status")
            else None
        )
        if not order_id:
            order.status = OrderStatus.REJECTED
            logger.error(
                "AngelOne order rejected side=%s symbol=%s qty=%s",
                order.side.value,
                order.symbol,
                order.quantity,
            )
            return order
        order.order_id = str(order_id)
        order.status = OrderStatus.SUBMITTED
        logger.done(
            "AngelOne order accepted broker_order_id=%s side=%s symbol=%s qty=%s",
            order.order_id,
            order.side.value,
            order.symbol,
            order.quantity,
        )
        return order

    def modify_order(self, order: Order) -> Order:
        params = self._order_params(order)
        params["orderid"] = order.order_id
        response = self.session.call_once(self.session.client.modifyOrder, params)
        if response and response.get("status"):
            order.status = OrderStatus.SUBMITTED
        return order

    def cancel_order(self, order_id: str) -> bool:
        response = self.session.call_once(
            self.session.client.cancelOrder,
            order_id,
            "NORMAL",
        )
        return bool(response and response.get("status"))

    def cancel_all(self) -> None:
        for order in self.get_orders():
            if order.status in {OrderStatus.SUBMITTED, OrderStatus.OPEN, OrderStatus.PARTIAL}:
                self.cancel_order(order.order_id)

    def get_order(self, order_id: str) -> Order | None:
        if not order_id:
            return None
        return next((order for order in self.get_orders() if order.order_id == order_id), None)

    def get_order_status(self, order_id: str) -> OrderStatus | None:
        order = self.get_order(order_id)
        return order.status if order else None

    def get_orders(self) -> list[Order]:
        return [
            self._to_order(item)
            for item in self._read_data(self.session.client.orderBook, "order book")
        ]

    def get_positions(self) -> list[Position]:
        return [
            self._to_position(item)
            for item in self._read_data(self.session.client.position, "positions")
        ]

    def get_holdings(self) -> list[Position]:
        return [
            self._to_position(item)
            for item in self._read_data(self.session.client.holding, "holdings")
        ]

    def get_trades(self) -> list[Trade]:
        return [
            self._to_trade(item)
            for item in self._read_data(self.session.client.tradeBook, "trade book")
        ]

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
                    intent=OrderIntent.EXIT,
                    position_type=position.position_type,
                )
            )

    def _order_params(self, order: Order) -> dict[str, object]:
        trading_symbol, token = self.session.get_instrument(order.symbol, order.exchange)
        product = self._product_type(order)
        return {
            "variety": "NORMAL",
            "tradingsymbol": trading_symbol,
            "symboltoken": token,
            "transactiontype": order.side.value,
            "exchange": order.exchange,
            "ordertype": order.order_type.value,
            "producttype": product,
            "duration": "DAY",
            "price": order.price if order.order_type == OrderType.LIMIT else None,
            "quantity": order.quantity,
        }

    def _fit_to_available_margin(self, order: Order) -> Order:
        """Reduce a new entry to the quantity affordable at broker-calculated cost."""
        available = self._available_margin()
        required = self._entry_requirement(order, order.quantity)
        if required <= available:
            return order

        quantity = min(order.quantity, int(order.quantity * available / required))
        while quantity > 0:
            required = self._entry_requirement(order, quantity)
            if required <= available:
                logger.info(
                    "AngelOne entry quantity reduced symbol=%s requested=%s approved=%s "
                    "required=%.2f available=%.2f",
                    order.symbol,
                    order.quantity,
                    quantity,
                    required,
                    available,
                )
                return replace(order, quantity=quantity)
            quantity -= 1
        logger.warning(
            "AngelOne entry blocked by margin symbol=%s required=%.2f available=%.2f",
            order.symbol,
            required,
            available,
        )
        return replace(order, quantity=0)

    def _entry_requirement(self, order: Order, quantity: int) -> float:
        trading_symbol, token = self.session.get_instrument(order.symbol, order.exchange)
        product = self._product_type(order)
        margin = self.session.call(
            self.session.client.getMarginApi,
            {
                "positions": [{
                    "exchange": order.exchange,
                    "qty": quantity,
                    "price": 0,
                    "productType": product,
                    "token": token,
                    "tradeType": order.side.value,
                }],
            },
        )
        charges = self.session.call(
            self.session.client.estimateCharges,
            {
                "orders": [{
                    "product_type": product,
                    "transaction_type": order.side.value,
                    "quantity": str(quantity),
                    "price": str(int(round(float(order.price or 0)))),
                    "exchange": order.exchange,
                    "symbol_name": trading_symbol,
                    "token": token,
                }],
            },
        )
        return self._response_amount(margin, "totalMarginRequired") + self._charge_amount(charges)

    def _available_margin(self) -> float:
        response = self.session.call(self.session.client.rmsLimit)
        if not isinstance(response, dict) or response.get("status") is not True:
            raise BrokerConnectionError("AngelOne RMS margin read failed")
        data = response.get("data") or {}
        return float(data.get("availablelimitmargin", data.get("availablecash", 0)) or 0)

    @staticmethod
    def _response_amount(response: object, key: str) -> float:
        if not isinstance(response, dict) or response.get("status") is not True:
            raise BrokerConnectionError(f"AngelOne margin estimate failed: {response}")
        data = response.get("data") or {}
        try:
            return float(data[key])
        except (KeyError, TypeError, ValueError) as exc:
            raise BrokerConnectionError("AngelOne margin estimate was invalid") from exc

    @staticmethod
    def _charge_amount(response: object) -> float:
        if not isinstance(response, dict) or response.get("status") is not True:
            raise BrokerConnectionError(f"AngelOne charge estimate failed: {response}")
        data = response.get("data") or {}
        try:
            return float(data["summary"]["total_charges"])
        except (KeyError, TypeError, ValueError) as exc:
            raise BrokerConnectionError("AngelOne charge estimate was invalid") from exc

    @staticmethod
    def _product_type(order: Order) -> str:
        if order.position_type == PositionType.INTRADAY:
            return "INTRADAY"
        return "DELIVERY" if order.exchange.upper() in {"NSE", "BSE"} else "CARRYFORWARD"

    @classmethod
    def _to_order(cls, item: dict) -> Order:
        status = str(item.get("orderstatus") or item.get("status") or "").lower()
        product = str(item.get("producttype", "")).upper()
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
            price=float(item.get("averageprice", item.get("price", 0)) or 0) or None,
            status=status_map.get(status, OrderStatus.SUBMITTED),
            position_type=PositionType.INTRADAY if product == "INTRADAY" else PositionType.POSITIONAL,
            filled_quantity=cls._filled_quantity(item, status),
        )

    def _read_data(self, operation, name: str) -> list[dict]:
        response = self.session.call(operation)
        if not isinstance(response, dict) or response.get("status") is not True:
            message = response.get("message", "unknown error") if isinstance(response, dict) else "invalid response"
            raise BrokerConnectionError(f"AngelOne {name} read failed: {message}")
        data = response.get("data")
        if not isinstance(data, list):
            raise BrokerConnectionError(f"AngelOne {name} read returned invalid data")
        return data

    @staticmethod
    def _filled_quantity(item: dict, status: str) -> int | None:
        value = item.get("filledshares", item.get("filledquantity"))
        if value is None:
            return int(item.get("quantity", 0) or 0) if status in {"complete", "filled"} else None
        return int(value or 0)

    @staticmethod
    def _to_position(item: dict) -> Position:
        product = str(item.get("producttype", "")).upper()
        return Position(
            symbol=str(item.get("tradingsymbol", "")),
            exchange=str(item.get("exchange", "")),
            quantity=int(item.get("netqty", item.get("quantity", 0)) or 0),
            average_price=float(item.get("averageprice", item.get("buyavgprice", 0)) or 0),
            realized_pnl=float(item.get("realised", item.get("realized", 0)) or 0),
            unrealized_pnl=float(item.get("unrealised", item.get("pnl", 0)) or 0),
            position_type=PositionType.INTRADAY if product == "INTRADAY" else PositionType.POSITIONAL,
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
