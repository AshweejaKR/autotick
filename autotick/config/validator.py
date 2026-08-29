# -*- coding: utf-8 -*-
"""Configuration validation for AutoTick."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ConfigValidationError(ValueError):
    """Raised when configuration values are invalid."""


_VALID_MODES = {"live", "paper", "backtest", "replay"}
_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_VALID_POSITION_TYPES = {"INTRADAY", "POSITIONAL"}
_VALID_SCHEDULE_TYPES = {"DAILY", "WEEKLY", "ALWAYS_OPEN"}
_VALID_DAYS = {"MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"}


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


def _hhmm(value: Any, name: str) -> time:
    if not isinstance(value, str):
        raise ConfigValidationError(f"{name} must be a HH:MM string")
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError as exc:
        raise ConfigValidationError(f"{name} must use HH:MM format") from exc


def _day(value: Any, name: str) -> str:
    if not isinstance(value, str) or value.upper() not in _VALID_DAYS:
        raise ConfigValidationError(f"{name} must be one of: {', '.join(sorted(_VALID_DAYS))}")
    return value.upper()


def _validate_session(session: dict[str, Any]) -> None:
    schedule_type = _require(session, "schedule_type", "session")
    if not isinstance(schedule_type, str) or schedule_type.upper() not in _VALID_SCHEDULE_TYPES:
        raise ConfigValidationError(
            f"session.schedule_type must be one of: {', '.join(sorted(_VALID_SCHEDULE_TYPES))}"
        )
    schedule_type = schedule_type.upper()

    timezone = _require(session, "timezone", "session")
    if not isinstance(timezone, str) or not timezone.strip():
        raise ConfigValidationError("session.timezone must be a non-empty IANA timezone")
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise ConfigValidationError(f"Unknown session.timezone: {timezone}") from exc

    closed_dates = session.get("closed_dates", [])
    if not isinstance(closed_dates, list):
        raise ConfigValidationError("session.closed_dates must be a list")
    for value in closed_dates:
        if not isinstance(value, str):
            raise ConfigValidationError("session.closed_dates must contain YYYY-MM-DD strings")
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ConfigValidationError(
                "session.closed_dates must contain valid YYYY-MM-DD dates"
            ) from exc

    if schedule_type == "DAILY":
        trading_days = _require(session, "trading_days", "session")
        if not isinstance(trading_days, list) or not trading_days:
            raise ConfigValidationError("session.trading_days must be a non-empty list")
        normalized_days = [_day(value, "session.trading_days") for value in trading_days]
        if len(set(normalized_days)) != len(normalized_days):
            raise ConfigValidationError("session.trading_days must not contain duplicates")
        market_start = _hhmm(_require(session, "market_start", "session"), "session.market_start")
        market_end = _hhmm(_require(session, "market_end", "session"), "session.market_end")
        square_off = _hhmm(
            _require(session, "square_off_time", "session"), "session.square_off_time"
        )
        if market_start >= market_end:
            raise ConfigValidationError("session.market_start must be before session.market_end")
        if not market_start <= square_off <= market_end:
            raise ConfigValidationError(
                "session.square_off_time must be inside market hours"
            )

    if schedule_type == "WEEKLY":
        start_day = _day(_require(session, "week_start_day", "session"), "session.week_start_day")
        end_day = _day(_require(session, "week_end_day", "session"), "session.week_end_day")
        start_time = _hhmm(
            _require(session, "week_start_time", "session"), "session.week_start_time"
        )
        end_time = _hhmm(
            _require(session, "week_end_time", "session"), "session.week_end_time"
        )
        if start_day == end_day and start_time == end_time:
            raise ConfigValidationError("weekly session start and end must differ")

        break_start = session.get("daily_break_start")
        break_end = session.get("daily_break_end")
        if (break_start is None) != (break_end is None):
            raise ConfigValidationError(
                "session.daily_break_start and session.daily_break_end must be set together"
            )
        if break_start is not None:
            parsed_start = _hhmm(break_start, "session.daily_break_start")
            parsed_end = _hhmm(break_end, "session.daily_break_end")
            if parsed_start == parsed_end:
                raise ConfigValidationError("daily break start and end must differ")

    only_market_hours = _require(session, "only_market_hours", "session")
    if not isinstance(only_market_hours, bool):
        raise ConfigValidationError("session.only_market_hours must be boolean")
    _number(_require(session, "replay_speed", "session"), "session.replay_speed", positive=True)


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
    position_type = trade.get("position_type", "POSITIONAL")
    if not isinstance(position_type, str) or position_type.upper() not in _VALID_POSITION_TYPES:
        raise ConfigValidationError("trade.position_type must be INTRADAY or POSITIONAL")

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

    simulated = config.get("simulated", {})
    if not isinstance(simulated, dict):
        raise ConfigValidationError("simulated must be a mapping")
    ui_data_enabled = simulated.get("ui_data_enabled", False)
    if not isinstance(ui_data_enabled, bool):
        raise ConfigValidationError("simulated.ui_data_enabled must be boolean")
    broker_auto_fetch = simulated.get("broker_auto_fetch", False)
    if not isinstance(broker_auto_fetch, bool):
        raise ConfigValidationError("simulated.broker_auto_fetch must be boolean")
    if ui_data_enabled and mode != "paper":
        raise ConfigValidationError(
            "simulated.ui_data_enabled is supported only in paper mode"
        )
    if broker_auto_fetch and not ui_data_enabled:
        raise ConfigValidationError(
            "simulated.broker_auto_fetch requires simulated.ui_data_enabled"
        )
    if broker_auto_fetch and broker.strip().lower() == "simulated":
        raise ConfigValidationError(
            "broker must select a real broker when simulated.broker_auto_fetch is enabled"
        )

    _validate_session(_mapping(config, "session"))

    if mode == "live" or (
        mode == "paper" and (not ui_data_enabled or broker_auto_fetch)
    ):
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
