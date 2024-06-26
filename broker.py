# -*- coding: utf-8 -*-
"""
Created on Fri Jun 21 23:34:15 2024

@author: ashwe
"""

from SmartApi import SmartConnect
from pyotp import TOTP

import pandas as pd
import datetime as dt
import time

from config import *
from utils import *

delay = 1.2

class broker:
    def __init__(self):
        lg.info("broker constructor called")
        
        self._instance = SmartConnect(API_KEY)
        totp = TOTP(TOTP_TOKEN).now()
        time.sleep(delay)
        data = self._instance.generateSession(CLIENT_ID, PASSWORD, totp)
        self.refreshToken = data['data']['refreshToken']
        self.instrument_list = load_instrument_list()
        if data['status'] and data['message'] == 'SUCCESS':
            lg.info('Login success ... !')
    
    def __del__(self):
        lg.info("broker destructor called")
        
        time.sleep(delay)
        data = self._instance.terminateSession(CLIENT_ID)
        if data['status'] and data['message'] == 'SUCCESS':
            lg.info('Logout success ... !')
    
    def __get_hist(self, ticker, interval, fromdate, todate, exchange):
        params = {
            "exchange" : exchange,
            "symboltoken" : token_lookup(ticker, self.instrument_list, exchange),
            "interval" : interval,
            "fromdate" : fromdate,
            "todate" : todate
                    }
        hist_data = self._instance.getCandleData(params)
        return hist_data

    def __place_order(self, ticker, quantity, buy_sell, exchange):
        orderid = None

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
            orderid = self._instance.placeOrder(params)
            lg.info(orderid)
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))

        return orderid

    def __wait_till_order_fill(self, orderid):
        count = 0
        while self.get_oder_status(orderid) == 'open':
            lg.info('Buy order is in open, waiting ... %d ' % count)
            count = count + 1

###############################################################################
    def get_user_data(self):
        res = self._instance.getProfile(self.refreshToken)
        lg.debug(res)
        return res

    def get_margin(self):
        res = self._instance.rmsLimit()
        lg.debug(res)
        margin = float(res['data']['net'])
        return margin

    def get_current_price(self, ticker, exchange):
        time.sleep(delay)
        lg.debug("GETTING LTP DATA")
        data = self._instance.ltpData(exchange=exchange, tradingsymbol=ticker, symboltoken=token_lookup(ticker, self.instrument_list, exchange))
        ltp = float(data['data']['ltp'])
        lg.debug("GETTING LTP DATA: DONE")
        return ltp

    def hist_data_daily(self, ticker, duration, exchange):
        interval = "ONE_DAY"
        fromdate = (dt.date.today() - dt.timedelta(duration)).strftime('%Y-%m-%d %H:%M')
        todate = dt.date.today().strftime('%Y-%m-%d %H:%M')
        time.sleep(delay)
        hist_data = self.__get_hist(ticker, interval, fromdate, todate, exchange)
        df_data = pd.DataFrame(hist_data["data"],
                               columns=["date", "open", "high", "low", "close", "volume"])
        df_data.set_index("date", inplace=True)
        df_data.index = pd.to_datetime(df_data.index)
        df_data.index = df_data.index.tz_localize(None)
        return df_data

    def hist_data_intraday(self, ticker, exchange, datestamp=dt.date.today()):
        interval = 'FIVE_MINUTE'
        fromdate = datestamp.strftime("%Y-%m-%d")+ " 09:15"
        todate = datestamp.strftime("%Y-%m-%d") + " 15:30" 
        time.sleep(delay)
        hist_data = self.__get_hist(ticker, interval, fromdate, todate, exchange)
        df_data = pd.DataFrame(hist_data["data"],
                               columns = ["date", "open", "high", "low", "close", "volume"])
        df_data.set_index("date",inplace=True)
        df_data.index = pd.to_datetime(df_data.index)
        df_data.index = df_data.index.tz_localize(None)
        return df_data

    def place_buy_order(self, ticker, quantity, exchange):
        buy_sell = "BUY"
        orderid = self.__place_order(ticker, quantity, buy_sell, exchange)
        self.__wait_till_order_fill(orderid)
        return orderid

    def place_sell_order(self, ticker, quantity, exchange):
        buy_sell = "SELL"
        orderid = self.__place_order(ticker, quantity, buy_sell, exchange)
        self.__wait_till_order_fill(orderid)
        return orderid

    def get_oder_status(self, orderid):
        time.sleep(delay)
        order_history_response = self._instance.orderBook()
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
