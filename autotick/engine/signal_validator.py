# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 00:19:15 2026

@author: ashwe

Structural validation for strategy-generated signals before engine processing.
"""

from __future__ import annotations

from numbers import Real

from autotick.models.signal import Signal, SignalType


class SignalValidationError(ValueError):
    """Raised when a strategy-generated signal is structurally invalid."""


class SignalValidator:
    """Validate strategy signal structure before risk/trade processing."""

    @staticmethod
    def validate(signal: Signal) -> None:
        """Validate one signal and raise SignalValidationError on failure."""
        if not isinstance(signal, Signal):
            raise SignalValidationError("signal must be a Signal instance")

        if not isinstance(signal.symbol, str) or not signal.symbol.strip():
            raise SignalValidationError("signal.symbol must be a non-empty string")

        if not isinstance(signal.exchange, str) or not signal.exchange.strip():
            raise SignalValidationError("signal.exchange must be a non-empty string")

        if not isinstance(signal.signal_type, SignalType):
            raise SignalValidationError("signal.signal_type must be a SignalType")

        if signal.quantity is not None:
            if isinstance(signal.quantity, bool) or not isinstance(signal.quantity, int):
                raise SignalValidationError("signal.quantity must be an integer when provided")
            if signal.quantity <= 0:
                raise SignalValidationError("signal.quantity must be greater than zero when provided")

        if signal.price is not None:
            if isinstance(signal.price, bool) or not isinstance(signal.price, Real):
                raise SignalValidationError("signal.price must be numeric when provided")
            if signal.price <= 0:
                raise SignalValidationError("signal.price must be greater than zero when provided")
