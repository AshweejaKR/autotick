# -*- coding: utf-8 -*-
"""
Created on Sun Aug 30 09:25:06 2026

@author: ashwe
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from autotick.config.secrets import load_secrets
from autotick.models.trade import Trade
from autotick.utils.logger import get_logger

logger = get_logger(__name__)


class ReportManager:
    """Append completed trades and refresh simple performance summaries."""

    _FIELDS = (
        "exit_trade_id",
        "entry_trade_id",
        "strategy",
        "broker",
        "user_id",
        "mode",
        "symbol",
        "exchange",
        "quantity",
        "entry_price",
        "exit_price",
        "pnl",
        "entry_time",
        "exit_time",
    )

    def __init__(self, config: dict[str, Any], execution: Any) -> None:
        reports = config.get("reports", {})
        self.enabled = bool(reports.get("enabled", False))
        self.output_dir = Path(reports.get("output_dir", "reports"))
        self.broker = self._safe(str(config.get("broker", "broker")))
        self.strategy = self._safe(str(config.get("strategy", "strategy")))
        self.mode = self._safe(str(config.get("mode", "mode")))
        configured_user = str(reports.get("user_id", "")).strip()
        broker_user = getattr(getattr(execution, "session", None), "client_id", None)
        if not configured_user and not broker_user and self.broker.lower() == "angelone":
            credentials_file = (
                config.get("broker_config", {}).get("angelone", {}).get("credentials_file")
            )
            if credentials_file:
                try:
                    broker_user = load_secrets(credentials_file)["CLIENT_ID"]
                except ValueError:
                    broker_user = None
        self.user_id = self._safe(configured_user or str(broker_user or "user"))

    def record(self, entry: Trade, exit_trade: Trade, pnl: float) -> None:
        if not self.enabled:
            return
        row = {
            "exit_trade_id": exit_trade.trade_id,
            "entry_trade_id": entry.trade_id,
            "strategy": self.strategy,
            "broker": self.broker,
            "user_id": self.user_id,
            "mode": self.mode,
            "symbol": exit_trade.symbol,
            "exchange": exit_trade.exchange,
            "quantity": exit_trade.quantity,
            "entry_price": round(entry.price, 4),
            "exit_price": round(exit_trade.price, 4),
            "pnl": round(pnl, 4),
            "entry_time": entry.timestamp.isoformat(),
            "exit_time": exit_trade.timestamp.isoformat(),
        }
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            strategy_base = f"{self.broker}_{self.user_id}_{self.strategy}_{self.mode}"
            combined_base = f"{self.broker}_{self.user_id}_{self.mode}"
            for base in (strategy_base, combined_base):
                trades_path = self.output_dir / f"{base}_trades.csv"
                if self._append_new(trades_path, row):
                    self._write_summary(trades_path, self.output_dir / f"{base}_summary.csv")
        except OSError:
            logger.exception("Report write failed")

    def _append_new(self, path: Path, row: dict[str, Any]) -> bool:
        existing = set()
        if path.is_file():
            with path.open("r", encoding="utf-8", newline="") as stream:
                existing = {
                    item.get("exit_trade_id", "")
                    for item in csv.DictReader(stream)
                }
        if row["exit_trade_id"] in existing:
            return False
        write_header = not path.exists() or path.stat().st_size == 0
        with path.open("a", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=self._FIELDS)
            if write_header:
                writer.writeheader()
            writer.writerow(row)
        return True

    @staticmethod
    def _write_summary(trades_path: Path, summary_path: Path) -> None:
        with trades_path.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        pnls = [float(row["pnl"]) for row in rows]
        wins = [value for value in pnls if value > 0]
        losses = [value for value in pnls if value < 0]
        total = len(pnls)
        summary = {
            "completed_trades": total,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate_pct": round((len(wins) / total * 100) if total else 0.0, 2),
            "gross_profit": round(sum(wins), 4),
            "gross_loss": round(sum(losses), 4),
            "net_pnl": round(sum(pnls), 4),
            "average_pnl": round((sum(pnls) / total) if total else 0.0, 4),
            "best_trade": round(max(pnls), 4) if pnls else 0.0,
            "worst_trade": round(min(pnls), 4) if pnls else 0.0,
        }
        with summary_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=summary.keys())
            writer.writeheader()
            writer.writerow(summary)

    @staticmethod
    def _safe(value: str) -> str:
        cleaned = "".join(
            char if char.isalnum() or char in "-_" else "_"
            for char in value.strip()
        )
        return cleaned or "user"
