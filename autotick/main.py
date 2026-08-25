# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 15:48:09 2026

@author: ashwe
"""

import argparse
from pathlib import Path
from time import sleep
from uuid import uuid4

from autotick.config.loader import load_config
from autotick.engine import RiskManager, SignalValidator, TradeManager
from autotick.models import Order, OrderSide, PositionType, SignalType
from autotick.providers.factory import ProviderFactory
from autotick.strategy.context import StrategyContext
from autotick.strategy.simple_strategy import SimpleStrategy
from autotick.utils.logger import configure_logging, get_logger, log_call

logger = get_logger(__name__)
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "default.yaml"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AutoTick algorithmic trading framework")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    return parser.parse_args()


def _symbols(value: str | list[str]) -> list[str]:
    return value if isinstance(value, list) else [value]


@log_call()
def _setup_strategies(providers, symbols: list[str]) -> dict[str, SimpleStrategy]:
    strategies = {}
    for symbol in symbols:
        tick = providers.market_data.get_tick(symbol)
        strategy = SimpleStrategy()
        strategy.initialize(StrategyContext(providers.market_data, symbol, tick=tick))
        strategy.on_market_open()
        strategy.on_initial_setup()
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
    strategies: dict[str, SimpleStrategy],
    trades: TradeManager,
    risk: RiskManager,
    entered: set[str],
    quantity: int,
    position_type: PositionType,
    mode: str,
) -> None:
    for symbol, strategy in strategies.items():
        if symbol in entered:
            continue
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
            mode.upper(), order.order_id, symbol, order.quantity, order.price, order.status.value,
        )


def _run_realtime(providers, config, symbols, trades, risk, position_type) -> None:
    strategies = _setup_strategies(providers, symbols)
    entered: set[str] = set()
    trading_date = providers.calendar_session.now().date()

    while True:
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
            _process_symbols(
                providers, strategies, trades, risk, entered,
                config["trade"]["quantity"], position_type, config["mode"],
            )
        sleep(config["engine"]["loop_sleep_s"])


def _run_historical(providers, config, symbols, trades, risk, position_type) -> None:
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

        if config["session"]["only_market_hours"] and not providers.calendar_session.is_market_open(value):
            continue
        _process_symbols(
            providers, strategies, trades, risk, entered,
            config["trade"]["quantity"], position_type, config["mode"],
        )


def main() -> None:
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
    providers = ProviderFactory.create_bundle(mode, config)
    risk = RiskManager(config)
    trades = TradeManager(providers.execution, risk)
    position_type = PositionType(config["trade"].get("position_type", "POSITIONAL").upper())
    symbols = _symbols(config["market"]["symbols"])

    logger.info("Configuration loaded from %s", config_path)
    logger.info("Starting mode=%s symbols=%s position_type=%s", mode.upper(), symbols, position_type.value)

    try:
        providers.market_data.connect()
        providers.account.connect()
        providers.market_data.subscribe(symbols)
        if mode in {"backtest", "replay"}:
            _run_historical(providers, config, symbols, trades, risk, position_type)
        else:
            _run_realtime(providers, config, symbols, trades, risk, position_type)
    except KeyboardInterrupt:
        logger.info("AutoTick stopped by user")
    except Exception:
        logger.exception("AutoTick runner failed")
        raise
    finally:
        providers.market_data.unsubscribe(symbols)
        providers.account.disconnect()
        providers.market_data.disconnect()
        logger.info("AutoTick shutdown complete")


if __name__ == "__main__":
    main()
