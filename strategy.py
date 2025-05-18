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
    prev_high = hist_data['High'].iloc[-1]
    prev_low = hist_data['Low'].iloc[-1]
    lg.info(f"High : {prev_high}, Low : {prev_low}")

def run_strategy(obj):
    global prev_high
    lg.info(f"Running Strategy for Stock {obj.tickers[0]} in {obj.Exchange} exchange ... ")
    buy_p = 0.99
    cur_price = obj.broker_obj.get_current_price(obj.tickers[0], obj.Exchange)
    lg.info("current price: {} < prev high: {} \n".format(cur_price, (buy_p * prev_high)))

    if cur_price < (buy_p * prev_high):
        return "BUY"
    else:
        return "NA"
