# -*- coding: utf-8 -*-
"""
Created on Sat Nov 30 18:11:42 2024

@author: ashwe
"""

import sys
from enum import Enum

from logger import *
from autotick import *

class Mode(Enum):
    LIVE_TRADE = 1
    PAPER_TRADE = 2
    BACKTEST = 3
    USER_TEST = 4

# TODO
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

    # TODO
    # Need to update here
    # read_config_data()
    # exec_fun(compile(code_ast, filename, "exec"), globals)

    start = time.time()
    lg.info("T0 : {}".format(start))

    ###########################################################################
    # User input here
    ticker = "INFY-EQ"
    exchange = "NSE"
    datestamp = dt.date.today()
    mode = Mode.LIVE_TRADE
    broker = Broker.ANGELONE

    # NEED TO REMOVE THIS LINE
    if len(sys.argv) > 1:
        if sys.argv[1] == '3':
            mode = Mode.BACKTEST
    ###########################

    # input for BACKTEST
    duration = 25
    from_date = (datestamp - dt.timedelta(duration)).strftime("%Y-%m-%d") # YYYY-MM-DD format
    # from_date = "2024-12-12" # YYYY-MM-DD format
    to_date = datestamp.strftime("%Y-%m-%d") # YYYY-MM-DD format
    # to_date = "2024-12-14" # YYYY-MM-DD format

    ###########################################################################

    if mode.value != 3:
        obj = autotick(ticker, exchange, mode, broker, datestamp)
        obj.run_trade()
        del obj
    else:
        dates = get_date_range(from_date, to_date)

        for date_str in dates:
            datestamp = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
            obj = autotick(ticker, exchange, mode, broker, datestamp)
            obj.run_trade()
            del obj

    ###########################################################################
    end = time.time()
    lg.info("T1 : {}".format(end))
    diff = end - start
    lg.info("Total time taken : {} \n".format(time.strftime('%H:%M:%S', time.gmtime(diff))))

    lg.done("Trading Bot done ...")
    
if __name__ == "__main__":
    main()
