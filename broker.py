# -*- coding: utf-8 -*-
"""
Created on Tue May  6 21:01:16 2025

@author: ashwe
"""

from broker_angleone import *
from broker_aliceblue import *
from broker_stub import *

def fetch_current_price_bt():
    global ltp
    try:
        ltp = float(intraday_data[gvars.i-1])
    except Exception as err:
        print(err)
    return ltp

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

        self.stub_obj = stub()
        mode_name = "LIVE" if (mode == 1) else ("PAPER") if (mode == 2) else ("BACKTEST") if (mode == 3) else ("USERTEST")
        lg.info(f"Trading mode value: {mode}")
        lg.info(f"Trading bot mode: {mode_name}")

    def __del__(self):
        pass

    def logout(self):
        del self.obj
        del self.stub_obj

    def init_test(self, ticker, exchange, datestamp):
        global intraday_data
        global ltp
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
        gvars.i = 0

        try:
            with open("../ltp.txt", "w") as file:
                for i in intraday_data:
                    file.write(str(i) + "\n")
        except Exception as err: print("***", err)

        lg.info("Init done ... !")

    def __wait_till_order_fill(self, orderid, order):
        count = 0
        if self.mode > 1:
            temp_obj = self.stub_obj
        else:
            temp_obj = self.obj
        lg.info('%s order is in open, waiting ... %d ' % (order, count))
        while temp_obj.get_oder_status(orderid) == 'open':
            lg.info('%s order is in open, waiting ... %d ' % (order, count))
            count = count + 1

###############################################################################

    def get_available_margin(self):
        if self.mode > 3:
            margin = self.stub_obj.get_available_margin()
        else:
            margin = self.obj.get_available_margin()
        return margin

    def get_current_price(self, ticker, exchange):
        if self.mode > 2:
            current_price = self.stub_obj.get_current_price(ticker, exchange)
        else:
            current_price = self.obj.get_current_price(ticker, exchange)
        return current_price

    def get_entry_exit_price(self, ticker, trade_direction, _exit=False):
        if self.mode > 1:
            price = self.stub_obj.get_entry_exit_price(ticker, trade_direction, _exit)
        else:
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
        if self.mode > 1:
            orderid = self.stub_obj.place_buy_order(ticker, quantity, exchange)
        else:
            orderid = self.obj.place_buy_order(ticker, quantity, exchange)
        if orderid is not None:
            self.__wait_till_order_fill(orderid, "BUY")
            if self.mode > 1:
                status = self.stub_obj.get_oder_status(orderid)
            else:
                status = self.obj.get_oder_status(orderid)
            self.error_msg = self.obj.error_msg
            if status == "complete":
                return True

        return False

    def place_sell_order(self, ticker, quantity, exchange):
        if self.mode > 1:
            orderid = self.stub_obj.place_sell_order(ticker, quantity, exchange)
        else:
            orderid = self.obj.place_sell_order(ticker, quantity, exchange)
        if orderid is not None:
            self.__wait_till_order_fill(orderid, "SELL")
            if self.mode > 1:
                status = self.stub_obj.get_oder_status(orderid)
            else:
                status = self.obj.get_oder_status(orderid)
            self.error_msg = self.obj.error_msg
            if status == "complete":
                return True

        return False

    def verify_holding(self, ticker, quantity):
        if self.mode > 1:
            res = self.stub_obj.verify_holding(ticker, quantity)
        else:
            res = self.obj.verify_holding(ticker, quantity)
        return res

    def verify_position(self, ticker, quantity, trade_direction, exit_=False):
        if self.mode > 1:
            res = self.stub_obj.verify_position(ticker, quantity, trade_direction, exit_)
        else:
            res = self.obj.verify_position(ticker, quantity, trade_direction, exit_)
        return res
