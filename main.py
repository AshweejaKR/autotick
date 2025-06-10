# -*- coding: utf-8 -*-
"""
Created on Sat Nov 30 18:11:42 2024

@author: ashwe
"""

import threading
import sys
import csv

from broker_thread import BrokerThread

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

def run_broker_thread():

    gvars.broker_threads = {}
    gvars.brokers.append("NOBROKER")
    gvars.brokers = list(dict.fromkeys(gvars.brokers))
    for broker in gvars.brokers:
        broker_obj = BrokerThread(broker)
        gvars.broker_threads[broker] = broker_obj

    for broker in gvars.brokers:
        gvars.broker_threads[broker].start()

def run_strategy_thread(datestamp, strategy_id, broker, mode, run_strategy, init_strategy, strategy_config_file):

    gvars.objs = []
    gvars.strategy_threads = []
    # tickers = ["GODREJPROP-EQ", "INFY-EQ", "SBIN-EQ"]
    tickers = ["GODREJPROP-EQ"]
    for ticker in tickers:
        obj = autotick(datestamp, strategy_id, broker, 1, ticker, run_strategy, init_strategy, strategy_config_file)
        gvars.objs.append(obj)
        threads = threading.Thread(target=obj.start_trade, args=(10,))
        gvars.strategy_threads.append(threads)
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

def main():

    initialize_logger()
    lg.info("Trading Bot running ... ! \n")

    start = time.time()
    ###########################################################################
    datestamp = dt.date.today()
    ###########################
    master_config_file = "config/master_config.csv"
    strategies = read_master_config(master_config_file)
    
    run_broker_thread()

    ###########################################################################
    try:
        for strat in strategies:
            run_strategy_thread(datestamp, strat["strategy_id"], strat["broker"], strat["mode"], 
                        strategy.run_strategy, strategy.init_strategy, strat["strategy_file"])
    except Exception as err:
        template = "An exception of type {0} occurred. error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error("{}".format(message))

    # broker_name = "ANGELONE"
    # broker_obj = Broker(0, broker_name)
    # Exchange = "NSE"
    # ticker = "NIFTYBEES-EQ"
    # datestamp = dt.date.today()
    # quantity = 1
    # duration = 30
    # trade_direction = "SELL"

    # user_data = broker_obj.get_user_data()
    # lg.info(f"{broker_name}: user data : {user_data}")
    # lg.info("---------------------------------------------------------\n")

    # user_amt = broker_obj.get_available_margin()
    # lg.info(f"{broker_name}: available margin: {user_amt}")
    # lg.info("---------------------------------------------------------\n")

    # current_price = broker_obj.get_current_price(ticker, Exchange)
    # lg.info(f"{broker_name}: {ticker} current_price: {current_price}")
    # lg.info("---------------------------------------------------------\n")

    # data1 = broker_obj.hist_data_daily(ticker, duration, Exchange, datestamp)
    # lg.info(f"{broker_name}: {ticker} historical data 1D: {data1}")
    # lg.info("---------------------------------------------------------\n")

    # data2 = broker_obj.hist_data_intraday(ticker, Exchange, datestamp)
    # lg.info(f"{broker_name}: {ticker} historical data 1m: {data2}")
    # lg.info("---------------------------------------------------------\n")

    # status = broker_obj.place_buy_order(ticker, quantity, Exchange)
    # lg.info(f"{broker_name}: buy order status for {ticker}, {quantity} qty: {status}, err: {broker_obj.error_msg}")
    # lg.info("---------------------------------------------------------\n")

    # status = broker_obj.place_sell_order(ticker, quantity, Exchange)
    # lg.info(f"{broker_name}: sell order status for {ticker}, {quantity} qty: {status}, err: {broker_obj.error_msg}")
    # lg.info("---------------------------------------------------------\n")

    # status = broker_obj.verify_position(ticker, quantity, trade_direction)
    # lg.info(f"{broker_name}: Position status for {ticker}, {quantity} qty: {status}")
    # lg.info("---------------------------------------------------------\n")

    # status = broker_obj.verify_position(ticker, quantity, trade_direction, True)
    # lg.info(f"{broker_name}: Position status for {ticker}, {quantity} qty: {status}")
    # lg.info("---------------------------------------------------------\n")

    # status = broker_obj.verify_holding(ticker, quantity)
    # lg.info(f"{broker_name}: holding status for {ticker}, {quantity} qty: {status}")
    # lg.info("---------------------------------------------------------\n")

    # entry_price = broker_obj.get_entry_exit_price(ticker, trade_direction)
    # lg.info(f"{broker_name}: {ticker} Entry Price: {entry_price}")
    # lg.info("---------------------------------------------------------\n")

    # exit_price = broker_obj.get_entry_exit_price(ticker, trade_direction, True)
    # lg.info(f"{broker_name}: {ticker} Exit Price: {exit_price}")
    # lg.info("---------------------------------------------------------\n")

    for thread in gvars.strategy_threads:
        thread.join()

    for broker in gvars.brokers:
        gvars.broker_threads[broker].stop()
        gvars.broker_threads[broker].join()
    ###########################################################################
    ###########################################################################

    end = time.time()
    diff = end - start
    lg.info("Total time taken : {} \n".format(time.strftime('%H:%M:%S', time.gmtime(diff))))

    lg.done("Trading Bot done ...")

if __name__ == "__main__":
    main()
