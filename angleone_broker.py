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

from logger import *
from config import *
from utils import *

delay = 1.2

def load_instrument_list():
    filename = "instrument_list_file.json"
    _instrument_list = read_from_json(filename)

    if _instrument_list is None:
        instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        response = urllib.request.urlopen(instrument_url)
        _instrument_list = json.loads(response.read())

        write_to_json(_instrument_list, filename)

    return _instrument_list

def ticker_lookup(name, instrument_list, exchange):
    for instrument in instrument_list:
        if exchange == "NSE":
            if instrument["name"] == name and instrument["exch_seg"] == exchange and instrument["symbol"].split('-')[
            -1] == "EQ":
                return instrument["symbol"]
        else:
            if instrument["symbol"] == ticker and instrument["exch_seg"] == exchange:
                return instrument["token"]

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
    def __init__(self, usr_="NO_USR"):
        self.usr = usr_
        self._instance = None
        self.__login()
        self.instrument_list = load_instrument_list()
        # lg.info(f"{self.usr} angleone broker class constructor called")

    def __del__(self):
        self.__logout()
        # lg.info(f"{self.usr} angleone broker class destructor called")

    def __login(self):
        try:
            self._instance = SmartConnect(API_KEY)
            totp = TOTP(TOTP_TOKEN).now()
            time.sleep(delay)
            data = self._instance.generateSession(CLIENT_ID, PASSWORD, totp)
            self.refreshToken = data['data']['refreshToken']
            if data['status'] and data['message'] == 'SUCCESS':
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
        try:
            time.sleep(delay)
            data = self._instance.terminateSession(CLIENT_ID)
            if data['status'] and data['message'] == 'SUCCESS':
                lg.done('Logout success ... !')
            else:
                lg.error('Logout failed ... !')
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            # time.sleep(5)
            # self.__logout()

    def __get_hist(self, ticker_, interval, fromdate, todate, exchange):
        ticker = ticker_lookup(ticker_, self.instrument_list, exchange)
        params = {
            "exchange" : exchange,
            "symboltoken" : token_lookup(ticker, self.instrument_list, exchange),
            "interval" : interval,
            "fromdate" : fromdate,
            "todate" : todate
                    }
        try:
            lg.debug(str((params)))
            hist_data = self._instance.getCandleData(params)
            lg.debug(str((hist_data)))
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            # time.sleep(1)
            # hist_data = self.__get_hist(ticker, interval, fromdate, todate, exchange)
        return hist_data

    def __place_order(self, ticker_, quantity, buy_sell, exchange):
        orderid = None
        ticker = ticker_lookup(ticker_, self.instrument_list, exchange)
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

            time.sleep(delay)
            try:
                lg.debug(str((params)))
                orderid = self._instance.placeOrder(params)
            except Exception as err:
                template = "An exception of type {0} occurred. error message:{1!r}"
                message = template.format(type(err).__name__, err.args)
                lg.error("{}".format(message))
                # time.sleep(1)
                # orderid = self.__place_order(ticker, quantity, buy_sell, exchange)
            lg.info("{} orderid: {} for {}".format(buy_sell, orderid, ticker))
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))

        return orderid

    def __get_oder_status(self):
        try:
            order_history_response = self._instance.orderBook()
            lg.debug(str((order_history_response)))
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            # time.sleep(1)
            # order_history_response = self.__get_oder_status()
        return order_history_response

    def __get_margin(self):
        try:
            res = self._instance.rmsLimit()
            lg.debug(str((res)))
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            # time.sleep(1)
            # res = self.__get_margin()
        return res

    def __get_positions(self):
        try:
            time.sleep(1)
            position = self._instance.position()
            lg.debug(str((position)))
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            # time.sleep(1)
            # position = self.__get_positions()
        
        return position
    
    def __get_holdings(self):
        try:
            time.sleep(1)
            holdings = self._instance.holding()
            lg.debug(str((holdings)))
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            # time.sleep(1)
            # holdings = self.__get_holdings()
        
        return holdings

###############################################################################

    def get_user_data(self):
        res = self._instance.getProfile(self.refreshToken)
        lg.info(str((res)))
        return res

    def get_trade_margin(self):
        res = self.__get_margin()
        lg.info(res)
        margin = float(res['data']['net'])
        return margin

    def get_current_price(self, ticker_, exchange):
        ticker = ticker_lookup(ticker_, self.instrument_list, exchange)
        time.sleep(delay)
        lg.debug("GETTING LTP DATA")
        try:
            data = self._instance.ltpData(exchange=exchange, tradingsymbol=ticker, symboltoken=token_lookup(ticker, self.instrument_list, exchange))
            lg.debug(str((data)))
            ltp = float(data['data']['ltp'])
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            # time.sleep(1)
            # ltp = self.get_current_price(ticker, exchange)
        lg.debug("GETTING LTP DATA: DONE")
        return ltp

    def hist_data_daily(self, ticker, duration, exchange):
        interval = "ONE_DAY"
        fromdate = (dt.date.today() - dt.timedelta(duration)).strftime('%Y-%m-%d %H:%M')
        todate = dt.date.today().strftime('%Y-%m-%d %H:%M')
        time.sleep(delay)
        hist_data = self.__get_hist(ticker, interval, fromdate, todate, exchange)
        df_data = pd.DataFrame(hist_data["data"],
                               columns=["date", "Open", "High", "Low", "Close", "Volume"])
        df_data.set_index("date", inplace=True)
        df_data.index = pd.to_datetime(df_data.index)
        df_data.index = df_data.index.tz_localize(None)
        return df_data

    def hist_data_intraday(self, ticker, exchange, datestamp):
        interval = 'FIVE_MINUTE'
        fromdate = datestamp.strftime("%Y-%m-%d")+ " 09:15"
        todate = datestamp.strftime("%Y-%m-%d") + " 15:30" 
        time.sleep(delay)
        hist_data = self.__get_hist(ticker, interval, fromdate, todate, exchange)
        df_data = pd.DataFrame(hist_data["data"],
                               columns=["date", "Open", "High", "Low", "Close", "Volume"])
        df_data.set_index("date",inplace=True)
        df_data.index = pd.to_datetime(df_data.index)
        df_data.index = df_data.index.tz_localize(None)
        return df_data

    def place_buy_order(self, ticker, quantity, exchange):
        buy_sell = "BUY"
        orderid = self.__place_order(ticker, quantity, buy_sell, exchange)
        return orderid

    def place_sell_order(self, ticker, quantity, exchange):
        buy_sell = "SELL"
        orderid = self.__place_order(ticker, quantity, buy_sell, exchange)
        return orderid

    def get_oder_status(self, orderid):
        time.sleep(delay)
        order_history_response = self.__get_oder_status()
        status = "NA"

        try:
            for i in order_history_response['data']:
                if i['orderid'] == orderid:
                    status = i['status']  # complete/rejected/open/cancelled
                    break
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))

        return status

    def verify_position(self, sym, qty, exit=False):
        res_positions = self.__get_positions()
        try:
            for i in res_positions['data']:
                if exit:
                    if i['tradingsymbol'] == sym and int(i['sellqty']) == qty:
                        return True
                    else:
                        return False
                else:
                    if i['tradingsymbol'] == sym and int(i['buyqty']) == qty:
                        return True
                    else:
                        return False

        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            return False

    def verify_holding(self, sym, qty):
        res_holdings = self.__get_holdings()
        try:
            for i in res_holdings['data']:    
                if i['tradingsymbol'] == sym and int(i['quantity']) >= qty:
                    return True
                else:
                    return False

        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            return False

    def get_entry_exit_price(self, sym, _exit=False):
        res_positions = self.__get_positions()
        price = 0.0
        try:
            for i in res_positions['data']:
                if i['tradingsymbol'] == sym:
                    if exit:
                        price = float(i['sellavgprice'])
                    else:
                        price = float(i['buyavgprice'])

        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
        return price
