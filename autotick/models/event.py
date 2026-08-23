"""Common event models for AutoTick."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EventType(str, Enum):
    MARKET_DATA = "MARKET_DATA"
    SIGNAL = "SIGNAL"
    ORDER = "ORDER"
    POSITION = "POSITION"
    TRADE = "TRADE"
    ACCOUNT = "ACCOUNT"


@dataclass(slots=True)
class Event:
    event_type: EventType
    data: Any
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
