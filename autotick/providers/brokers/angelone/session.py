# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 19:56:33 2026

@author: ashwe
"""

from __future__ import annotations

from pathlib import Path
from time import monotonic, sleep
from typing import Any, Callable

from autotick.providers.session_pool import BrokerSession
from autotick.utils.logger import get_logger

logger = get_logger(__name__)


class AngelOneSession(BrokerSession):
    """Shared AngelOne SmartAPI authenticated session."""

    def __init__(self, credentials_file: str | None = None) -> None:
        if not credentials_file:
            raise ValueError("credentials_file is required for AngelOne")
        keys = self._load_credentials(credentials_file)
        self.api_key = keys["API_KEY"]
        self.client_id = keys["CLIENT_ID"]
        self.password = keys["PASSWORD"]
        self.totp_secret = keys["TOTP_SECRET"]
        self.client = self._create_client(self.api_key)
        self.refresh_token: str | None = None
        self._connected = False
        self._instruments: dict[tuple[str, str], tuple[str, str]] = {}
        self._last_api_call = 0.0

    def _throttle(self) -> None:
        wait = 1.0 - (monotonic() - self._last_api_call)
        if wait > 0:
            sleep(wait)
        self._last_api_call = monotonic()

    def call(self, func: Callable[..., Any], *args: Any, retries: int = 3, **kwargs: Any) -> Any:
        """Call a safe broker read with throttling, retry, and auth recovery."""
        auth_retried = False
        for attempt in range(1, retries + 1):
            self._throttle()
            try:
                response = func(*args, **kwargs)
            except Exception as exc:
                if attempt == retries or not self._is_retryable(exc):
                    raise
                logger.warning("AngelOne read failed; retry %s/%s: %s", attempt, retries, exc)
                sleep(attempt)
                continue

            if self._is_auth_error(response) and not auth_retried:
                logger.warning("AngelOne session expired; re-authenticating")
                self._connected = False
                self.login()
                auth_retried = True
                continue

            if self._is_retryable(response) and attempt < retries:
                logger.warning("AngelOne read throttled/unavailable; retry %s/%s", attempt, retries)
                sleep(attempt)
                continue
            return response
        return None

    def call_once(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Call a broker write once with throttling and no automatic retry."""
        self._throttle()
        return func(*args, **kwargs)

    def login(self) -> None:
        if self._connected:
            return
        from pyotp import TOTP

        self._throttle()
        totp = TOTP(self.totp_secret).now()
        response = self.client.generateSession(self.client_id, self.password, totp)
        if not response or not response.get("status"):
            raise RuntimeError(f"AngelOne login failed: {(response or {}).get('message', 'unknown error')}")
        self.refresh_token = response["data"]["refreshToken"]
        self._connected = True
        logger.done("AngelOne login completed")

    def logout(self) -> None:
        if not self._connected:
            return
        self._throttle()
        self.client.terminateSession(self.client_id)
        self._connected = False
        logger.done("AngelOne logout completed")

    def refresh(self) -> None:
        if not self.refresh_token:
            self.login()
            return
        self._throttle()
        response = self.client.generateToken(self.refresh_token)
        if not response or not response.get("status"):
            self._connected = False
            self.login()
            return
        self._connected = True
        logger.done("AngelOne token refresh completed")

    def is_connected(self) -> bool:
        return self._connected

    def get_instrument(self, symbol: str, exchange: str) -> tuple[str, str]:
        key = (symbol.upper(), exchange.upper())
        if key in self._instruments:
            return self._instruments[key]

        response = self.call(self.client.searchScrip, key[1], key[0]) or {}
        matches = response.get("data") or []
        item = next(
            (
                value
                for value in matches
                if value.get("tradingsymbol", "").upper() == key[0]
                or value.get("tradingsymbol", "").upper().startswith(f"{key[0]}-")
            ),
            None,
        )
        if item is None:
            raise ValueError(f"AngelOne token not found for {symbol} on {exchange}")

        instrument = (str(item["tradingsymbol"]), str(item["symboltoken"]))
        self._instruments[key] = instrument
        return instrument

    def get_token(self, symbol: str, exchange: str) -> str:
        return self.get_instrument(symbol, exchange)[1]

    @staticmethod
    def _is_auth_error(value: object) -> bool:
        if not isinstance(value, dict) or value.get("status") is not False:
            return False
        text = f"{value.get('errorcode', '')} {value.get('message', '')}".lower()
        return any(word in text for word in ("token", "session expired", "unauthorized", "jwt"))

    @staticmethod
    def _is_retryable(value: object) -> bool:
        if isinstance(value, (TimeoutError, ConnectionError, OSError)):
            return True
        if isinstance(value, dict):
            if value.get("status") is not False:
                return False
            text = f"{value.get('errorcode', '')} {value.get('message', '')}".lower()
        else:
            text = str(value).lower()
        return any(word in text for word in (
            "rate limit", "access rate", "too many", "timeout", "timed out",
            "temporarily", "service unavailable", "connection", "429", "503",
        ))

    @staticmethod
    def _load_credentials(path: str) -> dict[str, str]:
        credentials: dict[str, str] = {}
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                credentials[key.strip()] = value.strip()

        required = {"API_KEY", "CLIENT_ID", "PASSWORD", "TOTP_SECRET"}
        missing = sorted(required - credentials.keys())
        if missing:
            raise ValueError(f"Missing AngelOne credentials: {', '.join(missing)}")
        return credentials

    @staticmethod
    def _create_client(api_key: str) -> Any:
        from SmartApi import SmartConnect

        return SmartConnect(api_key=api_key)
