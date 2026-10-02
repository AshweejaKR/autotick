# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 18:15:19 2026

@author: ashwe
"""

from __future__ import annotations

"""Common account models for AutoTick."""

from dataclasses import dataclass


@dataclass(slots=True)
class Account:
    configured_capital: float
    balance: float | None = None
    available_margin: float | None = None
    buying_power: float | None = None
    account_id: str | None = None
    name: str | None = None
    email: str | None = None
    phone: str | None = None
