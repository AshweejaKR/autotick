# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 15:48:09 2026

@author: ashwe
"""

import argparse
from pathlib import Path

from autotick.config.loader import load_config
from autotick.models import Account, MarketTick, Signal, SignalType
from autotick.utils.logger import configure_logging, get_logger

logger = get_logger(__name__)
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "default.yaml"


def _first_symbol(symbols: str | list[str]) -> str:
    return symbols[0] if isinstance(symbols, list) else symbols


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AutoTick algorithmic trading framework")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to YAML configuration file (default: {DEFAULT_CONFIG_PATH})",
    )
    return parser.parse_args()


def main():
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

    symbol = _first_symbol(config["market"]["symbols"])
    exchange = config["market"]["exchange"]
    quantity = config["trade"]["quantity"]

    market_tick = MarketTick(symbol=symbol, exchange=exchange)
    signal = Signal(
        symbol=symbol,
        exchange=exchange,
        signal_type=SignalType.HOLD,
        quantity=quantity,
    )
    account = Account(configured_capital=float(config["capital"]))

    logger.info("Log initialized")
    logger.info("Configuration loaded and validated from %s", config_path)
    logger.debug("Market tick model initialized: %s", market_tick)
    logger.debug("Signal model initialized: %s", signal)
    logger.debug("Account model initialized: %s", account)
    logger.info("Algo Trading BOT running ...")


if __name__ == "__main__":
    main()
