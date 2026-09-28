from __future__ import annotations

import pytest

from autotick.config.validator import ConfigValidationError
from autotick.config.validator import validate_config


def _goldpetal_config() -> dict:
    return {
        "mode": "backtest",
        "broker": "simulated",
        "strategy": "mcx_goldpetal_orb",
        "market": {
            "symbols": ["GOLDPETAL30SEP26FUT"],
            "exchange": "MCX",
        },
        "capital": 5_000,
        "trade": {"quantity": 1, "position_type": "POSITIONAL"},
        "risk": {
            "max_loss": -2_000,
            "max_trades_per_day": 5,
            "risk_per_trade_pct": 20,
            "stoploss_pct": 2,
            "target_pct": 5,
            "trailing_atr_period": 14,
            "trailing_atr_interval": "1d",
            "trailing_atr_multiplier": 2.5,
        },
        "engine": {"loop_sleep_s": 1},
        "reconnect": {
            "enabled": False,
            "initial_delay_s": 1,
            "max_delay_s": 60,
            "auth_max_attempts": 3,
        },
        "session": {
            "schedule_type": "DAILY",
            "timezone": "Asia/Kolkata",
            "trading_days": ["MON", "TUE", "WED", "THU", "FRI"],
            "closed_dates": [],
            "market_start": "09:15",
            "market_end": "23:30",
            "square_off_time": "23:20",
            "only_market_hours": True,
            "startup_wait_minutes": 30,
            "replay_speed": 1.0,
        },
        "backtest": {"csv": {"enabled": False, "data_file": ""}},
        "persistence": {"enabled": False, "state_path": "state.db"},
        "logging": {
            "enabled": False,
            "level": "DEBUG",
            "log_file": "",
            "timestamp": True,
        },
    }


def test_goldpetal_strategy_accepts_mcx_goldpetal_symbol() -> None:
    validate_config(_goldpetal_config())


def test_goldpetal_strategy_allows_manually_changed_market() -> None:
    config = _goldpetal_config()
    config["market"] = {"symbols": ["SBIN-EQ"], "exchange": "NSE"}

    validate_config(config)


def test_expiry_exit_configuration_is_validated() -> None:
    config = _goldpetal_config()
    config["trade"]["expiry_exit"] = {
        "enabled": True,
        "trading_days_before": -1,
        "time": "23:00",
    }

    with pytest.raises(ConfigValidationError, match="non-negative integer"):
        validate_config(config)


def test_expiry_exit_time_must_be_inside_market_hours() -> None:
    config = _goldpetal_config()
    config["trade"]["expiry_exit"] = {
        "enabled": True,
        "trading_days_before": 1,
        "time": "23:45",
        "contracts": {"GOLDPETAL30SEP26FUT": "2026-09-30"},
    }

    with pytest.raises(ConfigValidationError, match="inside market hours"):
        validate_config(config)


def test_historical_derivative_requires_configured_expiry() -> None:
    config = _goldpetal_config()
    config["trade"]["expiry_exit"] = {"enabled": True, "contracts": {}}

    with pytest.raises(ConfigValidationError, match="requires expiry for GOLDPETAL"):
        validate_config(config)

    config["trade"]["expiry_exit"]["contracts"] = {
        "GOLDPETAL30SEP26FUT": "2026-09-30"
    }
    for mode in ("backtest", "replay"):
        config["mode"] = mode
        validate_config(config)


@pytest.mark.parametrize("expiry", ["2026-02-30", "30SEP2026", 20260930])
def test_configured_expiry_requires_iso_date(expiry) -> None:
    config = _goldpetal_config()
    config["trade"]["expiry_exit"] = {
        "enabled": True,
        "contracts": {"GOLDPETAL30SEP26FUT": expiry},
    }

    with pytest.raises(ConfigValidationError, match="Expiry for GOLDPETAL"):
        validate_config(config)
