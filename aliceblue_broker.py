# -*- coding: utf-8 -*-
"""
Created on Sun Dec  1 21:10:57 2024

@author: ashwe
"""

from logger import *

class aliceblue:
    def __init__(self, usr_="NO_USR"):
        self.usr = usr_
        self.cp = 100.00
        lg.info(f"{self.usr} aliceblue broker class constructor called")

    def __del__(self):
        lg.info(f"{self.usr} aliceblue broker class destructor called")

    def __login(self):
        lg.info(f"{self.usr} aliceblue broker class Login done ...")

    def __logout(self):
        lg.info(f"{self.usr} aliceblue broker class Logout done ...")

    def __place_order(self, ticker, quantity, buy_sell, exchange):
        orderid = "ALICE_ID1234"
        lg.info(f"{self.usr} aliceblue broker class placing order")
        lg.info("{} orderid: {} for {}".format(buy_sell, orderid, ticker))
        return orderid

    def get_user_data(self):
        lg.info(f"{self.usr} aliceblue broker getting user data")
        return ""

    def get_trade_margin(self):
        lg.info(f"{self.usr} aliceblue broker getting trade margin")
        return 10000

    def get_current_price(self, ticker, exchange):
        lg.info(f"{self.usr} aliceblue broker current price")
        self.cp = float(input("Enter current price:\n"))
        return self.cp

    def hist_data_daily(self, ticker, duration, exchange):
        lg.info(f"{self.usr} aliceblue broker hist_data_daily")
        return ""

    def hist_data_intraday(self, ticker, exchange, datestamp=dt.date.today()):
        lg.info(f"{self.usr} aliceblue broker hist_data_intraday")
        return ""

    def place_buy_order(self, ticker, quantity, exchange):
        lg.info(f"{self.usr} aliceblue broker place_buy_order")

    def place_sell_order(self, ticker, quantity, exchange):
        lg.info(f"{self.usr} aliceblue broker place_sell_order")

    def get_oder_status(self, orderid):
        lg.info(f"{self.usr} aliceblue broker class getting order status")
        return "complete"

    def verify_position(self, sym, qty, exit=False):
        lg.info(f"{self.usr} aliceblue broker verify_position")

    def verify_holding(self, sym, qty):
        lg.info(f"{self.usr} aliceblue broker verify_holding")

    def get_entry_exit_price(self, sym, _exit=False):
        lg.info(f"{self.usr} aliceblue broker get_entry_exit_price")
        if _exit:
            price = self.cp
        else:
            price = self.cp
        return price
