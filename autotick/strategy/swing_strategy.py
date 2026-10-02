# -*- coding: utf-8 -*-
"""
Created on Sun Sep 06 2026

@author: ashwe

CSV trigger-price swing strategy for AutoTick.
"""

from __future__ import annotations

import csv
import math
import os
import re
from pathlib import Path
from tempfile import NamedTemporaryFile

from autotick.models.market import MarketTick
from autotick.models.signal import Signal, SignalType
from autotick.strategy.base import Strategy
from autotick.utils.logger import get_logger

logger = get_logger(__name__)


def _read_swing_watchlist(
    path: Path, *, ignore_duplicates: bool = False,
) -> dict[str, float]:
    """Load unique positive trigger prices keyed by normalized symbol."""
    if not path.is_file():
        raise ValueError(f"Swing watchlist not found: {path}")

    watchlist: dict[str, float] = {}
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not {"symbol", "trigger_price"}.issubset(
            name.strip() for name in reader.fieldnames
        ):
            raise ValueError("Swing watchlist requires symbol,trigger_price columns")
        reader.fieldnames = [name.strip() for name in reader.fieldnames]
        for line, row in enumerate(reader, start=2):
            symbol = str(row.get("symbol") or "").strip().upper()
            trigger = str(row.get("trigger_price") or "").strip()
            if not symbol and not trigger:
                continue
            try:
                trigger_price = float(trigger)
            except ValueError as exc:
                raise ValueError(f"Invalid trigger_price at CSV line {line}") from exc
            if not symbol or not math.isfinite(trigger_price) or trigger_price <= 0:
                raise ValueError(f"Invalid swing watchlist row at CSV line {line}")
            if symbol in watchlist:
                if ignore_duplicates:
                    continue
                raise ValueError(f"Duplicate swing symbol at CSV line {line}: {symbol}")
            watchlist[symbol] = trigger_price
    return watchlist


def _append_swing_symbols(path: Path, additions: dict[str, float]) -> None:
    """Atomically append rows while preserving existing CSV contents and columns."""
    with path.open(newline="", encoding="utf-8-sig") as stream:
        existing = stream.read()
        stream.seek(0)
        fieldnames = [name.strip() for name in csv.DictReader(stream).fieldnames]
    stream = NamedTemporaryFile(
        mode="w", newline="", encoding="utf-8", dir=path.parent,
        prefix=f".{path.name}.", suffix=".tmp", delete=False,
    )
    temporary = Path(stream.name)
    try:
        with stream:
            stream.write(existing)
            if not existing.endswith("\n"):
                stream.write("\n")
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writerows(
                {"symbol": symbol, "trigger_price": price}
                for symbol, price in additions.items()
            )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_swing_watchlist(
    csv_file: str | Path, *, import_pending: bool = False,
) -> dict[str, float]:
    """Load the watchlist; optionally consume timestamped imports at startup."""
    path = Path(csv_file)
    watchlist = _read_swing_watchlist(path)
    if import_pending:
        for source in sorted(path.parent.glob("swing_watchlist_import_*.csv")):
            if (
                source == path or not source.is_file() or source.is_symlink()
                or re.fullmatch(r"swing_watchlist_import_\d{8}_\d{6}\.csv", source.name) is None
            ):
                continue
            try:
                imported = _read_swing_watchlist(source, ignore_duplicates=True)
            except ValueError as exc:
                raise ValueError(f"Invalid swing import {source.name}: {exc}") from exc
            additions = {
                symbol: price for symbol, price in imported.items()
                if symbol not in watchlist
            }
            if additions:
                _append_swing_symbols(path, additions)
                watchlist.update(additions)
            source.unlink()
            logger.info(
                "Swing watchlist import processed file=%s added=%s ignored=%s",
                source.name, len(additions), len(imported) - len(additions),
            )
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
