# -*- coding: utf-8 -*-
"""
Created on Sat Nov 30 18:11:42 2024

@author: ashwe
"""

import sys

import strategy

from logger import *
from autotick import *

def read_bot_config_data(config_file):
    #TODO
    print(f"reading {config_file}")

def main():

    initialize_logger()
    lg.info("Trading Bot running ... ! \n")

    start = time.time()
    ###########################################################################
    datestamp = dt.date.today()
    ###########################
    config_file = "config/test_strategy.csv"
    read_bot_config_data(config_file)
    ###########################################################################
    # obj = autotick(datestamp, ["GODREJPROP-EQ"], strategy.run_strategy, strategy.init_strategy, strategy_config_file)
    # print("--------------------------------------------------------------------------\n")
    # print(dir(obj))
    # print("--------------------------------------------------------------------------\n")
    # print(f"\n{vars(obj)}")
    # print("--------------------------------------------------------------------------\n")
    # print(f"In main outside the class -- Broker: {obj.Broker}, {type(obj.Broker)}")
    # print(f"In main outside the class -- Exchange: {obj.Exchange}, {type(obj.Exchange)}")
    # print(f"In main outside the class -- Mode: {obj.Mode}, {type(obj.Mode)}")
    # print(f"In main outside the class -- Intraday: {obj.Intraday}, {type(obj.Intraday)}")
    # print(f"In main outside the class -- Interval: {obj.Interval}, {type(obj.Interval)}")
    # print(f"In main outside the class -- stop_loss_pct: {obj.stop_loss_pct}, {type(obj.stop_loss_pct)}")
    # print(f"In main outside the class -- target_pct: {obj.target_pct}, {type(obj.target_pct)}")
    # print(f"In main outside the class -- trailing_pct: {obj.trailing_pct}, {type(obj.trailing_pct)}")
    # print(f"In main outside the class -- trailing_trigger_pct: {obj.trailing_trigger_pct}, {type(obj.trailing_trigger_pct)}")
    # print(f"In main outside the class -- max_reentries: {obj.max_reentries}, {type(obj.max_reentries)}")
    # print(f"In main outside the class -- capital_per_trade: {obj.capital_per_trade}, {type(obj.capital_per_trade)}")
    # print(f"In main outside the class -- Trade count: {obj.Trade_count}, {type(obj.Trade_count)}")
    # print(f"In main outside the class -- Trade once: {obj.Trade_once}, {type(obj.Trade_once)}")
    # print("--------------------------------------------------------------------------\n")
    # obj.start_trade()
    # del obj
    ###########################################################################
    ###########################################################################

    end = time.time()
    diff = end - start
    lg.info("Total time taken : {} \n".format(time.strftime('%H:%M:%S', time.gmtime(diff))))

    lg.done("Trading Bot done ...")

if __name__ == "__main__":
    main()
