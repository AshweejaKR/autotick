# -*- coding: utf-8 -*-
"""
Created on Sat Sep 12 19:28:09 2026

@author: ashwe
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from autotick.models.order import Order
from autotick.reports.report import ReportManager
from autotick.utils.logger import get_logger

logger = get_logger(__name__)


class AuditTrail:
    """Append normalized order and recovery events beside report files."""

    _FIELDS = (
        "timestamp",
        "event",
        "order_id",
        "symbol",
        "exchange",
        "side",
        "quantity",
        "status",
        "price",
        "intent",
        "details",
    )

    def __init__(self, config: dict[str, Any], execution: Any) -> None:
        reports = config.get("reports", {})
        self.enabled = bool(reports.get("enabled", False))
        self.output_dir = Path(reports.get("output_dir", "reports"))
        broker = ReportManager._safe(str(config.get("broker", "broker")))
        strategy = ReportManager._safe(str(config.get("strategy", "strategy")))
        mode = ReportManager._safe(str(config.get("mode", "mode")))
        user_id = ReportManager._safe(
            str(reports.get("user_id") or getattr(getattr(execution, "session", None), "client_id", None) or "user")
        )
        self.path = self.output_dir / f"{broker}_{user_id}_{strategy}_{mode}_audit.csv"

    def record_order(self, order: Order) -> None:
        self._append({
            "event": "ORDER_STATE",
            "order_id": order.order_id,
            "symbol": order.symbol,
            "exchange": order.exchange,
            "side": order.side.value,
            "quantity": order.quantity,
            "status": order.status.value,
            "price": order.price,
            "intent": order.intent.value,
            "details": "",
        })

    def record_recovery(
        self,
        recovered: bool,
        changed_orders: int,
        unresolved_orders: int,
    ) -> None:
        self._append({
            "event": "RECOVERY",
            "order_id": "",
            "symbol": "",
            "exchange": "",
            "side": "",
            "quantity": "",
            "status": "",
            "price": "",
            "intent": "",
            "details": (
                f"recovered={recovered};changed_orders={changed_orders};"
                f"unresolved_orders={unresolved_orders}"
            ),
        })

    def _append(self, row: dict[str, Any]) -> None:
        if not self.enabled:
            return
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            row = {"timestamp": datetime.now(timezone.utc).isoformat(), **row}
            lock_path = self.path.with_name(f".{self.path.stem}.lock")
            with ReportManager._file_lock(lock_path):
                write_header = not self.path.exists() or self.path.stat().st_size == 0
                with self.path.open("a", encoding="utf-8", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=self._FIELDS)
                    if write_header:
                        writer.writeheader()
                    writer.writerow(row)
        except Exception:
            logger.exception("Audit update failed: %s", self.path)
