# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 15:48:09 2026

@author: ashwe

AutoTick command-line entry point and mode runner.
"""

from __future__ import annotations

import argparse
from contextlib import suppress
from pathlib import Path
from threading import Event
from time import sleep
from uuid import uuid4

from autotick.config.loader import load_config
from autotick.engine import (
    CalendarSessionManager,
    RiskManager,
    SignalValidator,
    TradeManager,
)
from autotick.models import Order, OrderSide, PositionType, SignalType
from autotick.providers.factory import ProviderFactory
from autotick.strategy.context import StrategyContext
from autotick.strategy.simple_strategy import SimpleStrategy
from autotick.utils.logger import configure_logging, get_logger, log_call


logger = get_logger(__name__)
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "default.yaml"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AutoTick algorithmic trading framework"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    return parser.parse_args()


def _symbols(value: str | list[str]) -> list[str]:
    return value if isinstance(value, list) else [value]


def _setup_strategy(providers, symbol: str) -> SimpleStrategy | None:
    """Create one strategy when its tick and completed daily bars are ready."""
    tick = providers.market_data.get_tick(symbol)
    if tick is None:
        return None

    strategy = SimpleStrategy()
    strategy.initialize(StrategyContext(providers.market_data, symbol, tick=tick))
    strategy.on_market_open()
    try:
        strategy.on_initial_setup()
    except RuntimeError as exc:
        logger.debug("Strategy waiting for %s data: %s", symbol, exc)
        return None
    return strategy


@log_call()
def _setup_strategies(
    providers,
    symbols: list[str],
) -> dict[str, SimpleStrategy]:
    strategies: dict[str, SimpleStrategy] = {}
    for symbol in symbols:
        strategy = _setup_strategy(providers, symbol)
        if strategy is not None:
            strategies[symbol] = strategy
    return strategies


@log_call(log_result=True)
def _place_order(
    trades: TradeManager,
    risk: RiskManager,
    signal,
    quantity: int,
    position_type: PositionType,
) -> Order:
    order = Order(
        order_id=str(uuid4()),
        symbol=signal.symbol,
        exchange=signal.exchange,
        side=OrderSide.BUY,
        quantity=quantity,
        price=signal.price,
        position_type=position_type,
    )
    return trades.create_order(risk.validate_order(order, signal.price))


def _process_symbols(
    providers,
    symbols: list[str],
    strategies: dict[str, SimpleStrategy],
    trades: TradeManager,
    risk: RiskManager,
    entered: set[str],
    quantity: int,
    position_type: PositionType,
    mode: str,
) -> None:
    for symbol in symbols:
        if symbol in entered:
            continue

        strategy = strategies.get(symbol)
        if strategy is None:
            strategy = _setup_strategy(providers, symbol)
            if strategy is None:
                continue
            strategies[symbol] = strategy

        tick = providers.market_data.get_tick(symbol)
        if tick is None:
            continue
        strategy.context.tick = tick
        signal = strategy.on_tick(tick)
        if signal is None or signal.signal_type != SignalType.BUY:
            continue

        SignalValidator.validate(signal)
        order = _place_order(trades, risk, signal, quantity, position_type)
        entered.add(symbol)
        logger.info(
            "%s order %s: %s qty=%s price=%s status=%s",
            mode.upper(),
            order.order_id,
            symbol,
            order.quantity,
            order.price,
            order.status.value,
        )


def _run_realtime(
    providers,
    config: dict,
    symbols: list[str],
    trades: TradeManager,
    risk: RiskManager,
    position_type: PositionType,
    stop_event: Event | None = None,
) -> None:
    strategies = _setup_strategies(providers, symbols)
    entered: set[str] = set()
    trading_date = providers.calendar_session.now().date()
    loop_sleep = float(config["engine"]["loop_sleep_s"])

    while stop_event is None or not stop_event.is_set():
        now = providers.calendar_session.now()
        market_open = providers.calendar_session.is_market_open(now)
        if now.date() != trading_date and market_open:
            for strategy in strategies.values():
                strategy.on_market_close()
            risk.reset_daily_state()
            entered.clear()
            strategies = _setup_strategies(providers, symbols)
            trading_date = now.date()

        if not config["session"]["only_market_hours"] or market_open:
            balance = providers.account.get_balance()
            if balance > 0:
                risk.update(balance)
                _process_symbols(
                    providers,
                    symbols,
                    strategies,
                    trades,
                    risk,
                    entered,
                    config["trade"]["quantity"],
                    position_type,
                    config["mode"],
                )

        if stop_event is None:
            sleep(loop_sleep)
        else:
            stop_event.wait(loop_sleep)


def _run_historical(
    providers,
    config: dict,
    symbols: list[str],
    trades: TradeManager,
    risk: RiskManager,
    position_type: PositionType,
) -> None:
    timestamps = providers.market_data.timestamps()
    strategies: dict[str, SimpleStrategy] = {}
    entered: set[str] = set()
    trading_date = None

    for value in timestamps:
        providers.calendar_session.wait_until(value)
        providers.calendar_session.update_time(value)
        providers.market_data.update_time(value)

        if trading_date != value.date():
            for strategy in strategies.values():
                strategy.on_market_close()
            if trading_date is not None:
                risk.reset_daily_state()
            entered.clear()
            strategies = _setup_strategies(providers, symbols)
            trading_date = value.date()

        if config["session"]["only_market_hours"]:
            if not providers.calendar_session.is_market_open(value):
                continue
        _process_symbols(
            providers,
            symbols,
            strategies,
            trades,
            risk,
            entered,
            config["trade"]["quantity"],
            position_type,
            config["mode"],
        )


def _run_providers(
    providers,
    config: dict,
    stop_event: Event | None = None,
) -> None:
    mode = config["mode"].lower()
    symbols = _symbols(config["market"]["symbols"])
    risk = RiskManager(config)
    trades = TradeManager(providers.execution, risk)
    position_type = PositionType(
        config["trade"].get("position_type", "POSITIONAL").upper()
    )

    try:
        providers.market_data.connect()
        providers.account.connect()
        providers.market_data.subscribe(symbols)
        if mode in {"backtest", "replay"}:
            _run_historical(
                providers,
                config,
                symbols,
                trades,
                risk,
                position_type,
            )
        else:
            _run_realtime(
                providers,
                config,
                symbols,
                trades,
                risk,
                position_type,
                stop_event,
            )
    finally:
        with suppress(Exception):
            providers.market_data.unsubscribe(symbols)
        with suppress(Exception):
            providers.account.disconnect()
        with suppress(Exception):
            providers.market_data.disconnect()
        logger.info("AutoTick provider shutdown complete")


def _run_ui_data(config: dict) -> None:
    """Run Paper mode with UI-backed simulated providers in one process."""
    from simulated_control_panel import run_control_panel

    symbols = _symbols(config["market"]["symbols"])
    broker = str(config["broker"]).strip().lower()
    credentials_file = (
        config.get("broker_config", {}).get(broker, {}).get("credentials_file")
    )

    def runner(providers, stop_event: Event) -> None:
        calendar = CalendarSessionManager(config["session"])
        calendar.configure_mode("paper")
        providers.calendar_session = calendar
        _run_providers(providers, config, stop_event)

    run_control_panel(
        strategy_runner=runner,
        configured_capital=float(config["capital"]),
        exchange=config["market"]["exchange"],
        initial_symbol=symbols[0],
        initial_interval="1d",
        credentials_file=credentials_file,
    )


def main() -> None:
    print("..... main start .....")
    try:
        args = _parse_args()
        config_path = args.config.expanduser().resolve()
        config = load_config(config_path)
        logging_config = config["logging"]
        configure_logging(
            level=logging_config["level"],
            log_file=logging_config["log_file"],
            file=logging_config["enabled"],
            timestamp=logging_config["timestamp"],
        )

        mode = config["mode"].lower()
        logger.info("Configuration loaded from %s", config_path)
        logger.info("Starting mode=%s", mode.upper())

        if config.get("simulated", {}).get("ui_data_enabled", False):
            logger.info("Starting Paper mode with simulated UI data")
            _run_ui_data(config)
        else:
            providers = ProviderFactory.create_bundle(mode, config)
            _run_providers(providers, config)
    except KeyboardInterrupt:
        logger.info("AutoTick stopped by user")
    except Exception:
        logger.exception("AutoTick runner failed")
        raise
    finally:
        print("..... main   end .....")


if __name__ == "__main__":
    main()
