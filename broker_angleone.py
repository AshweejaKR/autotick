# -*- coding: utf-8 -*-
"""
Created on Sun Dec  1 21:10:29 2024

@author: ashwe
"""
from SmartApi import SmartConnect
from pyotp import TOTP
import urllib

import pandas as pd
import datetime as dt
import time

import threading

from logger import *
from config import *
from utils import *

delay = 1.2
key_file = "angleone_key.txt"
API_KEY = get_keys(key_file)[0]
API_SECRET = get_keys(key_file)[1]
CLIENT_ID = get_keys(key_file)[2]
PASSWORD = get_keys(key_file)[3]
TOTP_TOKEN = get_keys(key_file)[4]

global test_lock
test_lock = threading.Lock()
last_called_time = {}
current_time = time.time()
key = f"get_hist_data"
last_called_time[key] = current_time
key = f"get_current_price"
last_called_time[key] = current_time
key = f"place_order"
last_called_time[key] = current_time
key = f"get_oder_status"
last_called_time[key] = current_time

def load_instrument_list():
    filename = "config/instrument_list_file.json"
    _instrument_list = read_from_json(filename)

    if _instrument_list is None:
        instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        response = urllib.request.urlopen(instrument_url)
        _instrument_list = json.loads(response.read())

        write_to_json(_instrument_list, filename)

    return _instrument_list

def token_lookup(ticker, instrument_list, exchange):
    for instrument in instrument_list:
        if exchange == "NSE":
            if instrument["symbol"] == ticker and instrument["exch_seg"] == exchange and instrument["symbol"].split('-')[
            -1] == "EQ":
                return instrument["token"]
        else:
            if instrument["symbol"] == ticker and instrument["exch_seg"] == exchange:
                return instrument["token"]

def symbol_lookup(token, instrument_list, exchange):
    for instrument in instrument_list:
        if exchange == "NSE":
            if instrument["token"] == token and instrument["exch_seg"] == exchange and instrument["symbol"].split('-')[
            -1] == "EQ":
                return instrument["symbol"]
        else:
            if instrument["token"] == token and instrument["exch_seg"] == exchange:
                return instrument["symbol"]

class angleone:
    def __init__(self):
        self._instance = None
        self.instrument_list = load_instrument_list()
        self.ltp = None
        self.error_msg = ""
        self.__login()

    def __del__(self):
        self.__logout()

    def __login(self):
        try:
            time.sleep(delay)
            self._instance = SmartConnect(API_KEY)
            totp = TOTP(TOTP_TOKEN).now()
            time.sleep(delay)
            data = self._instance.generateSession(CLIENT_ID, PASSWORD, totp)
            if data['status'] and data['message'] == 'SUCCESS':
                self.refreshToken = data['data']['refreshToken']
                lg.done('Login success ... !')
            else:
                lg.error('Login failed, ERROR: ', data['message'])
                sys.exit(-1)
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            sys.exit(-1)

    def __logout(self):
        try:
            time.sleep(delay)
            data = self._instance.terminateSession(CLIENT_ID)
            if data['status'] and data['message'] == 'SUCCESS':
                lg.done('Logout success ... !')
            else:
                lg.error('Logout failed, ERROR: ', data['message'])
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))

    def __get_hist_data(self, ticker, interval, fromdate, todate, exchange):
        params = {
            "exchange" : exchange,
            "symboltoken" : token_lookup(ticker, self.instrument_list, exchange),
            "interval" : interval,
            "fromdate" : fromdate,
            "todate" : todate
                    }
        key = f"get_hist_data"
        current_time = time.time()
        try:
            last_time = last_called_time.get(key, 0)
            elapsed = current_time - last_time
            minInterval = 1.5
            leftToWait = 0.0
            if minInterval > elapsed:
                leftToWait = minInterval - elapsed
                time.sleep(leftToWait)

            hist_data = self._instance.getCandleData(params)
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))

        last_called_time[key] = time.time()
        return hist_data

    def hist_data_daily(self, ticker, duration, exchange, datestamp):
        global test_lock
        with test_lock:
            interval = "ONE_DAY"
            fromdate = (datestamp - dt.timedelta(duration)).strftime('%Y-%m-%d %H:%M')
            todate = dt.date.today().strftime('%Y-%m-%d %H:%M')
            hist_data = self.__get_hist_data(ticker, interval, fromdate, todate, exchange)
            df_data = pd.DataFrame(hist_data["data"],
                                columns=["date", "Open", "High", "Low", "Close", "Volume"])
            df_data.set_index("date", inplace=True)
            df_data.index = pd.to_datetime(df_data.index)
            df_data.index = df_data.index.tz_localize(None)
            return df_data

    def hist_data_intraday(self, ticker, exchange, datestamp):
        global test_lock
        with test_lock:
            interval = 'ONE_MINUTE'
            fromdate = datestamp.strftime("%Y-%m-%d")+ " 09:15"
            todate = datestamp.strftime("%Y-%m-%d") + " 15:30" 
            hist_data = self.__get_hist_data(ticker, interval, fromdate, todate, exchange)
            df_data = pd.DataFrame(hist_data["data"],
                                columns=["date", "Open", "High", "Low", "Close", "Volume"])
            df_data.set_index("date",inplace=True)
            df_data.index = pd.to_datetime(df_data.index)
            df_data.index = df_data.index.tz_localize(None)
            return df_data

    def get_current_price(self, ticker, exchange):
        global test_lock, last_called_time

        with test_lock:
            key = f"get_current_price"
            current_time = time.time()

            # Handle rate limiting delay
            last_time = last_called_time.get(key, 0)
            elapsed = current_time - last_time
            minInterval = 1.5
            leftToWait = 0.0
            if minInterval > elapsed:
                leftToWait = minInterval - elapsed
                time.sleep(leftToWait)

            # lg.warning(f"API request for getting the current price for {ticker} in {exchange}")
            try:
                data = self._instance.ltpData(exchange=exchange, tradingsymbol=ticker, symboltoken=token_lookup(ticker, self.instrument_list, exchange))
                ltp = float(data['data']['ltp'])
                self.ltp = ltp
            except Exception as err:
                template = "An exception of type {0} occurred. error message:{1!r}"
                message = template.format(type(err).__name__, err.args)
                lg.error("{}".format(message))
                ltp = self.ltp

            last_called_time[key] = time.time()
            # lg.done(f"API request done for {ticker}")
            return ltp

    def __place_order(self, ticker, quantity, buy_sell, exchange):
        orderid = None
        key = f"place_order"
        try:
            params = {
                "variety" : "NORMAL",
                "tradingsymbol" : "{}".format(ticker),
                "symboltoken" : token_lookup(ticker, self.instrument_list, exchange),
                "transactiontype" : buy_sell,
                "exchange" : exchange,
                "ordertype" : "MARKET",
                "producttype" : "DELIVERY",
                "duration" : "DAY",
                "quantity" : quantity
            }

            # Handle rate limiting delay
            current_time = time.time()
            last_time = last_called_time.get(key, 0)
            elapsed = current_time - last_time
            minInterval = 4
            leftToWait = 0.0
            if minInterval > elapsed:
                leftToWait = minInterval - elapsed
                time.sleep(leftToWait)

            orderid = self._instance.placeOrder(params)
            lg.info("{} orderid: {} for {}".format(buy_sell, orderid, ticker))
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))

        last_called_time[key] = time.time()
        return orderid

    def place_buy_order(self, ticker, quantity, exchange):
        global test_lock
        with test_lock:
            buy_sell = "BUY"
            orderid = self.__place_order(ticker, quantity, buy_sell, exchange)
            return orderid

    def place_sell_order(self, ticker, quantity, exchange):
        global test_lock
        with test_lock:
            buy_sell = "SELL"
            orderid = self.__place_order(ticker, quantity, buy_sell, exchange)
            return orderid

    def get_oder_status(self, orderid):
        global test_lock
        key = f"get_oder_status"
        with test_lock:
            status = "NA"
            try:
                # Handle rate limiting delay
                current_time = time.time()
                last_time = last_called_time.get(key, 0)
                elapsed = current_time - last_time
                minInterval = 1
                leftToWait = 0.0
                if minInterval > elapsed:
                    leftToWait = minInterval - elapsed
                    time.sleep(leftToWait)

                order_history_response = self._instance.orderBook() #TODO there is a bug in this method
                for i in order_history_response['data']:
                    if i['orderid'] == orderid:
                        status = i['status']  # complete/rejected/open/cancelled
                        if status == "rejected" or status == "cancelled":
                            self.error_msg = status + " " + i['text']
                        break
            except Exception as err:
                template = "An exception of type {0} occurred. error message:{1!r}"
                message = template.format(type(err).__name__, err.args)
                lg.error("{}".format(message))
            
            last_called_time[key] = time.time()
            return status

    def get_user_data(self):
        global test_lock
        with test_lock:
            time.sleep(delay)
            res = self._instance.getProfile(self.refreshToken)
            return res

    def get_available_margin(self):
        global test_lock
        with test_lock:
            margin = 0.0
            try:
                time.sleep(delay)
                res = self._instance.rmsLimit()
                margin = float(res['data']['net'])
            except Exception as err:
                template = "An exception of type {0} occurred. error message:{1!r}"
                message = template.format(type(err).__name__, err.args)
                lg.error("{}".format(message))
            return margin

    def verify_position(self, ticker, quantity, trade_direction, exit_=False):
        global test_lock
        with test_lock:
            try:
                key = ""
                if trade_direction == "BUY":
                    key = "sellqty" if exit_ else "buyqty"
                if trade_direction == "SELL":
                    key = "buyqty" if exit_ else "sellqty"
                time.sleep(delay)
                res_positions = self._instance.position()
                if res_positions['data'] is not None:
                    for i in res_positions['data']:
                        if i['tradingsymbol'] == ticker and int(i[key]) >= quantity:
                            return True
                else:
                    lg.error("NO POSITIONS FOUND")

            except Exception as err:
                template = "An exception of type {0} occurred. error message:{1!r}"
                message = template.format(type(err).__name__, err.args)
                lg.error("{}".format(message))
                return False
            return False

    def verify_holding(self, ticker, quantity):
        global test_lock
        with test_lock:
            try:
                time.sleep(delay)
                res_holdings = self._instance.holding() 
                if res_holdings['data'] is not None:
                    for i in res_holdings['data']:    
                        if i['tradingsymbol'] == ticker and int(i['quantity']) >= quantity:
                            return True
                else:
                    lg.error("NO HOLDINGS FOUND")

            except Exception as err:
                template = "An exception of type {0} occurred. error message:{1!r}"
                message = template.format(type(err).__name__, err.args)
                lg.error("{}".format(message))
                return False
            return False

    def get_entry_exit_price(self, ticker, trade_direction, exit_=False):
        global test_lock
        with test_lock:
            price = None
            try:
                key = ""
                if trade_direction == "BUY":
                    key = "sellavgprice" if exit_ else "buyavgprice"
                if trade_direction == "SELL":
                    key = "buyavgprice" if exit_ else "sellavgprice"
                time.sleep(delay)
                res_positions = self._instance.position()
                if res_positions['data'] is not None:
                    for i in res_positions['data']:
                        if i['tradingsymbol'] == ticker:
                            price = float(i[key])
                else:
                    lg.error("NO POSITIONS FOUND")
                    return price

            except Exception as err:
                template = "An exception of type {0} occurred. error message:{1!r}"
                message = template.format(type(err).__name__, err.args)
                lg.error("{}".format(message))
                return price

            return price
