# -*- coding: utf-8 -*-
"""
Created on Fri Jun 21 20:58:12 2024

@author: ashwe
"""
import pandas as pd
import os

from autotick import *
from test import *

global ticker, exchange, target, stoploss
global import_file, init_fun, run_fun, interval

def read_config_data():
    global ticker, exchange, target, stoploss
    global import_file, init_fun, run_fun, interval
    if os.name == 'nt':
        df = pd.read_excel('../trade_settings.xlsx', "Sheet1")
    elif os.name == 'posix':
        # df = pd.read_csv('../trade_settings.csv')
        df = pd.read_excel('../trade_settings.xlsx', "Sheet1")

    ticker = extract_column_value(df, "SYMBOL")
    exchange = extract_column_value(df, "EXCHANGE")
    target = float(extract_column_value(df, "TARGET PRICE"))
    stoploss = float(extract_column_value(df, "STOPLOSS PRICE"))

    df = pd.read_excel('../trade_settings.xlsx', "Sheet2")

    import_file = extract_column_value(df, "FILE NAME")
    init_fun = extract_column_value(df, "INIT", True)
    run_fun = extract_column_value(df, "RUN")
    interval = extract_cell_value(df, "RUN", "INTVL")

def main():
    initialize_logger()
    
    lg.info("Trading Bot running ... ! \n")
    send_to_telegram("Trading Bot running ... ! \n")

    read_config_data()

    # run_test(ticker, exchange)
    # ltp_test(ticker, exchange)
    
    obj = autotick(ticker, exchange)
    obj.set_stoploss(stoploss)
    obj.set_takeprofit(target)

    obj.set_config_data(import_file, init_fun, run_fun, interval)
    obj.run()

    lg.info("Trading Bot done ...")
    send_to_telegram("Trading Bot done ...")

if __name__ == '__main__':
    main()
