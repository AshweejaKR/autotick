"""Common position models for AutoTick."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Position:
    symbol: str
    exchange: str
    quantity: int
    average_price: float
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
