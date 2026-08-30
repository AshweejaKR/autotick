# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 23:02:28 2026

@author: ashwe

Mode-aware market calendar and session timing for AutoTick.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from time import sleep
from zoneinfo import ZoneInfo


class CalendarSessionManager:
    """Provide one configured market clock for one exchange per run."""

    _DAYS = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6}
    _WEEK_SECONDS = 7 * 24 * 60 * 60

    def __init__(self, session_config: dict | None = None) -> None:
        config = session_config or {}
        self._timezone = ZoneInfo(config.get("timezone", "Asia/Kolkata"))
        self._schedule_type = str(config.get("schedule_type", "DAILY")).upper()
        if self._schedule_type not in {"DAILY", "WEEKLY", "ALWAYS_OPEN"}:
            raise ValueError(f"Unsupported schedule type: {self._schedule_type}")

        self._closed_dates = {
            date.fromisoformat(value) for value in config.get("closed_dates", [])
        }
        self._market_start = self._market_end = self._square_off = None
        self._week_start = self._week_end = None
        self._break_start = self._break_end = None

        if self._schedule_type == "DAILY":
            self._trading_days = {
                self._DAYS[value.upper()]
                for value in config.get("trading_days", ["MON", "TUE", "WED", "THU", "FRI"])
            }
            self._market_start = self._parse_time(config.get("market_start", "09:15"))
            self._market_end = self._parse_time(config.get("market_end", "15:30"))
            self._square_off = self._parse_time(config.get("square_off_time", "15:15"))
        elif self._schedule_type == "WEEKLY":
            self._week_start = self._week_position(
                config["week_start_day"], self._parse_time(config["week_start_time"])
            )
            self._week_end = self._week_position(
                config["week_end_day"], self._parse_time(config["week_end_time"])
            )
            if config.get("daily_break_start") is not None:
                self._break_start = self._parse_time(config["daily_break_start"])
                self._break_end = self._parse_time(config["daily_break_end"])

        self._replay_speed = float(config.get("replay_speed", 1.0))
        if self._replay_speed <= 0:
            raise ValueError("replay_speed must be greater than zero")
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
        if self._mode not in {"live", "paper"}:
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
        """Return True when the date overlaps the configured market schedule."""
        current = value or self.now()
        if self._schedule_type == "ALWAYS_OPEN":
            return True
        if current.date() in self._closed_dates:
            return False
        if self._schedule_type == "DAILY":
            return current.weekday() in self._trading_days

        day_start = current.weekday() * 86400
        day_end = day_start + 86399
        return any(
            max(day_start, start) <= min(day_end, end)
            for start, end in self._weekly_ranges()
        )

    def is_market_open(self, value: datetime | None = None) -> bool:
        """Return True when the timestamp is inside the configured schedule."""
        current = value or self.now()
        if self._schedule_type == "ALWAYS_OPEN":
            return True
        if current.date() in self._closed_dates:
            return False
        if self._schedule_type == "DAILY":
            return (
                current.weekday() in self._trading_days
                and self._market_start <= current.time() <= self._market_end
            )

        position = current.weekday() * 86400 + current.hour * 3600 + current.minute * 60
        weekly_open = any(start <= position <= end for start, end in self._weekly_ranges())
        in_break = (
            self._break_start is not None
            and self._time_in_range(current.time(), self._break_start, self._break_end)
        )
        return weekly_open and not in_break

    def current_session(self, value: datetime | None = None) -> str:
        """Return pre_market, open, or closed."""
        current = value or self.now()
        if self.is_market_open(current):
            return "open"
        if (
            self._schedule_type == "DAILY"
            and self.is_trading_day(current)
            and current.time() < self._market_start
        ):
            return "pre_market"
        return "closed"

    def next_open(self, value: datetime | None = None) -> datetime:
        """Return the next open timestamp for the configured schedule."""
        current = value or self.now()
        if self.is_market_open(current):
            return current
        candidate = current.replace(second=0, microsecond=0) + timedelta(minutes=1)
        for _ in range(370 * 24 * 60):
            if self.is_market_open(candidate):
                return candidate
            candidate += timedelta(minutes=1)
        raise RuntimeError("No market opening found within 370 days")

    def should_square_off(self, value: datetime | None = None) -> bool:
        """Return True at the DAILY square-off time while the market is open."""
        if self._schedule_type != "DAILY":
            return False
        current = value or self.now()
        return self.is_market_open(current) and current.time() >= self._square_off

    def detect_session_boundary(self, previous: datetime, current: datetime) -> bool:
        """Return True when session state changes between two timestamps."""
        return self.current_session(previous) != self.current_session(current)

    def _weekly_ranges(self) -> list[tuple[int, int]]:
        if self._week_start <= self._week_end:
            return [(self._week_start, self._week_end)]
        return [(self._week_start, self._WEEK_SECONDS - 1), (0, self._week_end)]

    @classmethod
    def _week_position(cls, day: str, value: time) -> int:
        return cls._DAYS[day.upper()] * 86400 + value.hour * 3600 + value.minute * 60

    @staticmethod
    def _time_in_range(value: time, start: time, end: time) -> bool:
        if start <= end:
            return start <= value < end
        return value >= start or value < end

    @staticmethod
    def _parse_time(value: str) -> time:
        return datetime.strptime(value, "%H:%M").time()
