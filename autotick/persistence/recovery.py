# -*- coding: utf-8 -*-
"""
Created on Sun Aug 30 09:25:06 2026

@author: ashwe
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any

from autotick.config.secrets import load_secrets
from autotick.engine.risk_manager import RiskManager
from autotick.engine.trade_manager import ReconciliationResult, TradeManager
from autotick.interfaces.account import AccountProvider
from autotick.interfaces.execution import ExecutionProvider
from autotick.models import (
    Account,
    Order,
    OrderIntent,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    PositionStatus,
    PositionType,
    Trade,
)
from autotick.persistence.sqlite_store import PersistenceError, SQLiteStateStore
from autotick.providers.brokers.simulated import (
    SimulatedAccountProvider,
    SimulatedExecutionProvider,
)
from autotick.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RecoveryResult:
    """Recovered runner state returned before strategy startup."""

    trading_date: date
    entered_symbols: frozenset[str] = frozenset()
    blocked_symbols: frozenset[str] = frozenset()
    last_processed_at: datetime | None = None
    recovered: bool = False


class RecoveryManager:
    """Persist and reconcile normalized AutoTick runtime state."""

    def __init__(
        self,
        config: dict,
        trades: TradeManager,
        risk: RiskManager,
        account: AccountProvider,
        execution: ExecutionProvider,
    ) -> None:
        self.config = config
        self.trades = trades
        self.risk = risk
        self.account = account
        self.execution = execution
        self.store = SQLiteStateStore(config["persistence"]["state_path"])
        self.profile = self._build_profile(config)
        profile_json = json.dumps(self.profile, separators=(",", ":"), sort_keys=True)
        self.profile_key = hashlib.sha256(profile_json.encode("utf-8")).hexdigest()
        self.mode = str(config["mode"]).lower()
        self.failed = False

    def recover(self, trading_date: date) -> RecoveryResult:
        """Restore one Live/Paper profile and reconcile provider truth."""
        if self.mode not in {"live", "paper"}:
            return RecoveryResult(trading_date)

        payload = self.store.load(self.profile_key)
        recovered = payload is not None
        last_processed_at = None
        if payload is not None:
            try:
                self._validate_profile(payload)
                saved_date = date.fromisoformat(str(payload["trading_date"]))
                last_processed_at = _datetime(payload.get("last_processed_at"))
                trade_state = _trade_state_from_dict(payload["trade_manager"])
                self.trades.restore_state(**trade_state)

                if saved_date == trading_date:
                    self.risk.restore_state(payload["risk"])
                else:
                    self.risk.reset_daily_state()

                if self.mode == "paper":
                    self._restore_simulated(payload)
            except PersistenceError:
                raise
            except (KeyError, TypeError, ValueError) as exc:
                raise PersistenceError("Persisted recovery state is invalid") from exc

        reconciled = self.reconcile(trading_date)
        if recovered:
            logger.done(
                "Recovered state profile=%s orders=%s positions=%s trades=%s",
                self.profile_key[:12],
                len(self.trades.get_orders()),
                len(self.trades.get_positions()),
                len(self.trades.get_trades()),
            )
        else:
            logger.info("No saved state found for profile=%s", self.profile_key[:12])
        return RecoveryResult(
            trading_date=trading_date,
            entered_symbols=reconciled.entered_symbols,
            blocked_symbols=reconciled.blocked_symbols,
            last_processed_at=last_processed_at,
            recovered=recovered,
        )

    def reconcile(self, trading_date: date) -> RecoveryResult:
        """Reconcile current in-memory state after a broker reconnect."""
        differences = self.trades.reconcile_startup(trading_date)
        self._handle_differences(differences)
        return RecoveryResult(
            trading_date=trading_date,
            entered_symbols=frozenset(self.trades.entered_symbols(trading_date)),
            blocked_symbols=differences.blocked_symbols,
        )

    def save(
        self,
        trading_date: date,
        last_processed_at: datetime | None = None,
    ) -> bool:
        """Save the current normalized state when it changed."""
        if self.failed:
            return False
        try:
            payload = self._snapshot(trading_date, last_processed_at)
            return self.store.save(self.profile_key, payload)
        except PersistenceError:
            self.failed = True
            raise
        except Exception as exc:
            self.failed = True
            raise PersistenceError("Unable to build runtime state snapshot") from exc

    def _snapshot(
        self,
        trading_date: date,
        last_processed_at: datetime | None,
    ) -> dict[str, Any]:
        state = self.trades.export_state()
        payload: dict[str, Any] = {
            "profile": self.profile,
            "trading_date": trading_date.isoformat(),
            "last_processed_at": (
                last_processed_at.isoformat() if last_processed_at is not None else None
            ),
            "trade_manager": {
                "orders": [_order_to_dict(item) for item in state["orders"]],
                "positions": [_position_to_dict(item) for item in state["positions"]],
                "trades": [_trade_to_dict(item) for item in state["trades"]],
                "exit_levels": state["exit_levels"],
            },
            "risk": self.risk.export_state(),
        }
        if self.mode == "paper":
            payload["account"] = asdict(self.account.get_profile())
            simulated = self._simulated_execution()
            state = simulated.export_state()
            payload["simulated_execution"] = {
                "orders": [_order_to_dict(item) for item in state["orders"]],
                "positions": [_position_to_dict(item) for item in state["positions"]],
                "trades": [_trade_to_dict(item) for item in state["trades"]],
                "pnl": state["pnl"],
            }
        return payload

    def _restore_simulated(self, payload: dict) -> None:
        try:
            account = Account(**payload["account"])
            state = payload["simulated_execution"]
            orders = [_order_from_dict(item) for item in state["orders"]]
            positions = [_position_from_dict(item) for item in state["positions"]]
            trades = [_trade_from_dict(item) for item in state["trades"]]
            pnl = float(state["pnl"])
        except (KeyError, TypeError, ValueError) as exc:
            raise PersistenceError("Persisted simulated state is invalid") from exc
        if not isinstance(self.account, SimulatedAccountProvider):
            raise PersistenceError("Paper recovery requires a simulated account")
        self.account.restore_state(account)
        self._simulated_execution().restore_state(orders, positions, trades, pnl)

    def _simulated_execution(self) -> SimulatedExecutionProvider:
        if not isinstance(self.execution, SimulatedExecutionProvider):
            raise PersistenceError("Paper recovery requires simulated execution")
        return self.execution

    def _validate_profile(self, payload: dict) -> None:
        if payload.get("profile") != self.profile:
            raise PersistenceError(
                "Persisted state profile does not match configuration"
            )

    def _handle_differences(self, result: ReconciliationResult) -> None:
        if result.changed_orders or result.closed_positions:
            logger.warning(
                "Reconciled state: changed_orders=%s closed_positions=%s",
                result.changed_orders,
                result.closed_positions,
            )
        if result.unknown_orders or result.unknown_positions:
            logger.warning(
                "Ignored unknown broker state: orders=%s positions=%s",
                result.unknown_orders,
                result.unknown_positions,
            )
        if result.unresolved_orders:
            self.risk.activate_kill_switch()
            logger.error(
                "Recovery found %s unresolved same-day order(s); new entries blocked",
                result.unresolved_orders,
            )

    @staticmethod
    def _build_profile(config: dict) -> dict[str, Any]:
        symbols = config["market"]["symbols"]
        if isinstance(symbols, str):
            symbols = [symbols]
        broker = str(config["broker"]).lower()
        account_id = ""
        if broker == "angelone":
            path = config.get("broker_config", {}).get("angelone", {}).get("credentials_file")
            if path:
                account_id = load_secrets(path)["CLIENT_ID"]
        return {
            "mode": str(config["mode"]).lower(),
            "broker": broker,
            "account_id": account_id,
            "exchange": str(config["market"]["exchange"]).upper(),
            "strategy": str(config["strategy"]).lower(),
            "symbols": sorted(str(symbol).upper() for symbol in symbols),
        }


def _order_to_dict(order: Order) -> dict[str, Any]:
    return {
        "order_id": order.order_id,
        "symbol": order.symbol,
        "exchange": order.exchange,
        "side": order.side.value,
        "quantity": order.quantity,
        "order_type": order.order_type.value,
        "price": order.price,
        "status": order.status.value,
        "intent": order.intent.value,
        "position_type": order.position_type.value,
        "status_updated_at": (
            order.status_updated_at.isoformat()
            if order.status_updated_at is not None
            else None
        ),
    }


def _order_from_dict(item: dict) -> Order:
    return Order(
        order_id=str(item["order_id"]),
        symbol=str(item["symbol"]),
        exchange=str(item["exchange"]),
        side=OrderSide(item["side"]),
        quantity=int(item["quantity"]),
        order_type=OrderType(item["order_type"]),
        price=float(item["price"]) if item.get("price") is not None else None,
        status=OrderStatus(item["status"]),
        intent=OrderIntent(item["intent"]),
        position_type=PositionType(item["position_type"]),
        status_updated_at=_datetime(item.get("status_updated_at")),
    )


def _position_to_dict(position: Position) -> dict[str, Any]:
    return {
        "symbol": position.symbol,
        "exchange": position.exchange,
        "quantity": position.quantity,
        "average_price": position.average_price,
        "realized_pnl": position.realized_pnl,
        "unrealized_pnl": position.unrealized_pnl,
        "status": position.status.value,
        "position_type": position.position_type.value,
    }


def _position_from_dict(item: dict) -> Position:
    return Position(
        symbol=str(item["symbol"]),
        exchange=str(item["exchange"]),
        quantity=int(item["quantity"]),
        average_price=float(item["average_price"]),
        realized_pnl=float(item.get("realized_pnl", 0.0)),
        unrealized_pnl=float(item.get("unrealized_pnl", 0.0)),
        status=PositionStatus(item["status"]),
        position_type=PositionType(item["position_type"]),
    )


def _trade_to_dict(trade: Trade) -> dict[str, Any]:
    return {
        "trade_id": trade.trade_id,
        "order_id": trade.order_id,
        "symbol": trade.symbol,
        "exchange": trade.exchange,
        "side": trade.side.value,
        "quantity": trade.quantity,
        "price": trade.price,
        "timestamp": trade.timestamp.isoformat(),
    }


def _trade_from_dict(item: dict) -> Trade:
    timestamp = _datetime(item["timestamp"])
    if timestamp is None:
        raise ValueError("trade timestamp is required")
    return Trade(
        trade_id=str(item["trade_id"]),
        order_id=str(item["order_id"]),
        symbol=str(item["symbol"]),
        exchange=str(item["exchange"]),
        side=OrderSide(item["side"]),
        quantity=int(item["quantity"]),
        price=float(item["price"]),
        timestamp=timestamp,
    )


def _trade_state_from_dict(state: dict) -> dict[str, Any]:
    try:
        return {
            "orders": [_order_from_dict(item) for item in state["orders"]],
            "positions": [_position_from_dict(item) for item in state["positions"]],
            "trades": [_trade_from_dict(item) for item in state["trades"]],
            "exit_levels": list(state["exit_levels"]),
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise PersistenceError("Persisted trade state is invalid") from exc


def _datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise PersistenceError("Persisted datetime is invalid") from exc
