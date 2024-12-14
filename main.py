# -*- coding: utf-8 -*-
"""
Created on Sat Nov 30 18:11:42 2024

@author: ashwe
"""

import pandas as pd
import os
from enum import Enum

from logger import *
from autotick import *

class Mode(Enum):
    LIVE = 1
    PAPER = 2
    BACKTEST = 3
    TEST = 4

# def read_config_data():
#     try:
#         df1 = pd.read_excel('../trade_settings.xlsx', "SETTING")
#         df2 = pd.read_excel('../trade_settings.xlsx', "SYMBOLS")
#     except Exception as err:
#         template = "An exception of type {0} occurred. error message:{1!r}"
#         message = template.format(type(err).__name__, err.args)
#         lg.error("{}".format(message))

def main():

    initialize_logger()
    lg.info("Trading Bot running ... ! \n")

    # read_config_data()

    ticker = "INFY"
    exchange = "NSE"
    
    mode = Mode.LIVE    
    # x = input(f"start {mode}:\n")
    lg.info("--------------------------------------------------------------")
    obj = autotick(ticker, exchange, mode)
    obj.run_strategy()
    del obj

    mode = Mode.PAPER
    # x = input(f"start {mode}:\n")
    lg.info("--------------------------------------------------------------")
    obj = autotick(ticker, exchange, mode)
    obj.run_strategy()
    del obj

    mode = Mode.BACKTEST
    # x = input(f"start {mode}:\n")
    lg.info("--------------------------------------------------------------")
    obj = autotick(ticker, exchange, mode)
    obj.run_strategy()
    del obj

    mode = Mode.TEST
    # x = input(f"start {mode}:\n")
    lg.info("--------------------------------------------------------------")
    obj = autotick(ticker, exchange, mode)

    # obj.set_stoploss(5)
    # obj.set_takeprofit(10)
    obj.run_strategy()
    
    del obj
    lg.done("Trading Bot done ...")
    
if __name__ == "__main__":
    main()
