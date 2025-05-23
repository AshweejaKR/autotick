# -*- coding: utf-8 -*-
"""
Created on Sat Nov 30 18:11:42 2024

@author: ashwe
"""

import sys

import strategy

from logger import *
from autotick import *

def main():

    initialize_logger()
    lg.info("Trading Bot running ... ! \n")

    start = time.time()
    ###########################################################################
    datestamp = dt.date.today()
    ###########################
    strategy_config_file = "config/test_strategy.csv"
    mode = int(pd.read_csv(strategy_config_file).at[2, 'VALUE'])
    ###########################################################################
    if mode != 3:
        obj = autotick(datestamp, ["INFY-EQ"], strategy.run_strategy, strategy.init_strategy, strategy_config_file)
        # print("--------------------------------------------------------------------------\n")
        # print(dir(obj))
        # print("--------------------------------------------------------------------------\n")
        # print(f"\n{vars(obj)}")
        # print("--------------------------------------------------------------------------\n")
        # print(f"Broker: {obj.Broker}, {type(obj.Broker)}")
        # print(f"Exchange: {obj.Exchange}, {type(obj.Exchange)}")
        # print(f"Mode: {obj.Mode}, {type(obj.Mode)}")
        # print(f"Intraday: {obj.Intraday}, {type(obj.Intraday)}")
        # print(f"Interval: {obj.Interval}, {type(obj.Interval)}")
        # print(f"stop_loss_pct: {obj.stop_loss_pct}, {type(obj.stop_loss_pct)}")
        # print(f"target_pct: {obj.target_pct}, {type(obj.target_pct)}")
        # print(f"trailing_pct: {obj.trailing_pct}, {type(obj.trailing_pct)}")
        # print(f"trailing_trigger_pct: {obj.trailing_trigger_pct}, {type(obj.trailing_trigger_pct)}")
        # print(f"max_reentries: {obj.max_reentries}, {type(obj.max_reentries)}")
        # print(f"capital_per_trade: {obj.capital_per_trade}, {type(obj.capital_per_trade)}")
        # print(f"Trade count: {obj.Trade_count}, {type(obj.Trade_count)}")
        # print(f"Trade once: {obj.Trade_once}, {type(obj.Trade_once)}")
        obj.start_trade()
        del obj
    ###########################################################################
    else:
        # # input for BACKTEST
        duration = 2
        from_date = (datestamp - dt.timedelta(duration)).strftime("%Y-%m-%d") # YYYY-MM-DD format
        # from_date = "2024-12-12" # YYYY-MM-DD format
        to_date = datestamp.strftime("%Y-%m-%d") # YYYY-MM-DD format
        # to_date = "2024-12-14" # YYYY-MM-DD format
        dates = get_date_range(from_date, to_date)
        for date_str in dates:
            datestamp = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
            obj = autotick(datestamp, ["INFY-EQ"], strategy.run_strategy, strategy.init_strategy, strategy_config_file)
            obj.start_trade()
            del obj
    ###########################################################################
    ###########################################################################

    end = time.time()
    diff = end - start
    lg.info("Total time taken : {} \n".format(time.strftime('%H:%M:%S', time.gmtime(diff))))

    lg.done("Trading Bot done ...")

if __name__ == "__main__":
    main()
