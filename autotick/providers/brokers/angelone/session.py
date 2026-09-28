# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 19:56:33 2026

@author: ashwe
"""

from __future__ import annotations

import json
from datetime import datetime
from time import monotonic, sleep
from typing import Any, Callable
from urllib.request import urlopen

from autotick.config.secrets import load_secrets
from autotick.models.market import ContractInfo
from autotick.providers.session_pool import (
    BrokerAuthenticationError,
    BrokerConnectionError,
    BrokerSession,
    BrokerWriteUncertainError,
)
from autotick.utils.logger import get_logger

logger = get_logger(__name__)


class AngelOneSession(BrokerSession):
    """Shared AngelOne SmartAPI authenticated session."""

    _INSTRUMENT_MASTER_URL = (
        "https://margincalculator.angelbroking.com/OpenAPI_File/files/"
        "OpenAPIScripMaster.json"
    )

    def __init__(self, credentials_file: str | None = None) -> None:
        if not credentials_file:
            raise ValueError("credentials_file is required for AngelOne")
        keys = load_secrets(credentials_file)
        self.api_key = keys["API_KEY"]
        self.client_id = keys["CLIENT_ID"]
        self.password = keys["PASSWORD"]
        self.totp_secret = keys["TOTP_SECRET"]
        self.client = self._create_client(self.api_key)
        self.refresh_token: str | None = None
        self._connected = False
        self._instruments: dict[tuple[str, str], tuple[str, str]] = {}
        self._contracts: dict[tuple[str, str], ContractInfo] | None = None
        self._last_api_call = 0.0

    def _throttle(self) -> None:
        wait = 1.0 - (monotonic() - self._last_api_call)
        if wait > 0:
            sleep(wait)
        self._last_api_call = monotonic()

    def call(self, func: Callable[..., Any], *args: Any, retries: int = 3, **kwargs: Any) -> Any:
        """Call a safe broker read with short local retries."""
        for attempt in range(1, retries + 1):
            self._throttle()
            try:
                response = func(*args, **kwargs)
            except Exception as exc:
                if self._is_auth_error(exc):
                    self._connected = False
                    raise BrokerAuthenticationError("AngelOne authentication failed") from exc
                if not self._is_retryable(exc):
                    raise
                if attempt == retries:
                    raise BrokerConnectionError("AngelOne read failed after retries") from exc
                logger.warning("AngelOne read failed; retry %s/%s: %s", attempt, retries, exc)
                sleep(attempt)
                continue

            if self._is_auth_error(response):
                self._connected = False
                raise BrokerAuthenticationError("AngelOne session expired")

            if self._is_retryable(response):
                if attempt == retries:
                    raise BrokerConnectionError("AngelOne read unavailable after retries")
                logger.warning("AngelOne read throttled/unavailable; retry %s/%s", attempt, retries)
                sleep(attempt)
                continue
            return response
        return None

    def call_once(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Call a broker write once with throttling and no automatic retry."""
        self._throttle()
        try:
            response = func(*args, **kwargs)
        except Exception as exc:
            if self._is_auth_error(exc):
                self._connected = False
            raise BrokerWriteUncertainError(
                "AngelOne write result is uncertain; write was not retried"
            ) from exc
        if self._is_auth_error(response) or self._is_retryable(response):
            if self._is_auth_error(response):
                self._connected = False
            raise BrokerWriteUncertainError(
                "AngelOne write result is uncertain; write was not retried"
            )
        return response

    def login(self) -> None:
        if self._connected:
            return
        from pyotp import TOTP

        try:
            self._throttle()
            totp = TOTP(self.totp_secret).now()
            response = self.client.generateSession(self.client_id, self.password, totp)
        except Exception as exc:
            self._raise_session_error(exc, "login")
        if not response or not response.get("status"):
            self._raise_session_error(response, "login")
        data = response.get("data")
        if not isinstance(data, dict) or not data.get("refreshToken"):
            self._connected = False
            raise BrokerAuthenticationError("AngelOne login returned invalid session data")
        self.refresh_token = str(data["refreshToken"])
        self._connected = True
        logger.done("AngelOne login completed")

    def logout(self) -> None:
        if not self._connected:
            return
        try:
            self._throttle()
            self.client.terminateSession(self.client_id)
        finally:
            self._connected = False
        logger.done("AngelOne logout completed")

    def refresh(self) -> None:
        self._connected = False
        if not self.refresh_token:
            raise BrokerAuthenticationError("AngelOne refresh token is unavailable")
        try:
            self._throttle()
            response = self.client.generateToken(self.refresh_token)
        except Exception as exc:
            self._raise_session_error(exc, "token refresh")
        if not response or not response.get("status"):
            self._raise_session_error(response, "token refresh")
        data = response.get("data")
        if not isinstance(data, dict):
            self._connected = False
            raise BrokerAuthenticationError(
                "AngelOne token refresh returned invalid session data"
            )
        self.refresh_token = str(
            data.get("refreshToken") or self.refresh_token
        )
        self._connected = True
        logger.done("AngelOne token refresh completed")

    def reconnect(self) -> None:
        """Refresh the token first, then use full login when refresh is rejected."""
        self._connected = False
        try:
            self.refresh()
        except BrokerAuthenticationError:
            logger.warning("AngelOne token refresh rejected; trying full login")
            self.login()

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

    def get_contract(self, symbol: str, exchange: str) -> ContractInfo | None:
        """Resolve expiry metadata from AngelOne's official instrument master."""
        trading_symbol, _ = self.get_instrument(symbol, exchange)
        if self._contracts is None:
            self._contracts = self._load_contracts()
        return self._contracts.get((trading_symbol.upper(), exchange.upper()))

    def _load_contracts(self) -> dict[tuple[str, str], ContractInfo]:
        try:
            with urlopen(self._INSTRUMENT_MASTER_URL, timeout=20) as response:
                payload = json.load(response)
        except (OSError, ValueError, TypeError) as exc:
            raise BrokerConnectionError(
                "AngelOne instrument master is temporarily unavailable"
            ) from exc
        if not isinstance(payload, list):
            raise BrokerConnectionError("AngelOne instrument master returned invalid data")
        return self._parse_contracts(payload)

    @staticmethod
    def _parse_contracts(payload: list[object]) -> dict[tuple[str, str], ContractInfo]:
        contracts: dict[tuple[str, str], ContractInfo] = {}
        for value in payload:
            if not isinstance(value, dict):
                continue
            instrument_type = str(value.get("instrumenttype") or "").upper()
            if not instrument_type.startswith(("FUT", "OPT")):
                continue
            symbol = str(value.get("symbol") or "").upper()
            exchange = str(value.get("exch_seg") or "").upper()
            expiry_text = str(value.get("expiry") or "").upper()
            if not symbol or not exchange or not expiry_text:
                continue
            try:
                expiry = datetime.strptime(expiry_text, "%d%b%Y").date()
            except ValueError:
                continue
            contracts[(symbol, exchange)] = ContractInfo(
                symbol=symbol,
                exchange=exchange,
                instrument_type=instrument_type,
                expiry=expiry,
            )
        return contracts

    @staticmethod
    def _is_auth_error(value: object) -> bool:
        if isinstance(value, dict):
            if value.get("status") is not False:
                return False
            code = str(value.get("errorcode", "")).upper()
            if code in {"AG8001", "AG8002", "AB1007", "AB8050"}:
                return True
            text = str(value.get("message", "")).lower()
        else:
            text = str(value).lower()
        return any(word in text for word in (
            "session expired",
            "unauthorized",
            "invalid jwt",
            "invalid token",
            "token expired",
        ))

    @staticmethod
    def _is_retryable(value: object) -> bool:
        if value is None:
            return True
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
            "couldn't parse the json response", "could not parse the json response",
            "jsondecodeerror",
        ))

    @classmethod
    def _raise_session_error(cls, value: object, operation: str) -> None:
        if value is None or cls._is_retryable(value):
            raise BrokerConnectionError(f"AngelOne {operation} is temporarily unavailable")
        raise BrokerAuthenticationError(f"AngelOne {operation} failed")

    @staticmethod
    def _create_client(api_key: str) -> Any:
        from SmartApi import SmartConnect

        return SmartConnect(api_key=api_key)
