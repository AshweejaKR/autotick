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
from autotick.utils.logger import configure_logging, get_logger

logger = get_logger(__name__)
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "default.yaml"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AutoTick algorithmic trading framework")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    return parser.parse_args()


def _symbols(value: str | list[str]) -> list[str]:
    return value if isinstance(value, list) else [value]


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


def main() -> None:
    args = _parse_args()
    config = load_config(args.config.expanduser().resolve())
    logging_config = config["logging"]
    configure_logging(
        level=logging_config["level"],
        log_file=logging_config["log_file"],
        file=logging_config["enabled"],
        timestamp=logging_config["timestamp"],
    )

    mode = config["mode"].lower()
    if mode not in {"paper", "live"}:
        raise NotImplementedError("main smoke runner currently supports paper and live modes")

    providers = ProviderFactory.create_bundle(mode, config)
    risk = RiskManager(config)
    trades = TradeManager(providers.execution, risk)
    position_type = PositionType(config["trade"].get("position_type", "POSITIONAL").upper())
    symbols = _symbols(config["market"]["symbols"])
    entered: set[str] = set()

    try:
        providers.market_data.connect()
        providers.account.connect()
        providers.market_data.subscribe(symbols)
        strategies = _setup_strategies(providers, symbols)
        trading_date = providers.calendar_session.now().date()

        logger.info("AutoTick %s mode started for %s", mode.upper(), ", ".join(symbols))

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

            if config["session"]["only_market_hours"] and not market_open:
                sleep(config["engine"]["loop_sleep_s"])
                continue

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
                order = Order(
                    order_id=str(uuid4()),
                    symbol=signal.symbol,
                    exchange=signal.exchange,
                    side=OrderSide.BUY,
                    quantity=config["trade"]["quantity"],
                    price=signal.price,
                    position_type=position_type,
                )
                order = risk.validate_order(order, signal.price)
                order = trades.create_order(order)
                entered.add(symbol)
                logger.info(
                    "%s order %s: %s qty=%s price=%s status=%s",
                    mode.upper(), order.order_id, symbol, order.quantity, order.price, order.status.value,
                )

            sleep(config["engine"]["loop_sleep_s"])
    except KeyboardInterrupt:
        logger.info("AutoTick stopped by user")
    finally:
        providers.market_data.unsubscribe(symbols)
        providers.account.disconnect()
        providers.market_data.disconnect()


if __name__ == "__main__":
    main()
