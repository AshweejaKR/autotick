# -*- coding: utf-8 -*-
"""
Created on Sat May 17 16:48:59 2025

@author: ashwe
"""
from logger import *
global prev_high
global prev_low

prev_high = {}
def init_strategy(obj):
    global prev_high
    global prev_low
    lg.info(f"Initializing Test Strategy for Stock {obj.ticker} in {obj.Exchange} exchange ... ")
    duration = 10
    hist_data = obj.broker_obj.hist_data_daily(obj.ticker, duration, obj.Exchange, obj.datestamp)
    # myPrint(hist_data)
    h1 = hist_data['Close'].iloc[-1]
    h2 = hist_data['Close'].iloc[-2]
    h3 = hist_data['Close'].iloc[-3]
    prev_high[obj.ticker] = max(h1, h2, h3)
    prev_low = hist_data['Low'].iloc[-1]
    lg.info(f"High Close : {prev_high[obj.ticker]}, Low : {prev_low}")

def run_strategy(obj):
    # actual strategy
    global prev_high
    myPrint(f"Running Test Strategy for Stock {obj.ticker} in {obj.Exchange} exchange ... ")
    buy_p = 0.975
    cur_price = obj.broker_obj.get_current_price(obj.ticker, obj.Exchange)
    myPrint("current price for Stock {} = {} < prev high: {} \n".format(obj.ticker, cur_price, (buy_p * prev_high[obj.ticker])))
    # return "NA"

    if cur_price < (buy_p * prev_high[obj.ticker]):
        prev_high[obj.ticker] = cur_price
        return "BUY"
    else:
        return "NA"

    # for testing only
    # lg.info(f"Running Strategy for Stock {obj.ticker} in {obj.Exchange} exchange ... ")
    # cur_price = obj.broker_obj.get_current_price(obj.ticker, obj.Exchange)
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
