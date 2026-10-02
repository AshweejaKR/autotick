# -*- coding: utf-8 -*-
"""
Created on Sat Sep 12 19:28:09 2026

@author: ashwe
"""

from __future__ import annotations

import pytest


@pytest.fixture
def make_config(tmp_path):
    """Build the minimal deterministic configuration used by offline tests."""
    def build(
        mode: str = "paper",
        capital: int = 1_000,
        quantity: int = 5,
        reports: bool = False,
        max_position_value: int | None = None,
        max_trades: int = 2,
    ) -> dict:
        trade = {"quantity": quantity, "position_type": "POSITIONAL"}
        if max_position_value is not None:
            trade["max_position_value"] = max_position_value
        return {
            "mode": mode,
            "broker": "simulated",
            "strategy": "test",
            "capital": capital,
            "market": {"exchange": "NSE", "symbols": ["INFY-EQ"]},
            "trade": trade,
            "risk": {
                "max_loss": -100 if capital == 1_000 else -2_000,
                "max_trades_per_day": max_trades,
                "risk_per_trade_pct": 10 if capital == 1_000 else 1,
                "stoploss_pct": 2,
                "target_pct": 5,
                "trailing_atr_period": 14,
                "trailing_atr_interval": "1d",
                "trailing_atr_multiplier": 0,
            },
            "persistence": {"state_path": str(tmp_path / "state.db")},
            "reports": {
                "enabled": reports,
                "output_dir": str(tmp_path / "reports"),
                "user_id": "tester",
            },
        }

    return build
