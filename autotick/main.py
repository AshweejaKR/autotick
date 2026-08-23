# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 15:48:09 2026

@author: ashwe
"""

from autotick.utils.logger import configure_logging, get_logger, log_call

logger = get_logger(__name__)


@log_call(log_args=True, log_result=True)
def place_order(name, qty):
    logger.info("placing order for %s, quantity = %s", name, qty)
    logger.debug("debug: placing order for %s, quantity = %s", name, qty)
    logger.warning("placing order for %s, quantity = %s", name, qty)
    return True


def main():
    configure_logging(level="DEBUG")
    logger.info("Log initialized")
    logger.info("Algo Trading BOT running ...")
    place_order("INFY-EQ", 150)


if __name__ == "__main__":
    main()
