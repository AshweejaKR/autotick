# -*- coding: utf-8 -*-
"""
Created on Thu May 29 22:25:20 2025

@author: ashwe
"""

import threading

import strategy

from logger import *
from autotick import *

def main():

    initialize_logger()
    lg.info("Trading Bot running ... ! \n")

    start = time.time()
    ###########################################################################
    ###########################
    strategy_config_file = "config/test_strategy.csv"
    def back_test(sym, duration=250):
        # input for BACKTEST
        datestamp = dt.date.today()
        from_date = (datestamp - dt.timedelta(duration)).strftime("%Y-%m-%d") # YYYY-MM-DD format
        to_date = datestamp.strftime("%Y-%m-%d") # YYYY-MM-DD format
        dates = get_date_range(from_date, to_date)
        for date_str in dates:
            datestamp = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
            obj = autotick(datestamp, [sym], strategy.run_strategy, strategy.init_strategy, strategy_config_file)
            obj.start_trade()
            del obj
    
    ###########################################################################
    ###########################################################################
    sym_list = ["TITAN-EQ", "HUDCO-EQ", "DIVISLAB-EQ", "ASTRAL-EQ", "GODREJPROP-EQ", "TATAMOTORS-EQ", "ITC-EQ", "NESTLEIND-EQ", "TECHM-EQ", "M&M-EQ"]
    # sym_list = ["TITAN-EQ", "HUDCO-EQ"]
    # sym_list = ["TITAN-EQ"]

    for sym in sym_list:
        back_test(sym)

    ###########################################################################
    ###########################################################################
    end = time.time()
    diff = end - start
    lg.info("Total time taken : {} \n".format(time.strftime('%H:%M:%S', time.gmtime(diff))))

    lg.done("Trading Bot done ...")

if __name__ == "__main__":
    main()