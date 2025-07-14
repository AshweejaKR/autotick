# -*- coding: utf-8 -*-
"""
Created on Sat May 17 16:48:59 2025

@author: ashwe
"""
from logger import *
from utils import *

global prev_high
global prev_low

prev_high = {}
def init_strategy(obj):
    global prev_high
    lg.info(f"Initializing Strategy for Stock {obj.ticker} in {obj.Exchange} exchange ... ")
    high_data = get_highPrice_from_csv(obj.ticker)
    prev_high[obj.ticker] = high_data
    lg.info(f"High Close : {prev_high[obj.ticker]} ")

def run_strategy(obj):
    # actual strategy
    global prev_high
    myPrint(f"Running Strategy for Stock {obj.ticker} in {obj.Exchange} exchange ... ")
    cur_price = obj.broker_obj.get_current_price(obj.ticker, obj.Exchange)
    myPrint("current price for Stock {} = {} > prev high: {} \n".format(obj.ticker, cur_price, (prev_high[obj.ticker])))
    # return "NA"

    if cur_price > (prev_high[obj.ticker]):
        prev_high[obj.ticker] = update_highPrice_in_csv(obj.ticker)
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
