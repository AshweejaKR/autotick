# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 18:15:19 2026

@author: ashwe
"""

from __future__ import annotations

"""Common order models for AutoTick."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from autotick.models.position import PositionType


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderIntent(str, Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"


class OrderStatus(str, Enum):
    NEW = "NEW"
    VALIDATED = "VALIDATED"
    SUBMITTED = "SUBMITTED"
    OPEN = "OPEN"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


@dataclass(slots=True)
class Order:
    order_id: str
    symbol: str
    exchange: str
    side: OrderSide
    quantity: int
    order_type: OrderType = OrderType.MARKET
    price: float | None = None
    status: OrderStatus = OrderStatus.NEW
    intent: OrderIntent = OrderIntent.ENTRY
    position_type: PositionType = PositionType.POSITIONAL
    status_updated_at: datetime | None = None
