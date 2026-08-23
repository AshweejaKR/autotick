# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 18:15:19 2026

@author: ashwe
"""

from __future__ import annotations

"""Common signal models for AutoTick."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(slots=True)
class Signal:
    symbol: str
    exchange: str
    signal_type: SignalType
    quantity: int | None = None
    price: float | None = None
    timestamp: datetime | None = None
