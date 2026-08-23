# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 23:02:28 2026

@author: ashwe

Mode-aware market calendar and session timing for AutoTick.
"""

from __future__ import annotations

from datetime import datetime, time
from time import sleep
from zoneinfo import ZoneInfo


class CalendarSessionManager:
    """Provide one session clock for live, paper, backtest, and replay modes."""

    def __init__(self, session_config: dict | None = None) -> None:
        config = session_config or {}
        self._timezone = ZoneInfo(config.get("timezone", "Asia/Kolkata"))
        self._market_start = self._parse_time(config.get("market_start", "09:15"))
        self._market_end = self._parse_time(config.get("market_end", "15:30"))
        self._square_off = self._parse_time(config.get("square_off_time", "15:15"))
        self._replay_speed = float(config.get("replay_speed", 1.0))
        self._mode = "paper"
        self._current_time: datetime | None = None

    def configure_mode(self, mode: str) -> None:
        """Configure clock behaviour for one trading mode."""
        mode = mode.strip().lower()
        if mode not in {"live", "paper", "backtest", "replay"}:
            raise ValueError(f"Unsupported trading mode: {mode}")
        self._mode = mode

    def now(self) -> datetime:
        """Return wall-clock or simulated time for the active mode."""
        if self._mode in {"live", "paper"}:
            return datetime.now(self._timezone)
        if self._current_time is None:
            raise RuntimeError("Simulated session time is not initialized")
        return self._current_time

    def update_time(self, value: datetime) -> None:
        """Update simulated time for backtest or replay modes."""
        if self._mode in {"live", "paper"}:
            return
        self._current_time = value

    def wait_until(self, value: datetime) -> None:
        """Wait in replay mode; backtest advances immediately."""
        if self._mode != "replay" or self._current_time is None:
            return
        delay = (value - self._current_time).total_seconds() / self._replay_speed
        if delay > 0:
            sleep(delay)
        self._current_time = value

    def reset(self) -> None:
        """Clear simulated session time."""
        self._current_time = None

    def is_trading_day(self, value: datetime | None = None) -> bool:
        """Return True for Monday through Friday."""
        return (value or self.now()).weekday() < 5

    def is_market_open(self, value: datetime | None = None) -> bool:
        """Return True when current time is inside configured market hours."""
        current = value or self.now()
        return self.is_trading_day(current) and self._market_start <= current.time() <= self._market_end

    def current_session(self, value: datetime | None = None) -> str:
        """Return pre_market, open, or closed."""
        current = value or self.now()
        if not self.is_trading_day(current):
            return "closed"
        if current.time() < self._market_start:
            return "pre_market"
        if current.time() <= self._market_end:
            return "open"
        return "closed"

    def should_square_off(self, value: datetime | None = None) -> bool:
        """Return True at or after configured square-off time while market is open."""
        current = value or self.now()
        return self.is_market_open(current) and current.time() >= self._square_off

    def detect_session_boundary(self, previous: datetime, current: datetime) -> bool:
        """Return True when session state changes between two timestamps."""
        return self.current_session(previous) != self.current_session(current)

    @staticmethod
    def _parse_time(value: str) -> time:
        return datetime.strptime(value, "%H:%M").time()
