# -*- coding: utf-8 -*-
"""
Created on Sun Sep 06 2026

@author: ashwe

CSV trigger-price swing strategy for AutoTick.
"""

from __future__ import annotations

import csv
from pathlib import Path

from autotick.models.market import MarketTick
from autotick.models.signal import Signal, SignalType
from autotick.strategy.base import Strategy
from autotick.utils.logger import get_logger

logger = get_logger(__name__)


def load_swing_watchlist(csv_file: str | Path) -> dict[str, float]:
    """Load unique positive trigger prices keyed by normalized symbol."""
    path = Path(csv_file)
    if not path.is_file():
        raise ValueError(f"Swing watchlist not found: {path}")

    watchlist: dict[str, float] = {}
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not {"symbol", "trigger_price"}.issubset(
            name.strip() for name in reader.fieldnames
        ):
            raise ValueError("Swing watchlist requires symbol,trigger_price columns")
        for line, row in enumerate(reader, start=2):
            symbol = str(row.get("symbol") or "").strip().upper()
            trigger = str(row.get("trigger_price") or "").strip()
            if not symbol and not trigger:
                continue
            try:
                trigger_price = float(trigger)
            except ValueError as exc:
                raise ValueError(f"Invalid trigger_price at CSV line {line}") from exc
            if not symbol or trigger_price <= 0:
                raise ValueError(f"Invalid swing watchlist row at CSV line {line}")
            if symbol in watchlist:
                raise ValueError(f"Duplicate swing symbol at CSV line {line}: {symbol}")
            watchlist[symbol] = trigger_price
    return watchlist


class SwingStrategy(Strategy):
    """Buy once LTP moves above the CSV trigger price."""

    def __init__(self, csv_file: str | Path) -> None:
        super().__init__()
        self.csv_file = Path(csv_file)
        self.trigger_price: float | None = None

    def on_initial_setup(self) -> None:
        if self.context is None:
            raise RuntimeError("Strategy is not initialized")
        self.trigger_price = load_swing_watchlist(self.csv_file).get(
            self.context.symbol.upper()
        )
        if self.trigger_price is not None:
            logger.info(
                "SWING ready symbol=%s trigger_price=%.2f",
                self.context.symbol,
                self.trigger_price,
            )

    def on_tick(self, tick: MarketTick) -> Signal | None:
        if self.trigger_price is None or tick.ltp is None:
            return None
        if tick.ltp <= self.trigger_price:
            return None
        logger.warning(
            "SWING ENTRY TRIGGER symbol=%s ltp=%.2f trigger_price=%.2f",
            tick.symbol,
            tick.ltp,
            self.trigger_price,
        )
        return Signal(
            symbol=tick.symbol,
            exchange=tick.exchange,
            signal_type=SignalType.BUY,
            price=tick.ltp,
            timestamp=tick.timestamp,
        )
