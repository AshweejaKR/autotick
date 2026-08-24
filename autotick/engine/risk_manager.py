# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 22:07:58 2026

@author: ashwe
"""

from __future__ import annotations

from dataclasses import replace

from autotick.models.order import Order


class RiskManager:
    """Validate order risk, size quantity, and enforce daily limits."""

    def __init__(self, config: dict) -> None:
        risk = config["risk"]
        self.capital = float(config["capital"])
        self.quantity = int(config["trade"]["quantity"])
        self.max_loss = float(risk["max_loss"])
        self.risk_pct = float(risk["risk_per_trade_pct"])
        self.stoploss_pct = float(risk["stoploss_pct"])
        self.target_pct = float(risk["target_pct"])
        self.kill_switch = False

    def position_size(self, price: float) -> int:
        if price <= 0 or self.stoploss_pct <= 0:
            return 0
        risk_amount = self.capital * self.risk_pct / 100
        risk_per_unit = price * self.stoploss_pct / 100
        return min(self.quantity, int(risk_amount / risk_per_unit))

    def validate_order(self, order: Order, price: float | None = None) -> Order:
        if self.kill_switch:
            raise RuntimeError("Kill switch is active")
        current_price = price if price is not None else order.price
        if current_price is None or current_price <= 0:
            raise ValueError("Current price must be greater than zero")
        quantity = self.position_size(current_price)
        if quantity <= 0:
            raise ValueError("Order quantity is zero after risk sizing")
        return replace(order, quantity=min(order.quantity, quantity))

    def can_trade(self, price: float) -> bool:
        return not self.kill_switch and self.position_size(price) > 0

    def stop_loss(self, entry_price: float) -> float:
        return entry_price * (1 - self.stoploss_pct / 100)

    def target(self, entry_price: float) -> float:
        return entry_price * (1 + self.target_pct / 100)

    def check_daily_limits(self, pnl: float) -> bool:
        if pnl <= self.max_loss:
            self.activate_kill_switch()
        return not self.kill_switch

    def activate_kill_switch(self) -> None:
        self.kill_switch = True

    def reset_daily_state(self) -> None:
        self.kill_switch = False

    def update(self, capital: float) -> None:
        if capital <= 0:
            raise ValueError("capital must be greater than zero")
        self.capital = float(capital)
