# -*- coding: utf-8 -*-
"""
Created on Tue May  6 21:01:16 2025

@author: ashwe
"""

from broker_angleone import *
from broker_aliceblue import *
from broker_stub import *

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

    def init_test(self, ticker, exchange, datestamp):
        global intraday_data
        global ltp
        if self.obj is None:
            data = fetch_intraday_data(ticker, datestamp)
        else:
            data = self.obj.hist_data_intraday(ticker, exchange, datestamp)

        intraday_data = []
        if len(data) > 0:
            for i in data['Open']:
                intraday_data.append(i)

            for i in data['High']:
                intraday_data.append(i)

            for i in data['Low']:
                intraday_data.append(i)

            for i in data['Close']:
                intraday_data.append(i)

        gvars.max_len = len(intraday_data)
        gvars.i = -1

        ltp = self.get_current_price(ticker, exchange)

        try:
            with open("../ltp.txt", "w") as file:
                for i in range(5):
                    file.write(str(ltp) + "\n")
        except Exception as err: print("***", err)

        lg.info("Init done ... !")

    def __wait_till_order_fill(self, orderid, order):
        count = 0
        lg.info('%s order is in open, waiting ... %d ' % (order, count))
        while self.obj.get_oder_status(orderid) == 'open':
            lg.info('%s order is in open, waiting ... %d ' % (order, count))
            count = count + 1

###############################################################################

    def get_available_margin(self):
        margin = self.obj.get_available_margin()
        return margin

    def get_current_price(self, ticker, exchange):
        current_price = self.obj.get_current_price(ticker, exchange)
        return current_price

    def get_entry_exit_price(self, ticker, trade_direction, _exit=False):
        price = self.obj.get_entry_exit_price(ticker, trade_direction, _exit)
        return price

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
        if orderid is not None:
            self.__wait_till_order_fill(orderid, "BUY")
            status = self.obj.get_oder_status(orderid)
            self.error_msg = self.obj.error_msg
            if status == "complete":
                return True

        return False

    def place_sell_order(self, ticker, quantity, exchange):
        orderid = self.obj.place_sell_order(ticker, quantity, exchange)
        if orderid is not None:
            self.__wait_till_order_fill(orderid, "SELL")
            status = self.obj.get_oder_status(orderid)
            self.error_msg = self.obj.error_msg
            if status == "complete":
                return True

        return False

    def verify_holding(self, ticker, quantity):
        res = self.obj.verify_holding(ticker, quantity)
        return res

    def verify_position(self, ticker, quantity, trade_direction, exit_=False):
        res = self.obj.verify_position(ticker, quantity, trade_direction, exit_)
        return res
