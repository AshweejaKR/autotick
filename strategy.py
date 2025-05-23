# -*- coding: utf-8 -*-
"""
Created on Sat May 17 16:48:59 2025

@author: ashwe
"""
from logger import *
global prev_high
global prev_low

def init_strategy(obj):
    global prev_high
    global prev_low
    lg.info(f"Initializing Strategy for Stock {obj.tickers[0]} in {obj.Exchange} exchange ... ")
    duration = 4
    hist_data = obj.broker_obj.hist_data_daily(obj.tickers[0], duration, obj.Exchange, obj.datestamp)
    lg.info(str(hist_data))
    lg.info("\n")
    prev_high = hist_data['Close'].iloc[-1]
    prev_low = hist_data['Low'].iloc[-1]
    lg.info(f"High : {prev_high}, Low : {prev_low}")

def run_strategy(obj):
    # actual strategy
    global prev_high
    lg.info(f"Running Strategy for Stock {obj.tickers[0]} in {obj.Exchange} exchange ... ")
    buy_p = 0.985
    cur_price = obj.broker_obj.get_current_price(obj.tickers[0], obj.Exchange)
    lg.info("current price: {} < prev high: {} \n".format(cur_price, (buy_p * prev_high)))

    if cur_price < (buy_p * prev_high):
        prev_high = cur_price
        return "BUY"
    else:
        return "NA"

    # for testing only
    # lg.info(f"Running Strategy for Stock {obj.tickers[0]} in {obj.Exchange} exchange ... ")
    # cur_price = obj.broker_obj.get_current_price(obj.tickers[0], obj.Exchange)
    # lg.info("current price: {} \n".format(cur_price))
    # filename = "C:\\user\\ashwee\\stub_test.txt"
    # signal = None
    # try:
    #     with open(filename) as file:
    #         data = file.readlines()
    #         x = int(data[0])
    #         if x == 1:
    #             signal = "BUY"
    #         if x == 2:
    #             signal = "SELL"
    # except Exception as err: 
    #     print(err)
    # return signal
