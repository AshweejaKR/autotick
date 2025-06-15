# -*- coding: utf-8 -*-
"""
Created on Sat Nov 30 18:11:42 2024

@author: ashwe
"""

import sys
import threading
import csv

import strategy

from logger import *
from autotick import *

def read_master_config(config_file):
    strategies = []
    try:
        with open(config_file, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row["enabled"].strip().upper() == "TRUE":
                    strategy = {
                        "strategy_id": row["strategy_id"],
                        "strategy_file": row["strategy_file"],
                        "broker": row["broker"],
                        "mode": row["mode"].strip().upper(),  # Pass mode to strategy
                        "max_positions": int(row["max_positions"]),
                        "max_reentry": int(row["max_reentry"])
                    }
                    strategies.append(strategy)
                    gvars.brokers.append(row["broker"])

    except Exception as err:
        print(err)
    
    return strategies

def run_broker_thread(mode):

    broker_threads = {}
    # gvars.brokers.append("NOBROKER")
    gvars.brokers = list(dict.fromkeys(gvars.brokers))
    for broker in gvars.brokers:
        broker_obj = Broker(mode, broker)
        broker_threads[broker] = broker_obj

        print(broker_threads)
    
    return broker_threads


def run_strategy_thread(datestamp, strategy_id, broker, mode, run_strategy, init_strategy, strategy_config_file):

    gvars.strategy_threads = []
    # tickers = ["SUNTV-EQ", "INFY-EQ", "SBIN-EQ"]
    tickers = ["SUNTV-EQ", "INFY-EQ", "SBIN-EQ", "ITC-EQ", "ASIANPAINT-EQ"]
    # tickers = ["SBIN-EQ"]
    tickers = ["ADANIENT-EQ", "ADANIPORTS-EQ", "ASIANPAINT-EQ", "AXISBANK-EQ", "BAJAJFINSV-EQ", "BEL-EQ",
           "BHARTIARTL-EQ", "CIPLA-EQ", "COALINDIA-EQ", "DRREDDY-EQ", "ETERNAL-EQ", "GRASIM-EQ",
           "HCLTECH-EQ", "HDFCBANK-EQ", "HDFCLIFE-EQ", "HEROMOTOCO-EQ", "HINDALCO-EQ", "HINDUNILVR-EQ", 
           "ICICIBANK-EQ", "ITC-EQ", "INDUSINDBK-EQ", "INFY-EQ", "JSWSTEEL-EQ", "JIOFIN-EQ", "KOTAKBANK-EQ", 
           "LT-EQ", "M&M-EQ", "NTPC-EQ", "NESTLEIND-EQ", "ONGC-EQ", "POWERGRID-EQ", "RELIANCE-EQ", 
           "SBILIFE-EQ", "SHRIRAMFIN-EQ", "SBIN-EQ", "SUNPHARMA-EQ", "TCS-EQ", "TATACONSUM-EQ", 
           "TATAMOTORS-EQ", "TATASTEEL-EQ", "TECHM-EQ", "TITAN-EQ", "WIPRO-EQ"]

    for ticker in tickers:
        obj = autotick(datestamp, strategy_id, broker, mode, ticker, run_strategy, init_strategy, strategy_config_file)
        th_name = "Thread_" + strategy_id + "_" + ticker
        th_name = th_name.replace("-EQ", "")
        threads = threading.Thread(target=obj.start_trade, name=th_name,args=())
        # threads = threading.Thread(target=obj.start_trade, args=())
        gvars.strategy_threads.append(threads)

    #     print(gvars.strategy_threads)
        # print("--------------------------------------------------------------------------\n")
        # print(dir(obj))
        # print("--------------------------------------------------------------------------\n")
        # print(f"\n{vars(obj)}")
        # print("--------------------------------------------------------------------------\n")
        # print(f"In main outside the class -- Exchange: {obj.Exchange}, {type(obj.Exchange)}")
        # print(f"In main outside the class -- Interval: {obj.Interval}, {type(obj.Interval)}")
        # print(f"In main outside the class -- stop_loss_pct: {obj.stop_loss_pct}, {type(obj.stop_loss_pct)}")
        # print(f"In main outside the class -- target_pct: {obj.target_pct}, {type(obj.target_pct)}")
        # print(f"In main outside the class -- trailing_pct: {obj.trailing_pct}, {type(obj.trailing_pct)}")
        # print(f"In main outside the class -- trailing_trigger_pct: {obj.trailing_trigger_pct}, {type(obj.trailing_trigger_pct)}")
        # print(f"In main outside the class -- max_reentries: {obj.max_reentries}, {type(obj.max_reentries)}")
        # print(f"In main outside the class -- capital_per_trade: {obj.capital_per_trade}, {type(obj.capital_per_trade)}")
        # print("--------------------------------------------------------------------------\n")

    for thread in gvars.strategy_threads:
        thread.start()
        time.sleep(1.2)

def main():

    initialize_logger()
    lg.info("Trading Bot running ... ! \n")

    start = time.time()
    ###########################################################################
    datestamp = dt.date.today()
    ###########################
    master_config_file = "config/master_config.csv"
    strategies = read_master_config(master_config_file)
    mode = 1

    broker_threads = run_broker_thread(mode)

    try:
        for strat in strategies:
            run_strategy_thread(datestamp, strat["strategy_id"], broker_threads[strat["broker"]], strat["mode"], 
                        strategy.run_strategy, strategy.init_strategy, strat["strategy_file"])
    except Exception as err:
        template = "An exception of type {0} occurred. error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error("{}".format(message))

    ###########################################################################
    # mode = 1
    # strategy_id = "test_strategy1"
    # # broker_obj = Broker(mode, "NOBROKER")
    # broker_obj = Broker(mode, "ANGELONE")
    # strategy_config_file = "config/test_strategy.csv"
    ##########################################################################
    # obj = autotick(datestamp, strategies[0]["strategy_id"], strategies[0]["broker"], mode, "GODREJPROP-EQ", strategy.run_strategy, strategy.init_strategy, strategy_config_file)
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

    for thread in gvars.strategy_threads:
        thread.join()

    for key, value in list(broker_threads.items()):
        broker_threads[key].logout()
    ###########################################################################
    ###########################################################################

    end = time.time()
    diff = end - start
    lg.info("Total time taken : {} \n".format(time.strftime('%H:%M:%S', time.gmtime(diff))))

    lg.done("Trading Bot done ...")

if __name__ == "__main__":
    main()
