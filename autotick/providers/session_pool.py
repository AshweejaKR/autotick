# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 23:02:28 2026

@author: ashwe

Shared broker-session lifecycle management for AutoTick providers.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol


class BrokerError(RuntimeError):
    """Base error for recoverable broker failures."""


class BrokerConnectionError(BrokerError):
    """Raised for temporary broker connectivity or service failures."""


class BrokerAuthenticationError(BrokerError):
    """Raised when broker authentication recovery is required."""


class BrokerWriteUncertainError(BrokerConnectionError):
    """Raised when a once-only broker write may have reached the broker."""


class BrokerSession(Protocol):
    """Minimal contract required by SessionPool."""

    def login(self) -> None: ...

    def logout(self) -> None: ...

    def refresh(self) -> None: ...

    def reconnect(self) -> None: ...

    def is_connected(self) -> bool: ...


class SessionPool:
    """Create, reuse, refresh, and close shared broker sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, BrokerSession] = {}

    def get_or_create(
        self,
        broker: str,
        factory: Callable[[], BrokerSession],
    ) -> BrokerSession:
        """Return one healthy shared session for a broker."""
        key = self._key(broker)
        session = self._sessions.get(key)

        if session is None:
            session = factory()
            session.login()
            self._sessions[key] = session
        elif not session.is_connected():
            session.reconnect()

        return session

    def close(self, broker: str) -> None:
        """Logout and remove one broker session."""
        session = self._sessions.pop(self._key(broker), None)
        if session is not None:
            session.logout()

    def close_all(self) -> None:
        """Logout and remove all broker sessions."""
        for broker in list(self._sessions):
            self.close(broker)

    @staticmethod
    def _key(broker: str) -> str:
        if not isinstance(broker, str) or not broker.strip():
            raise ValueError("broker must be a non-empty string")
        return broker.strip().lower()
