# -*- coding: utf-8 -*-
"""
Created on Sat Nov 30 18:21:09 2024

@author: ashwe
"""

import time

from broker import *
from utils import *

import gvars

global no_of_order_placed
no_of_order_placed = 0

def KillSwitch():
    global no_of_order_placed
    if no_of_order_placed > 5:
        lg.error("Kill Switch Activated!!")
        lg.error("Stopping the Trading Bot")
        sys.exit(-1)

class autotick:
    def __init__(self, datestamp, tickers=None, strategy_config=None):
        global no_of_order_placed
        self.datestamp = datestamp
        self.ticker = ["NIFTYBEES-EQ"]
        self.init_strategy = None
        self.run_strategy = None

        ###########################
        self.exchange = "NSE"
        _broker = "NOBROKER"
        self.interval = 2
        self.broker_obj = Broker(0, _broker)

    def __del__(self):
        pass

    def run_trade(self):
        global no_of_order_placed
        if self.init_strategy is not None:
                self.init_strategy(self)
        lg.info(f"Running Trade for Stock {self.ticker} in {self.exchange} exchange ... ")

        while True:
            start_time = time.time()
            try:
                if self.run_strategy is not None:
                    self.run_strategy(self)

                end_time = time.time()
                taken_time = end_time - start_time
                if self.interval - taken_time > 0:
                    taken_time = self.interval - taken_time
                else:
                    taken_time = self.interval
                time.sleep(taken_time)

            except KeyboardInterrupt:
                lg.error("Bot stop request by user")
                break

            except Exception as err:
                template = "An exception of type {0} occurred. error message:{1!r}"
                message = template.format(type(err).__name__, err.args)
                lg.error("{}".format(message))
                break


        # for i in range(0, 11):
        #     if self.run_strategy is not None:
        #         self.run_strategy(self)

###############################################################################
    def set_stoploss(self, sl_p):
        if sl_p < 1:
            self.stoploss_p = sl_p
        else:
            self.stoploss_p = sl_p / 100.00

    def set_takeprofit(self, tp_p):
        if tp_p < 1:
            self.target_p = tp_p
        else:
            self.target_p = tp_p / 100.00

###############################################################################
