# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 15:48:09 2026

@author: ashwe
"""

from pathlib import Path

from autotick.config.loader import load_config
from autotick.models import Account, MarketData, Signal, SignalType
from autotick.utils.logger import configure_logging, get_logger, log_call

logger = get_logger(__name__)
CONFIG_PATH = Path("config/config.yaml")


@log_call(log_args=True, log_result=True)
def place_order(name, qty):
    logger.info("placing order for %s, quantity = %s", name, qty)
    logger.debug("debug: placing order for %s, quantity = %s", name, qty)
    logger.warning("placing order for %s, quantity = %s", name, qty)
    return True


def _first_symbol(symbols: str | list[str]) -> str:
    return symbols[0] if isinstance(symbols, list) else symbols


def main():
    config = load_config(CONFIG_PATH)
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

    market = MarketData(symbol=symbol, exchange=exchange)
    signal = Signal(
        symbol=symbol,
        exchange=exchange,
        signal_type=SignalType.HOLD,
        quantity=quantity,
    )
    account = Account(configured_capital=float(config["capital"]))

    logger.info("Log initialized")
    logger.info("Configuration loaded and validated from %s", CONFIG_PATH)
    logger.debug("Market model initialized: %s", market)
    logger.debug("Signal model initialized: %s", signal)
    logger.debug("Account model initialized: %s", account)
    logger.info("Algo Trading BOT running ...")

    place_order(symbol, quantity)


if __name__ == "__main__":
    main()
