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
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "config.yaml"


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
        logger.debug("Strategy initialized symbol=%s previous_close=%s", symbol, strategy.previous_close)
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
    logger.debug("Order created symbol=%s qty=%s price=%s type=%s", order.symbol, order.quantity, order.price, order.position_type.value)
    order = risk.validate_order(order, signal.price)
    logger.debug("Order risk validated symbol=%s qty=%s", order.symbol, order.quantity)
    return trades.create_order(order)


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
    if mode not in {"paper", "live"}:
        raise NotImplementedError("main smoke runner currently supports paper and live modes")

    providers = ProviderFactory.create_bundle(mode, config)
    risk = RiskManager(config)
    trades = TradeManager(providers.execution, risk)
    position_type = PositionType(config["trade"].get("position_type", "POSITIONAL").upper())
    symbols = _symbols(config["market"]["symbols"])
    quantity = config["trade"]["quantity"]
    entered: set[str] = set()

    logger.info("Configuration loaded from %s", config_path)
    logger.info("Starting mode=%s symbols=%s position_type=%s", mode.upper(), symbols, position_type.value)

    try:
        providers.market_data.connect()
        logger.debug("Market-data provider connected: %s", type(providers.market_data).__name__)
        providers.account.connect()
        logger.debug("Account provider connected: %s", type(providers.account).__name__)
        providers.market_data.subscribe(symbols)
        logger.debug("Subscribed symbols=%s", symbols)

        strategies = _setup_strategies(providers, symbols)
        now = providers.calendar_session.now()
        trading_date = now.date()
        logger.info(
            "Session status=%s current=%s market=%s-%s",
            providers.calendar_session.current_session(now),
            now.strftime("%H:%M:%S"),
            config["session"]["market_start"],
            config["session"]["market_end"],
        )
        logger.info("AutoTick %s mode started", mode.upper())

        while True:
            now = providers.calendar_session.now()
            market_open = providers.calendar_session.is_market_open(now)

            if now.date() != trading_date and market_open:
                logger.info("New trading day detected: %s -> %s", trading_date, now.date())
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
                    logger.debug("No tick available symbol=%s", symbol)
                    continue

                logger.debug("Tick symbol=%s ltp=%s volume=%s timestamp=%s", symbol, tick.ltp, tick.volume, tick.timestamp)
                strategy.context.tick = tick
                signal = strategy.on_tick(tick)
                if signal is None:
                    logger.debug("No signal symbol=%s", symbol)
                    continue

                logger.debug("Signal symbol=%s type=%s price=%s", symbol, signal.signal_type.value, signal.price)
                if signal.signal_type != SignalType.BUY:
                    continue

                SignalValidator.validate(signal)
                order = _place_order(trades, risk, signal, quantity, position_type)
                entered.add(symbol)
                logger.info(
                    "%s order %s: %s qty=%s price=%s status=%s",
                    mode.upper(), order.order_id, symbol, order.quantity, order.price, order.status.value,
                )

            sleep(config["engine"]["loop_sleep_s"])
    except KeyboardInterrupt:
        logger.info("AutoTick stopped by user")
    except Exception:
        logger.exception("AutoTick smoke runner failed")
        raise
    finally:
        logger.debug("Shutting down providers")
        providers.market_data.unsubscribe(symbols)
        providers.account.disconnect()
        providers.market_data.disconnect()
        logger.info("AutoTick shutdown complete")


if __name__ == "__main__":
    main()
