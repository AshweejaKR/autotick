# -*- coding: utf-8 -*-
"""
Created on Sun Aug 30 09:25:06 2026

@author: ashwe
"""

from __future__ import annotations

from collections.abc import Callable
from threading import Event
from time import sleep
from typing import TypeVar

from autotick.interfaces.market_data import MarketDataProvider
from autotick.providers.session_pool import (
    BrokerAuthenticationError,
    BrokerError,
    BrokerSession,
)
from autotick.utils.logger import get_logger

logger = get_logger(__name__)
_T = TypeVar("_T")


class ReconnectStopped(RuntimeError):
    """Raised when shutdown is requested during broker recovery."""


class ReconnectManager:
    """Recover one broker session with hybrid retry limits."""

    def __init__(
        self,
        session: BrokerSession,
        market_data: MarketDataProvider,
        symbols: list[str],
        config: dict,
        stop_event: Event | None = None,
    ) -> None:
        self.session = session
        self.market_data = market_data
        self.symbols = symbols
        self.initial_delay = float(config["initial_delay_s"])
        self.max_delay = float(config["max_delay_s"])
        self.auth_max_attempts = int(config["auth_max_attempts"])
        self.stop_event = stop_event

    def recover(self, error: BrokerError, reconcile: Callable[[], _T]) -> _T:
        """Reconnect, restore subscriptions, reconcile, then resume."""
        delay = self.initial_delay
        attempt = 0
        auth_attempts = 0
        current: BrokerError = error

        while True:
            if self._stopped():
                raise ReconnectStopped("Broker recovery stopped")
            if isinstance(current, BrokerAuthenticationError):
                auth_attempts += 1
                if auth_attempts > self.auth_max_attempts:
                    raise current

            attempt += 1
            logger.warning(
                "Broker processing paused; reconnect attempt=%s delay=%.1fs auth_attempt=%s/%s",
                attempt,
                delay,
                auth_attempts,
                self.auth_max_attempts,
            )
            self._wait(delay)
            try:
                self.market_data.disconnect()
                self.session.reconnect()
                self.market_data.connect()
                self.market_data.subscribe(self.symbols)
                result = reconcile()
            except BrokerAuthenticationError as exc:
                if not isinstance(current, BrokerAuthenticationError):
                    auth_attempts += 1
                current = exc
            except BrokerError as exc:
                current = exc
            else:
                logger.done(
                    "Broker reconnected; subscriptions restored=%s; reconciliation completed",
                    len(self.symbols),
                )
                return result
            delay = min(delay * 2, self.max_delay)

    def _wait(self, delay: float) -> None:
        if self.stop_event is None:
            sleep(delay)
        elif self.stop_event.wait(delay):
            raise ReconnectStopped("Broker recovery stopped")

    def _stopped(self) -> bool:
        return self.stop_event is not None and self.stop_event.is_set()
