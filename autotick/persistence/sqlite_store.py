# -*- coding: utf-8 -*-
"""
Created on Sun Aug 30 09:25:06 2026

@author: ashwe
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS state_snapshots (
    profile_key TEXT PRIMARY KEY,
    schema_version INTEGER NOT NULL,
    updated_at TEXT NOT NULL,
    payload TEXT NOT NULL
)
"""


class PersistenceError(RuntimeError):
    """Raised when persisted runtime state cannot be read or written safely."""


class SQLiteStateStore:
    """Store one atomic runtime snapshot per AutoTick profile."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()
        self._last_payload: dict[str, str] = {}

    def load(self, profile_key: str) -> dict | None:
        """Load and validate one profile snapshot."""
        if not self.path.exists():
            return None
        try:
            with self._connect() as connection:
                result = connection.execute("PRAGMA quick_check").fetchone()
                if result is None or result[0] != "ok":
                    raise PersistenceError("SQLite integrity check failed")
                connection.execute(_CREATE_TABLE)
                row = connection.execute(
                    "SELECT schema_version, payload FROM state_snapshots "
                    "WHERE profile_key = ?",
                    (profile_key,),
                ).fetchone()
        except (OSError, sqlite3.Error) as exc:
            raise PersistenceError(
                f"Unable to load state database: {self.path}"
            ) from exc

        if row is None:
            return None
        if row[0] != SCHEMA_VERSION:
            raise PersistenceError(f"Unsupported state schema version: {row[0]}")
        try:
            payload = json.loads(row[1])
        except (TypeError, json.JSONDecodeError) as exc:
            raise PersistenceError("Persisted state payload is invalid") from exc
        if not isinstance(payload, dict):
            raise PersistenceError("Persisted state payload must be a mapping")
        self._last_payload[profile_key] = row[1]
        return payload

    def save(self, profile_key: str, payload: dict) -> bool:
        """Atomically save a changed snapshot; return True when written."""
        serialized = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        if self._last_payload.get(profile_key) == serialized:
            return False

        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self._connect() as connection:
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute(_CREATE_TABLE)
                connection.execute(
                    """
                    INSERT INTO state_snapshots (
                        profile_key, schema_version, updated_at, payload
                    ) VALUES (?, ?, ?, ?)
                    ON CONFLICT(profile_key) DO UPDATE SET
                        schema_version = excluded.schema_version,
                        updated_at = excluded.updated_at,
                        payload = excluded.payload
                    """,
                    (
                        profile_key,
                        SCHEMA_VERSION,
                        datetime.now(timezone.utc).isoformat(),
                        serialized,
                    ),
                )
        except (OSError, sqlite3.Error) as exc:
            raise PersistenceError(
                f"Unable to save state database: {self.path}"
            ) from exc
        self._last_payload[profile_key] = serialized
        return True

    def clear(self, profile_key: str) -> None:
        """Delete one runtime profile without affecting other profiles."""
        if not self.path.exists():
            return
        try:
            with self._connect() as connection:
                connection.execute(_CREATE_TABLE)
                connection.execute(
                    "DELETE FROM state_snapshots WHERE profile_key = ?",
                    (profile_key,),
                )
        except (OSError, sqlite3.Error) as exc:
            raise PersistenceError(
                f"Unable to clear state database: {self.path}"
            ) from exc
        self._last_payload.pop(profile_key, None)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        return connection
