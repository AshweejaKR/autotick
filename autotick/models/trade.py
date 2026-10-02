# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 18:15:19 2026

@author: ashwe
"""

from __future__ import annotations

"""Common trade models for AutoTick."""

from dataclasses import dataclass
from datetime import datetime

from autotick.models.order import OrderSide


@dataclass(slots=True)
class Trade:
    trade_id: str
    order_id: str
    symbol: str
    exchange: str
    side: OrderSide
    quantity: int
    price: float
    timestamp: datetime
