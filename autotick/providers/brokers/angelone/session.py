# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 19:56:33 2026

@author: ashwe
"""

from __future__ import annotations

from pathlib import Path

import pyotp
from SmartApi import SmartConnect


class AngelOneSession:
    """Shared AngelOne SmartAPI authenticated session."""

    def __init__(self, credentials_file: str) -> None:
        keys = self._load_credentials(credentials_file)
        self.api_key = keys["API_KEY"]
        self.client_id = keys["CLIENT_ID"]
        self.password = keys["PASSWORD"]
        self.totp_secret = keys["TOTP_SECRET"]
        self.client = SmartConnect(api_key=self.api_key)
        self.refresh_token: str | None = None
        self._connected = False
        self._tokens: dict[tuple[str, str], str] = {}

    def login(self) -> None:
        if self._connected:
            return

        totp = pyotp.TOTP(self.totp_secret).now()
        response = self.client.generateSession(self.client_id, self.password, totp)
        if not response.get("status"):
            raise RuntimeError(f"AngelOne login failed: {response.get('message', 'unknown error')}")

        self.refresh_token = response["data"]["refreshToken"]
        self._connected = True

    def logout(self) -> None:
        if self._connected:
            self.client.terminateSession(self.client_id)
        self._connected = False

    def refresh(self) -> None:
        if not self.refresh_token:
            self.login()
            return
        self.client.generateToken(self.refresh_token)
        self._connected = True

    def is_connected(self) -> bool:
        return self._connected

    def get_token(self, symbol: str, exchange: str) -> str:
        key = (symbol.upper(), exchange.upper())
        if key in self._tokens:
            return self._tokens[key]

        response = self.client.searchScrip(key[1], key[0])
        for item in response.get("data") or []:
            if item.get("tradingsymbol", "").upper() == key[0]:
                token = str(item["symboltoken"])
                self._tokens[key] = token
                return token
        raise ValueError(f"AngelOne token not found for {symbol} on {exchange}")

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
