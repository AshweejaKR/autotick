# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 00:19:15 2026

@author: ashwe

Mode-neutral runtime context exposed to strategies.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from autotick.models.market import MarketBar, MarketTick


@dataclass(slots=True)
class StrategyContext:
    """Hold the latest market inputs and calculated indicator values."""

    tick: MarketTick | None = None
    bar: MarketBar | None = None
    indicators: dict[str, float | None] = field(default_factory=dict)
