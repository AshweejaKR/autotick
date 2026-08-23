# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 15:48:09 2026

@author: ashwe
"""

from pathlib import Path

from autotick.config.loader import load_config
from autotick.utils.logger import configure_logging, get_logger, log_call

logger = get_logger(__name__)
CONFIG_PATH = Path("config/config.yaml")


@log_call(log_args=True, log_result=True)
def place_order(name, qty):
    logger.info("placing order for %s, quantity = %s", name, qty)
    logger.debug("debug: placing order for %s, quantity = %s", name, qty)
    logger.warning("placing order for %s, quantity = %s", name, qty)
    return True


def main():
    config = load_config(CONFIG_PATH)
    logging_config = config["logging"]

    configure_logging(
        level=logging_config["level"],
        log_file=logging_config["log_file"],
        file=logging_config["enabled"],
        timestamp=logging_config["timestamp"],
    )

    logger.info("Log initialized")
    logger.info("Configuration loaded and validated from %s", CONFIG_PATH)
    logger.info("Algo Trading BOT running ...")
    place_order("INFY-EQ", 150)


if __name__ == "__main__":
    main()
