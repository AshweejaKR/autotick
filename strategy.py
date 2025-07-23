# -*- coding: utf-8 -*-
"""
Created on Sat May 17 16:48:59 2025

@author: ashwe
"""
from logger import *
from utils import *

global trigger_prices
trigger_prices = {}

def init_strategy(obj):
    """Initialize strategy by reading trigger prices from stocks.csv"""
    global trigger_prices
    lg.info(f"Initializing Strategy for Stock {obj.ticker} in {obj.Exchange} exchange ... ")
    
    # Get trigger price from stocks.csv
    trigger_price = get_highPrice_from_csv(obj.ticker)
    trigger_prices[obj.ticker] = trigger_price
    
    cur_price = obj.broker_obj.get_current_price(obj.ticker, obj.Exchange)
    lg.info(f"Trigger price for stock: {obj.ticker} : {trigger_prices[obj.ticker]} and Current price: {cur_price} ")

def run_strategy(obj):
    """
    Trading Strategy:
    - BUY if current price > trigger price
    - After BUY, reset trigger price to None
    - Return NA if trigger price is None or empty
    """
    global trigger_prices
    myPrint(f"Running Strategy for Stock {obj.ticker} in {obj.Exchange} exchange ... ")
    
    # Get current trigger price
    trigger_price = trigger_prices.get(obj.ticker)
    
    # Get current market price
    cur_price = obj.broker_obj.get_current_price(obj.ticker, obj.Exchange)
    myPrint(f"Current price for Stock {obj.ticker} = {cur_price} > Trigger price: {trigger_price} \n")

    # Return NA if trigger price is None or empty
    if not trigger_price:
        return "NA"
    
    # Check if price crosses trigger price
    if cur_price > trigger_price:
        # Reset trigger price to None
        trigger_prices[obj.ticker] = update_highPrice_in_csv(obj.ticker)
        return "BUY"
    
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
