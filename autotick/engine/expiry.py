# -*- coding: utf-8 -*-
"""Derivative expiry safety policy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from autotick.models.market import ContractInfo


@dataclass(frozen=True, slots=True)
class ExpiryState:
    """Resolved expiry action for one symbol at one point in time."""

    is_derivative: bool = False
    expiry: date | None = None
    cutoff: datetime | None = None
    block_entry: bool = False
    exit_due: bool = False
    reason: str | None = None


def derivative_symbol(symbol: str) -> bool:
    """Identify standard AngelOne futures and options trading symbols."""
    return symbol.upper().endswith(("FUT", "CE", "PE"))


def expiry_cutoff(
    contract: ContractInfo,
    calendar,
    session_config: dict,
    policy: dict,
) -> datetime:
    """Return the configured cutoff on an exchange trading day."""
    days_before = int(policy.get("trading_days_before", 1))
    cutoff_date = contract.expiry
    timezone = ZoneInfo(session_config.get("timezone", "Asia/Kolkata"))
    while days_before > 0:
        cutoff_date -= timedelta(days=1)
        probe = datetime.combine(cutoff_date, datetime.min.time(), timezone)
        if calendar.is_trading_day(probe):
            days_before -= 1
    cutoff_time = datetime.strptime(policy.get("time", "23:00"), "%H:%M").time()
    return datetime.combine(cutoff_date, cutoff_time, timezone)


def resolve_expiry_state(
    market_data,
    symbol: str,
    now: datetime,
    calendar,
    config: dict,
) -> ExpiryState:
    """Resolve whether a derivative entry or open position needs action."""
    policy = config.get("trade", {}).get("expiry_exit", {})
    if not policy.get("enabled", False):
        return ExpiryState()

    contract = market_data.get_contract(symbol)
    if contract is None:
        if derivative_symbol(symbol):
            return ExpiryState(
                is_derivative=True,
                block_entry=True,
                reason="expiry metadata unavailable",
            )
        return ExpiryState()
    if not contract.is_derivative:
        return ExpiryState()

    cutoff = expiry_cutoff(contract, calendar, config.get("session", {}), policy)
    if now.tzinfo is None:
        now = now.replace(tzinfo=cutoff.tzinfo)
    else:
        now = now.astimezone(cutoff.tzinfo)
    due = now >= cutoff
    return ExpiryState(
        is_derivative=True,
        expiry=contract.expiry,
        cutoff=cutoff,
        block_entry=due,
        exit_due=due,
        reason="expiry cutoff reached" if due else None,
    )
