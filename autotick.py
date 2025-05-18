# -*- coding: utf-8 -*-
"""
Created on Sat Nov 30 18:21:09 2024

@author: ashwe
"""

import time
import pandas as pd

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
    def __init__(self, datestamp, tickers = None, run_strategy = None, init_strategy = None, strategy_config = None):
        global no_of_order_placed
        self.__datestamp = datestamp
        self.tickers = tickers
        self.__init_strategy = init_strategy
        self.__run_strategy = run_strategy

        ###########################
        self.Exchange = "NSE"
        _broker = "NOBROKER"
        self.Interval = 1
        self.broker_obj = Broker(0, _broker)
        self.strategy_config = strategy_config
        ###########################
        self.read_config_data()
        ###########################

    def __del__(self):
        pass

    # TODO
    def read_config_data(self):
        try:
            lg.warning("Reading strategy config CSV data")
            df = pd.read_csv(self.strategy_config)
            # Create a dictionary with proper types
            typed_mapping = {
                row['NAME']: cast_value(row['VALUE'], row['TYPE'])
                for _, row in df.iterrows()
            }

            for i in typed_mapping:
                n = i.replace(" ", "_")
                setattr(self, n, typed_mapping[i])

        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))

    def start_trade(self, index=0):
        global no_of_order_placed
        if self.__init_strategy is not None:
                self.__init_strategy(self)

        self.__run_trade()

    def __run_trade(self, index=0):

        while True:
            start_time = time.time()
            try:
                if self.__run_strategy is not None:
                    self.__run_strategy(self)

                end_time = time.time()
                taken_time = end_time - start_time
                if self.Interval - taken_time > 0:
                    taken_time = self.Interval - taken_time
                else:
                    taken_time = self.Interval
                time.sleep(taken_time)

            except KeyboardInterrupt:
                lg.error("Bot stop request by user")
                break

            except Exception as err:
                template = "An exception of type {0} occurred. error message:{1!r}"
                message = template.format(type(err).__name__, err.args)
                lg.error("{}".format(message))
                break
