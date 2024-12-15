# -*- coding: utf-8 -*-
"""
Created on Sun Dec  1 21:10:57 2024

@author: ashwe
"""

from logger import *
from pya3 import *

from config import *

class aliceblue:
    def __init__(self, usr_="NO_USR"):
        self.usr = usr_
        self._instance = None
        self.__login()

    def __del__(self):
        self.__logout()

    def __login(self):
        try:
            self._instance = Aliceblue(user_id = CLIENT_ID, api_key = API_KEY)
            session_id = self._instance.get_session_id()
            if session_id['stat'] == 'Ok':
                if 'emsg' in session_id:
                    lg.error('Login failed ... !')
                    raise Exception("Login failed, Wrong username/password/api key")
                else:
                    lg.done('Login success ... !')
            else:
                lg.error('Login failed ... !')
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            # time.sleep(5)
            # self.__login()

    def __logout(self):
        lg.done('Logout success ... !')

    def __place_order(self, ticker, quantity, buy_sell, exchange):
        pass

    def get_user_data(self):
        pass

    def get_trade_margin(self):
        pass

    def get_current_price(self, ticker, exchange):
        pass

    def hist_data_daily(self, ticker, duration, exchange):
        pass

    def hist_data_intraday(self, ticker, exchange, datestamp=dt.date.today()):
        pass

    def place_buy_order(self, ticker, quantity, exchange):
        pass

    def place_sell_order(self, ticker, quantity, exchange):
        pass

    def get_oder_status(self, orderid):
        pass

    def verify_position(self, sym, qty, exit=False):
        pass

    def verify_holding(self, sym, qty):
        pass

    def get_entry_exit_price(self, sym, _exit=False):
        pass
