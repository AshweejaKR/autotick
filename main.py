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
    LIVE_TRADE = 1
    PAPER_TRADE = 2
    BACKTEST = 3
    USER_TEST = 4

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
    start = time.time()
    lg.info("T0 : {}".format(start))

    ticker = "SAGILITY-EQ"
    exchange = "NSE"
    datestamp = dt.date.today()
    mode = Mode.LIVE_TRADE
    obj = autotick(ticker, exchange, mode, datestamp)
    obj.run_trade()
    del obj

    end = time.time()
    lg.info("T1 : {}".format(end))
    diff = end - start
    lg.info("Total time taken : {} \n".format(time.strftime('%H:%M:%S', time.gmtime(diff))))

    '''
    mode = Mode.PAPER_TRADE
    # x = input(f"start {mode}:\n")
    lg.info("--------------------------------------------------------------")
    obj = autotick(ticker, exchange, mode)
    obj.run_strategy()
    del obj

    mode = Mode.BACKTEST
    from_date = "2024-12-12" # YYYY-MM-DD format
    to_date = "2024-12-14" # YYYY-MM-DD format
    dates = get_date_range(from_date, to_date)

    # x = input(f"start {mode}:\n")
    lg.info("--------------------------------------------------------------")
    for date_str in dates:
        datestamp = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
        obj = autotick(ticker, exchange, mode, datestamp)
        obj.run_strategy()
        del obj

    mode = Mode.USER_TEST
    # x = input(f"start {mode}:\n")
    lg.info("--------------------------------------------------------------")
    obj = autotick(ticker, exchange, mode)
    obj.run_strategy()
    del obj
    '''

    lg.done("Trading Bot done ...")
    
if __name__ == "__main__":
    main()
