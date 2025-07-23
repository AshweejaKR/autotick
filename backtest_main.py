# -*- coding: utf-8 -*-
"""
Created on Thu May 29 22:25:20 2025

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
                        "mode": "BACKTEST",  # Hardcoded for backtest
                        "max_positions": int(row["max_positions"]),
                        "max_reentry": int(row["max_reentry"])
                    }
                    strategies.append(strategy)
                    gvars.brokers.append(row["broker"])

    except Exception as err:
        template = "An exception of type {0} occurred in function read_master_config(). error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error("{}".format(message))
        log_error()
    
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

def run_strategy_thread_backtest(datestamp, strategy_id, broker, mode, run_strategy, init_strategy, strategy_config_file, sym_list):
    """
    Run backtest strategy for given symbols
    """
    gvars.strategy_threads = []
    
    for ticker in sym_list:
        obj = autotick(datestamp, strategy_id, broker, mode, ticker, run_strategy, init_strategy, strategy_config_file)
        th_name = "Thread_" + strategy_id + "_" + ticker
        th_name = th_name.replace("-EQ", "")
        threads = threading.Thread(target=obj.start_trade, name=th_name, args=())
        gvars.strategy_threads.append(threads)

    for thread in gvars.strategy_threads:
        thread.start()

def back_test(sym_list, strategies, broker_threads, duration=10):
    """
    Run backtest for given symbols over specified duration
    """
    # input for BACKTEST
    datestamp = dt.date.today()
    from_date = (datestamp - dt.timedelta(duration)).strftime("%Y-%m-%d") # YYYY-MM-DD format
    to_date = datestamp.strftime("%Y-%m-%d") # YYYY-MM-DD format
    dates = get_date_range(from_date, to_date)
    
    for date_str in dates:
        datestamp = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
        lg.info(f"Running backtest for date: {date_str}")
        
        try:
            for strat in strategies:
                # Hardcoded BACKTEST mode
                strategy_mode = "BACKTEST"
                run_strategy_thread_backtest(datestamp, strat["strategy_id"], broker_threads[strat["broker"]], strategy_mode, 
                            strategy.run_strategy, strategy.init_strategy, strat["strategy_file"], sym_list)
                            
                # Wait for all threads to complete for this date
                for thread in gvars.strategy_threads:
                    thread.join()
                    
        except Exception as err:
            template = "An exception of type {0} occurred in function back_test(). error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            log_error()

def main():

    initialize_logger()
    lg.info("Trading Bot running in BACKTEST mode ... ! \n")

    start = time.time()
    ###########################################################################
    ###########################
    master_config_file = "config/master_config.csv"
    strategies = read_master_config(master_config_file)
    
    # Hardcoded BACKTEST mode
    mode = "BACKTEST"
    lg.info(f"Mode hardcoded for backtest: {mode}")
    
    # Convert mode string to numeric value for broker
    mode_mapping = {"LIVE": 1, "PAPER": 2, "BACKTEST": 3}
    broker_mode = mode_mapping.get(mode, 3)  # Default to BACKTEST (3)

    broker_threads = run_broker_thread(broker_mode)
    
    ###########################################################################
    # Define symbol list for backtesting
    sym_list = ["TITAN-EQ", "HUDCO-EQ", "DIVISLAB-EQ", "ASTRAL-EQ", "GODREJPROP-EQ", "TATAMOTORS-EQ", "ITC-EQ", "NESTLEIND-EQ", "TECHM-EQ", "M&M-EQ"]
    # sym_list = ["TITAN-EQ", "HUDCO-EQ"]
    # sym_list = ["TITAN-EQ"]

    # Run backtest for the symbol list
    back_test(sym_list, strategies, broker_threads, duration=25)
    
    # Clean up broker threads
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