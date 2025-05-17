# -*- coding: utf-8 -*-
"""
Created on Tue May  6 21:01:16 2025

@author: ashwe
"""

from angleone_broker import *
from aliceblue_broker import *
from stub_broker import *

class Broker:
    def __init__(self, mode, broker_name):
        self.error_msg = "NA"
        self.mode = mode
        if broker_name == "ANGELONE":
            self.obj = angleone()
        elif broker_name == "ALICEBLUE":
            self.obj = aliceblue()
        elif broker_name == "NOBROKER":
            self.obj = stub()

    def __del__(self):
        del self.obj

    def get_available_margin(self):
        margin = self.obj.get_available_margin()
        return margin

    def get_current_price(self, ticker, exchange):
        current_price = self.obj.get_current_price(ticker, exchange)
        return current_price

    def get_entry_exit_price(self, ticker, _exit=False):
        price = self.obj.get_entry_exit_price(ticker, _exit)
        return price

    def get_oder_status(self, orderid):
        status = self.obj.get_oder_status(orderid)
        return status

    def get_user_data(self):
        usr_data = self.obj.get_user_data()
        return usr_data

    def hist_data_daily(self, ticker, duration, exchange, datestamp):
        df_data = self.obj.hist_data_daily(ticker, duration, exchange, datestamp)
        return df_data

    def hist_data_intraday(self, ticker, exchange, datestamp):
        df_data = self.obj.hist_data_intraday(ticker, exchange, datestamp)
        return df_data

    def place_buy_order(self, ticker, quantity, exchange):
        orderid = self.obj.place_buy_order(ticker, quantity, exchange)
        return orderid

    def place_sell_order(self, ticker, quantity, exchange):
        orderid = self.obj.place_sell_order(ticker, quantity, exchange)
        return orderid

    def verify_holding(self, ticker, quantity):
        res = self.obj.verify_holding(ticker, quantity)
        return res

    def verify_position(self, ticker, quantity, exit_=False):
        res = self.obj.verify_position(ticker, quantity, exit_)
        return res
