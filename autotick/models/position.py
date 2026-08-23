# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 18:15:19 2026

@author: ashwe
"""

from __future__ import annotations

"""Common position models for AutoTick."""

from dataclasses import dataclass


@dataclass(slots=True)
class Position:
    symbol: str
    exchange: str
    quantity: int
    average_price: float
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
