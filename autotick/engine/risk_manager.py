# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 22:07:58 2026

@author: ashwe
"""

from __future__ import annotations

from dataclasses import replace

from autotick.models.order import Order, OrderSide


class RiskManager:
    """Validate order risk, size quantity, and enforce daily limits."""

    def __init__(self, config: dict) -> None:
        self.config = config
        risk = config["risk"]
        trade = config["trade"]
        self.capital = float(config["capital"])
        self.quantity = int(trade["quantity"]) if "quantity" in trade else None
        self.max_position_value = (
            float(trade["max_position_value"])
            if "max_position_value" in trade
            else None
        )
        self.max_loss = float(risk["max_loss"])
        self.max_trades = int(risk["max_trades_per_day"])
        self.risk_pct = float(risk["risk_per_trade_pct"])
        self.stoploss_pct = float(risk["stoploss_pct"])
        self.target_pct = float(risk["target_pct"])
        self.trailing_activation_pct = float(
            risk.get("trailing_activation_pct", self.target_pct)
        )
        self.trailing_atr_period = int(risk["trailing_atr_period"])
        self.trailing_atr_interval = str(risk["trailing_atr_interval"]).lower()
        self.trailing_atr_multiplier = float(risk["trailing_atr_multiplier"])
        self.trade_count = 0
        self.daily_pnl = 0.0
        self.kill_switch = False
        self.persistence_failed = False

    def position_size(self, price: float, margin_aware: bool = False) -> int:
        if price <= 0 or self.stoploss_pct <= 0:
            return 0
        trade_capital = (
            min(self.capital, self.max_position_value)
            if self.max_position_value is not None
            else self.capital
        )
        risk_amount = trade_capital * self.risk_pct / 100
        risk_per_unit = price * self.stoploss_pct / 100
        if margin_aware:
            quantity_limit = (
                int(self.quantity)
                if self.quantity is not None
                else int(risk_amount / risk_per_unit)
            )
        elif self.max_position_value is not None:
            quantity_limit = int(trade_capital / price)
        else:
            quantity_limit = int(self.quantity or 0)
        return min(quantity_limit, int(risk_amount / risk_per_unit))

    def validate_order(
        self,
        order: Order,
        price: float | None = None,
        margin_aware: bool = False,
    ) -> Order:
        current_price = price if price is not None else order.price
        if current_price is None or current_price <= 0:
            raise ValueError("Current price must be greater than zero")
        if not self.can_trade(current_price, margin_aware):
            raise RuntimeError("Trading blocked by daily risk limits")
        quantity = self.position_size(current_price, margin_aware)
        return replace(order, quantity=min(order.quantity, quantity))

    def can_trade(self, price: float, margin_aware: bool = False) -> bool:
        return (
            not self.kill_switch
            and self.trade_count < self.max_trades
            and self.position_size(price, margin_aware) > 0
        )

    def record_entry(self) -> None:
        """Count one entry execution and activate the limit kill switch."""
        self.trade_count += 1
        if self.trade_count >= self.max_trades:
            self.activate_kill_switch()

    def stop_loss(
        self,
        entry_price: float,
        side: OrderSide = OrderSide.BUY,
    ) -> float:
        direction = -1 if side == OrderSide.BUY else 1
        return entry_price * (1 + direction * self.stoploss_pct / 100)

    def target(
        self,
        entry_price: float,
        side: OrderSide = OrderSide.BUY,
    ) -> float:
        activation_pct = (
            self.trailing_activation_pct if self.trailing_enabled else self.target_pct
        )
        direction = 1 if side == OrderSide.BUY else -1
        return entry_price * (1 + direction * activation_pct / 100)

    @property
    def trailing_enabled(self) -> bool:
        return self.trailing_atr_multiplier > 0

    def trailing_stop(
        self,
        best_price: float,
        atr: float,
        side: OrderSide = OrderSide.BUY,
    ) -> float:
        if atr <= 0:
            raise ValueError("ATR must be greater than zero")
        direction = -1 if side == OrderSide.BUY else 1
        return best_price + direction * atr * self.trailing_atr_multiplier

    def check_daily_limits(self, pnl: float) -> bool:
        if pnl <= self.max_loss or self.trade_count >= self.max_trades:
            self.activate_kill_switch()
        return not self.kill_switch

    def record_realized_pnl(self, pnl: float) -> bool:
        """Add realized P&L and enforce the configured daily max loss."""
        self.daily_pnl += float(pnl)
        return self.check_daily_limits(self.daily_pnl)

    def activate_kill_switch(self) -> None:
        self.kill_switch = True

    def block_for_persistence_failure(self) -> None:
        """Block entries until restart after runtime state can no longer be saved."""
        self.persistence_failed = True
        self.activate_kill_switch()

    def reset_daily_state(self) -> None:
        self.trade_count = 0
        self.daily_pnl = 0.0
        self.kill_switch = self.persistence_failed

    def export_state(self) -> dict[str, int | float | bool]:
        """Return daily risk state for persistence."""
        return {
            "trade_count": self.trade_count,
            "daily_pnl": self.daily_pnl,
            "kill_switch": self.kill_switch,
            "persistence_failed": self.persistence_failed,
        }

    def restore_state(self, state: dict) -> None:
        """Restore validated daily risk state."""
        trade_count = state.get("trade_count", 0)
        daily_pnl = state.get("daily_pnl", 0.0)
        kill_switch = state.get("kill_switch", False)
        persistence_failed = state.get("persistence_failed", False)
        if isinstance(trade_count, bool) or not isinstance(trade_count, int):
            raise ValueError("risk trade_count must be an integer")
        if trade_count < 0:
            raise ValueError("risk trade_count must not be negative")
        if isinstance(daily_pnl, bool) or not isinstance(daily_pnl, (int, float)):
            raise ValueError("risk daily_pnl must be a number")
        if not isinstance(kill_switch, bool):
            raise ValueError("risk kill_switch must be boolean")
        if not isinstance(persistence_failed, bool):
            raise ValueError("risk persistence_failed must be boolean")
        self.trade_count = trade_count
        self.daily_pnl = float(daily_pnl)
        self.persistence_failed = persistence_failed
        self.kill_switch = (
            kill_switch
            or persistence_failed
            or trade_count >= self.max_trades
            or self.daily_pnl <= self.max_loss
        )

    def update(self, capital: float) -> None:
        self.capital = max(0.0, float(capital))
