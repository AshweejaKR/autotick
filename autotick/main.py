# -*- coding: utf-8 -*-
"""
Created on Sun Aug 23 15:48:09 2026

@author: ashwe
"""

from autotick.utils.logger import configure_logging, get_logger, log_call

@log_call(log_args=True, log_result=True)
def place_order(name, qty):
    lg = get_logger(__name__)
    lg.info(f"placing order for {name}, quantity = {qty}")
    lg.debug(f"placing order for {name}, quantity = {qty}")
    lg.warning(f"placing order for {name}, quantity = {qty}")

def main():
    configure_logging()
    lg = get_logger(__name__)
    lg.info('Log initialized \n')
    lg.info("Algo Trading BOT running ...")
    place_order("INFY-EQ", 150)

if __name__ == "__main__":
    main()