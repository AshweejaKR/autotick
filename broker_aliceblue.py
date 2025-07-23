# -*- coding: utf-8 -*-
"""
Created on Sun Dec  1 21:10:57 2024

@author: ashwe
"""

from pya3 import *

import pandas as pd
from logger import log_error, lg
from datetime import datetime, timedelta
import time

from logger import *
from config import *
from utils import *

delay = 1.2
key_file = "aliceblue_key.txt"
API_KEY = get_keys(key_file)[0]
CLIENT_ID = get_keys(key_file)[2]

class aliceblue:
    def __init__(self):
        self._instance = None
        self.instrument = None
        self.ltp = None
        self.error_msg = ""
        self.__login()

    def __del__(self):
        self.__logout()

    def __login(self):
        try:
            time.sleep(delay)
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
            template = "An exception of type {0} occurred in function __login(). error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            log_error()

    def __logout(self):
        lg.done('Logout success ... !')

    def __get_hist_data(self, ticker, interval, fromdate, todate, exchange):
        try:
            time.sleep(delay)
            instrument = self._instance.get_instrument_by_symbol(exchange, ticker)
            indices = False
            hist_data = self._instance.get_historical(instrument, fromdate, todate, interval, indices)
        except Exception as err:
            template = "An exception of type {0} occurred in function __get_hist_data(). error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            log_error()
        return hist_data

    def hist_data_daily(self, ticker, duration, exchange, datestamp):
        fromdate = datetime.now() - timedelta(days=duration)
        todate = datetime.combine(datestamp, datetime.min.time())
        interval = "D"       # ["1", "D"]
        hist_data = self.__get_hist_data(ticker, interval, fromdate, todate, exchange)
        df_data = pd.DataFrame(hist_data)
        df_data.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume', 'datetime': 'date'}, inplace=True)
        df_data.set_index("date", inplace=True)
        df_data.index = pd.to_datetime(df_data.index)
        df_data.index = df_data.index.tz_localize(None)
        return df_data

    def hist_data_intraday(self, ticker, exchange, datestamp):
        fromdate = datetime.combine(datestamp, datetime.min.time())
        todate = datetime.combine(datestamp, datetime.min.time())
        # fromdate = datestamp.strftime("%Y-%m-%d")+ " 09:15"
        # todate = datestamp.strftime("%Y-%m-%d") + " 15:30" 
        interval = "1"       # ["1", "D"]
        hist_data = self.__get_hist_data(ticker, interval, fromdate, todate, exchange)
        df_data = pd.DataFrame(hist_data)
        df_data.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume', 'datetime': 'date'}, inplace=True)
        df_data.set_index("date", inplace=True)
        df_data.index = pd.to_datetime(df_data.index)
        df_data.index = df_data.index.tz_localize(None)
        return df_data

    def get_current_price(self, ticker, exchange):
        try:
            time.sleep(delay)
            self.instrument = self._instance.get_instrument_by_symbol(exchange, ticker)
            data = self._instance.get_scrip_info(self.instrument)
            ltp = float(data['Ltp'])
            self.ltp = ltp
        except Exception as err:
            template = "An exception of type {0} occurred in function get_current_price(). error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            log_error()
            ltp = self.ltp

        return ltp


    def __place_order(self, ticker, quantity, buy_sell, exchange):
        try:
            time.sleep(delay)
            order = self._instance.place_order(transaction_type = buy_sell,
                instrument = self._instance.get_instrument_by_symbol(exchange, ticker),
                quantity = quantity,
                order_type = OrderType.Market,
                product_type = ProductType.Intraday,
                price = 0.0,
                trigger_price = None,
                stop_loss = None,
                square_off = None,
                trailing_sl = None,
                is_amo = False,
                order_tag ='order_tag')
            
            if(order['stat'] == 'Ok'):
                orderid = order['NOrdNo']
            else:
                lg.error(str(order))

            lg.info("{} orderid: {} for {}".format(buy_sell, orderid, ticker))
        except Exception as err:
            template = "An exception of type {0} occurred in function __place_order(). error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            log_error()

        return orderid

    def place_buy_order(self, ticker, quantity, exchange):
        buy_sell = TransactionType.Buy
        orderid = self.__place_order(ticker, quantity, buy_sell, exchange)
        return orderid

    def place_sell_order(self, ticker, quantity, exchange):
        buy_sell = TransactionType.Sell
        orderid = self.__place_order(ticker, quantity, buy_sell, exchange)
        return orderid

    def get_oder_status(self, orderid):
        status = "NA"
        try:
            time.sleep(delay)
            order_history_response = self._instance.get_order_history('')
            for i in order_history_response:
                if i['Nstordno'] == orderid:
                    status = i['Status']  # complete/rejected/open/cancelled
                    self.error_msg = i['RejReason']
                    break
        except Exception as err:
            template = "An exception of type {0} occurred in function get_oder_status(). error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            log_error()
        
        return status

    def get_user_data(self):
        time.sleep(delay)
        res = self._instance.get_profile()
        return res

    def get_available_margin(self):
        try:
            time.sleep(delay)
            res = self._instance.get_balance()
            margin = float(res[0]['net'])
        except Exception as err:
            template = "An exception of type {0} occurred in function get_available_margin(). error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            log_error()
        return margin

    def verify_position(self, ticker, quantity, trade_direction, exit_=False):
        try:
            #TODO Need to update for trade_direction and bug fix when data in empty
            time.sleep(delay)
            res_positions = self._instance.get_netwise_positions()
            if res_positions['stat'] != "Ok":
                return False

            if len(res_positions) > 0:
                for i in res_positions:
                    if i["stat"] == "Ok":
                        if exit_:
                            if i['Tsym'] == ticker and int(i['Sqty']) >= quantity:
                                return True
                        else:
                            if i['Tsym'] == ticker and int(i['Bqty']) >= quantity:
                                return True
            else:
                lg.error("NO POSITIONS FOUND")

        except Exception as err:
            template = "An exception of type {0} occurred in function verify_position(). error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            log_error()
            return False
        return False

    def verify_holding(self, ticker, quantity):
        try:
            time.sleep(delay)
            res_holdings = self._instance.get_holding_positions()
            if res_holdings['stat'] == "Ok":
                if len(res_holdings['HoldingVal']) > 0:
                    for i in res_holdings['HoldingVal']:
                            if i['Nsetsym'] == ticker and int(i['SellableQty']) >= quantity:
                                return True
                else:
                    lg.error("NO HOLDINGS FOUND")

        except Exception as err:
            template = "An exception of type {0} occurred in function verify_holding(). error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            log_error()
            return False
        return False

    def get_entry_exit_price(self, ticker, trade_direction, _exit=False):
        try:
            #TODO Need to update for trade_direction and bug fix when data in empty
            time.sleep(delay)
            res_positions = self._instance.get_netwise_positions()
            if res_positions['stat'] != "Ok":
                return False

            if len(res_positions) > 0:
                for i in res_positions:
                    if i["stat"] == "Ok":
                        if _exit:
                            if i['Tsym'] == ticker:
                                price = float(i['Sellavgprc'])
                        else:
                            if i['Tsym'] == ticker:
                                price = float(i['Buyavgprc'])
            else:
                lg.error("NO POSITIONS FOUND")

        except Exception as err:
            template = "An exception of type {0} occurred in function get_entry_exit_price(). error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            log_error()
            return None

        return price
