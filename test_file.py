# -*- coding: utf-8 -*-
"""
Created on Sun Aug 11 00:16:20 2024

@author: ashwe
"""

# from broker import *
from broker_stub import *

global obj

ticker = "INFY-EQ"
exchange = "NSE"

def init1():
    global obj
    lg.info("running test1 here ...")
    obj = broker("TEST")

###################### Init fun ###############################################
def init2():
    global prev_high
    lg.info("running test2 here ...")
    stock_data = obj.hist_data_daily(ticker, 4, exchange)
    prev_high = max(stock_data.iloc[-1]['high'], stock_data.iloc[-2]['high'])
    prev_low = min(stock_data.iloc[-1]['low'], stock_data.iloc[-2]['low'])
    cur_price = obj.get_current_price(ticker, exchange)
    lg.info("High Price: {}, Low Price: {}, Current Price: {} ".format(prev_high, prev_low, cur_price))
###############################################################################

########################### run fun ###########################################
def strategy():
    global obj, prev_high
    buy_p = 0.995

    cur_price = obj.get_current_price(ticker, exchange)
    lg.info("current price: {} < prev high: {}".format(cur_price, (buy_p * prev_high)))
    if cur_price < (buy_p * prev_high):
        return "BUY"
    else:
        return "NA"

###############################################################################

def del_variables():
    global obj
    del obj
    time.sleep(1)
