"""Common account models for AutoTick."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Account:
    configured_capital: float
    balance: float | None = None
    available_margin: float | None = None
    buying_power: float | None = None
