# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 23:02:28 2026

@author: ashwe

Provider bundle definitions and mode mapping for AutoTick.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from autotick.engine.market_session import CalendarSessionManager
from autotick.interfaces.account import AccountProvider
from autotick.interfaces.execution import ExecutionProvider
from autotick.interfaces.market_data import MarketDataProvider
from autotick.providers.brokers.angelone import (
    AngelOneAccountProvider,
    AngelOneExecutionProvider,
    AngelOneMarketDataProvider,
    AngelOneSession,
)
from autotick.providers.brokers.simulated import (
    SimulatedAccountProvider,
    SimulatedExecutionProvider,
    SimulatedSession,
)
from autotick.providers.historical import HistoricalProvider
from autotick.providers.session_pool import SessionPool


@dataclass(frozen=True, slots=True)
class ModeMapping:
    """Describe provider and session choices for one trading mode."""

    market_data: str
    account: str
    execution: str
    session_timing: str


@dataclass(slots=True)
class ProviderBundle:
    """Group the mode-neutral providers consumed by the trading core."""

    market_data: MarketDataProvider
    account: AccountProvider
    execution: ExecutionProvider
    calendar_session: Any | None = None


class ProviderFactory:
    """Resolve mode-specific provider wiring from one centralized mapping."""

    _session_pool = SessionPool()
    _MODE_MAPPING: dict[str, ModeMapping] = {
        "live": ModeMapping("broker", "broker", "broker", "realtime"),
        "paper": ModeMapping("broker", "simulated", "simulated", "realtime"),
        "backtest": ModeMapping("historical", "simulated", "simulated", "fast"),
        "replay": ModeMapping("historical", "simulated", "simulated", "replay"),
    }

    @classmethod
    def resolve_mode(cls, mode: str) -> ModeMapping:
        """Return the provider mapping for a configured trading mode."""
        if not isinstance(mode, str) or not mode.strip():
            raise ValueError("mode must be a non-empty string")
        try:
            return cls._MODE_MAPPING[mode.strip().lower()]
        except KeyError as exc:
            supported = ", ".join(sorted(cls._MODE_MAPPING))
            raise ValueError(f"Unsupported trading mode '{mode}'. Supported modes: {supported}") from exc

    @classmethod
    def create_bundle(cls, mode: str, config: dict[str, Any]) -> ProviderBundle:
        """Create the provider bundle for an implemented trading mode."""
        normalized = mode.strip().lower()
        cls.resolve_mode(normalized)
        if not isinstance(config, dict):
            raise TypeError("config must be a dictionary")

        if normalized == "live":
            return cls._create_live(config)
        if normalized == "paper":
            return cls._create_paper(config)
        if normalized in {"backtest", "replay"}:
            return cls._create_historical(normalized, config)
        raise NotImplementedError(f"{normalized} mode is not implemented yet")

    @classmethod
    def _broker_session(cls, config: dict[str, Any]) -> tuple[str, AngelOneSession]:
        broker = str(config["broker"]).strip().lower()
        if broker != "angelone":
            raise ValueError("Supported broker: angelone")
        broker_config = config["broker_config"][broker]
        session = cls._session_pool.get_or_create(
            broker,
            lambda: AngelOneSession(broker_config["credentials_file"]),
        )
        return broker, session

    @classmethod
    def _create_live(cls, config: dict[str, Any]) -> ProviderBundle:
        _, session = cls._broker_session(config)
        market_data = AngelOneMarketDataProvider(session, config["market"]["exchange"])
        account = AngelOneAccountProvider(session, float(config["capital"]))
        execution = AngelOneExecutionProvider(session)
        calendar = CalendarSessionManager(config["session"])
        calendar.configure_mode("live")
        return ProviderBundle(market_data, account, execution, calendar)

    @classmethod
    def _create_paper(cls, config: dict[str, Any]) -> ProviderBundle:
        _, session = cls._broker_session(config)
        market_data = AngelOneMarketDataProvider(session, config["market"]["exchange"])
        return cls._simulated_bundle("paper", config, market_data)

    @classmethod
    def _create_historical(cls, mode: str, config: dict[str, Any]) -> ProviderBundle:
        csv_config = config.get("backtest", {}).get("csv", {})
        market_data = (
            HistoricalProvider.from_csv(csv_config["data_file"])
            if csv_config.get("enabled") and csv_config.get("data_file")
            else HistoricalProvider()
        )
        return cls._simulated_bundle(mode, config, market_data)

    @staticmethod
    def _simulated_bundle(
        mode: str,
        config: dict[str, Any],
        market_data: MarketDataProvider,
    ) -> ProviderBundle:
        session = SimulatedSession()
        session.set_market_data(market_data)
        account = SimulatedAccountProvider(session, float(config["capital"]))
        execution = SimulatedExecutionProvider(session)
        calendar = CalendarSessionManager(config["session"])
        calendar.configure_mode(mode)
        return ProviderBundle(market_data, account, execution, calendar)
