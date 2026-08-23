# -*- coding: utf-8 -*-
"""Provider bundle definitions and mode mapping for AutoTick.

Created on Sun Aug 23 23:02:28 2026

@author: ashwe
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from autotick.interfaces.account import AccountProvider
from autotick.interfaces.execution import ExecutionProvider
from autotick.interfaces.market_data import MarketDataProvider


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

    _MODE_MAPPING: dict[str, ModeMapping] = {
        "live": ModeMapping(
            market_data="broker",
            account="broker",
            execution="broker",
            session_timing="realtime",
        ),
        "paper": ModeMapping(
            market_data="broker",
            account="simulated",
            execution="simulated",
            session_timing="realtime",
        ),
        "backtest": ModeMapping(
            market_data="historical",
            account="simulated",
            execution="simulated",
            session_timing="fast",
        ),
        "replay": ModeMapping(
            market_data="historical",
            account="simulated",
            execution="simulated",
            session_timing="replay",
        ),
    }

    @classmethod
    def resolve_mode(cls, mode: str) -> ModeMapping:
        """Return the provider mapping for a configured trading mode."""
        if not isinstance(mode, str) or not mode.strip():
            raise ValueError("mode must be a non-empty string")

        normalized_mode = mode.strip().lower()
        try:
            return cls._MODE_MAPPING[normalized_mode]
        except KeyError as exc:
            supported = ", ".join(sorted(cls._MODE_MAPPING))
            raise ValueError(
                f"Unsupported trading mode '{mode}'. Supported modes: {supported}"
            ) from exc

    @classmethod
    def create_bundle(cls, mode: str, config: dict[str, Any]) -> ProviderBundle:
        """Create providers for a mode when concrete provider adapters exist."""
        cls.resolve_mode(mode)
        if not isinstance(config, dict):
            raise TypeError("config must be a dictionary")

        raise NotImplementedError(
            "Concrete provider construction is implemented in provider-layer phases"
        )
