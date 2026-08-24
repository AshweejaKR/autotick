# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 18:15:19 2026

@author: ashwe

Configuration validation for AutoTick.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


class ConfigValidationError(ValueError):
    """Raised when configuration values are invalid."""


_VALID_MODES = {"live", "paper", "backtest", "replay"}
_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def _require(config: dict[str, Any], key: str, path: str = "") -> Any:
    if key not in config:
        name = f"{path}.{key}" if path else key
        raise ConfigValidationError(f"Missing required configuration: {name}")
    return config[key]


def _mapping(config: dict[str, Any], key: str, path: str = "") -> dict[str, Any]:
    value = _require(config, key, path)
    if not isinstance(value, dict):
        name = f"{path}.{key}" if path else key
        raise ConfigValidationError(f"{name} must be a mapping")
    return value


def _number(value: Any, name: str, *, positive: bool = False) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigValidationError(f"{name} must be a number")
    if positive and value <= 0:
        raise ConfigValidationError(f"{name} must be greater than 0")


def _hhmm(value: Any, name: str) -> None:
    if not isinstance(value, str):
        raise ConfigValidationError(f"{name} must be a HH:MM string")
    try:
        datetime.strptime(value, "%H:%M")
    except ValueError as exc:
        raise ConfigValidationError(f"{name} must use HH:MM format") from exc


def validate_config(config: dict[str, Any]) -> None:
    """Validate the AutoTick YAML configuration."""
    mode = _require(config, "mode")
    if mode not in _VALID_MODES:
        raise ConfigValidationError(
            f"mode must be one of: {', '.join(sorted(_VALID_MODES))}"
        )

    broker = _require(config, "broker")
    if not isinstance(broker, str) or not broker.strip():
        raise ConfigValidationError("broker must be a non-empty string")

    strategy = _require(config, "strategy")
    if not isinstance(strategy, str) or not strategy.strip():
        raise ConfigValidationError("strategy must be a non-empty string")

    market = _mapping(config, "market")
    symbols = _require(market, "symbols", "market")
    if isinstance(symbols, str):
        if not symbols.strip():
            raise ConfigValidationError("market.symbols must not be empty")
    elif isinstance(symbols, list):
        if not symbols or not all(isinstance(item, str) and item.strip() for item in symbols):
            raise ConfigValidationError("market.symbols must contain non-empty strings")
    else:
        raise ConfigValidationError("market.symbols must be a string or list of strings")

    exchange = _require(market, "exchange", "market")
    if not isinstance(exchange, str) or not exchange.strip():
        raise ConfigValidationError("market.exchange must be a non-empty string")

    _number(_require(config, "capital"), "capital", positive=True)

    trade = _mapping(config, "trade")
    quantity = _require(trade, "quantity", "trade")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise ConfigValidationError("trade.quantity must be a positive integer")

    risk = _mapping(config, "risk")
    _number(_require(risk, "max_loss", "risk"), "risk.max_loss")
    max_trades = _require(risk, "max_trades_per_day", "risk")
    if isinstance(max_trades, bool) or not isinstance(max_trades, int) or max_trades <= 0:
        raise ConfigValidationError("risk.max_trades_per_day must be a positive integer")
    for key in ("risk_per_trade_pct", "stoploss_pct", "target_pct", "trailing_sl_pct"):
        value = _require(risk, key, "risk")
        _number(value, f"risk.{key}")
        if value < 0 or value > 100:
            raise ConfigValidationError(f"risk.{key} must be between 0 and 100")

    engine = _mapping(config, "engine")
    loop_sleep = _require(engine, "loop_sleep_s", "engine")
    _number(loop_sleep, "engine.loop_sleep_s", positive=True)

    session = _mapping(config, "session")
    for key in ("market_start", "market_end", "square_off_time"):
        _hhmm(_require(session, key, "session"), f"session.{key}")
    only_market_hours = _require(session, "only_market_hours", "session")
    if not isinstance(only_market_hours, bool):
        raise ConfigValidationError("session.only_market_hours must be boolean")
    _number(_require(session, "replay_speed", "session"), "session.replay_speed", positive=True)

    if mode in {"live", "paper"}:
        broker_config = _mapping(config, "broker_config")
        if broker not in broker_config or not isinstance(broker_config[broker], dict):
            raise ConfigValidationError(f"broker_config.{broker} must be configured")

    if mode in {"backtest", "replay"}:
        backtest = config.get("backtest", {})
        csv_config = backtest.get("csv", {})
        if csv_config and not isinstance(csv_config.get("enabled", False), bool):
            raise ConfigValidationError("backtest.csv.enabled must be boolean")
        if csv_config.get("enabled"):
            data_file = csv_config.get("data_file")
            if not isinstance(data_file, str) or not data_file.strip():
                raise ConfigValidationError("backtest.csv.data_file is required when enabled")

    persistence = _mapping(config, "persistence")
    if not isinstance(_require(persistence, "enabled", "persistence"), bool):
        raise ConfigValidationError("persistence.enabled must be boolean")
    state_path = _require(persistence, "state_path", "persistence")
    if not isinstance(state_path, str) or not state_path.strip():
        raise ConfigValidationError("persistence.state_path must be a non-empty string")

    logging_config = _mapping(config, "logging")
    enabled = _require(logging_config, "enabled", "logging")
    if not isinstance(enabled, bool):
        raise ConfigValidationError("logging.enabled must be boolean")

    timestamp = _require(logging_config, "timestamp", "logging")
    if not isinstance(timestamp, bool):
        raise ConfigValidationError("logging.timestamp must be boolean")

    level = _require(logging_config, "level", "logging")
    if not isinstance(level, str) or level.upper() not in _VALID_LOG_LEVELS:
        raise ConfigValidationError(
            f"logging.level must be one of: {', '.join(sorted(_VALID_LOG_LEVELS))}"
        )

    log_file = _require(logging_config, "log_file", "logging")
    if enabled and (not isinstance(log_file, str) or not log_file.strip()):
        raise ConfigValidationError("logging.log_file must be a non-empty string when enabled")
