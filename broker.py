# -*- coding: utf-8 -*-
"""
Created on Sat Nov 30 22:07:10 2024

@author: ashwe
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

from logger import *
from angleone_broker import *
from aliceblue_broker import *

import gvars
global intraday_data
global ltp
intraday_data = []

# Fetch historical data using yfinance
def fetch_historical_data(ticker, start, end):
    try:
        ticker_data = yf.Ticker(ticker)

        historical_data = ticker_data.history(start=start, end=end)
        return historical_data
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return None

# Function to fetch intraday data for a specific date
def fetch_intraday_data(ticker, date):
    try:
        ticker_data = yf.Ticker(ticker)
        # Ensure date is a string before processing
        date = date.strftime("%Y-%m-%d")

        # Fetch data for the range covering the specific date
        start_date = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        intraday_data = ticker_data.history(interval="1m", start=start_date, end=date)
        return intraday_data
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return None

# Function to fetch the current price of a stock
def fetch_current_price(ticker):
    try:
        ticker_data = yf.Ticker(ticker)
        current_price = ticker_data.info["currentPrice"]
        return current_price
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return None

def fetch_current_price_bt():
    global ltp
    try:
        ltp = float(intraday_data[gvars.i-1])
    except Exception as err:
        print(err)
    return ltp

class broker:
    def __init__(self, sym_, exchange, usr_, mode_, datestamp):
        self.mode = mode_
        self.usr = usr_
        # self._instance = None
        self._instance = angleone()
        # self._instance = aliceblue()
        self.cp = None
        self.intraday_data = None
        # lg.info(f"{self.usr} stub broker class constructor called")

        if self._instance is None:
            self.ticker = sym_ + ".NS"
        else:
            self.ticker = sym_
        self.__init_test(exchange, datestamp)

    def __del__(self):
        pass

    def __wait_till_order_fill(self, orderid, order):
        count = 0
        lg.info('%s order is in open, waiting ... %d ' % (order, count))
        while self._instance.get_oder_status(orderid) == 'open':
            lg.info('%s order is in open, waiting ... %d ' % (order, count))
            count = count + 1

###############################################################################

    def __init_test(self, exchange, datestamp):
        global intraday_data
        global ltp
        if self._instance is None:
            data = fetch_intraday_data(self.ticker, datestamp)
        else:
            data = self._instance.hist_data_intraday(self.ticker, exchange, datestamp)
        max_ = 4
        ct = 0
        intraday_data = []
        for i in data['Open']:
            intraday_data.append(i)
            ct = ct + 1
            if ct > max_:
                ct = 0
                break

        for i in data['High']:
            intraday_data.append(i)
            ct = ct + 1
            if ct > max_:
                ct = 0
                break

        for i in data['Low']:
            intraday_data.append(i)
            ct = ct + 1
            if ct > max_:
                ct = 0
                break

        for i in data['Close']:
            intraday_data.append(i)
            ct = ct + 1
            if ct > max_:
                ct = 0
                break

        gvars.max_len = len(intraday_data)
        gvars.i = -1

        if self._instance is None:
            ltp = fetch_current_price(self.ticker)
        else:
            ltp = self._instance.get_current_price(self.ticker, exchange)
        try:
            with open("../ltp.txt", "w") as file:
                for i in range(5):
                    file.write(str(ltp + i) + "\n")
        except Exception as err: print("***", err)

        lg.done("test init done ... !")

    def __place_order(self, ticker, quantity, buy_sell, exchange):
        orderid = "STUB_ID1234"
        lg.info(f"{self.usr} stub broker class placing order")
        lg.info("{} orderid: {} for {}".format(buy_sell, orderid, ticker))
        return orderid

    def __place_buy_order(self, ticker, quantity, exchange):
        lg.info(f"{self.usr} stub broker place_buy_order")

    def __place_sell_order(self, ticker, quantity, exchange):
        lg.info(f"{self.usr} stub broker place_sell_order")

    def __read_dummy_ltp(self):
        global ltp
        try:
            with open("../ltp.txt") as file:
                data = file.readlines()
                gvars.max_len = len(data)
                if gvars.i < gvars.max_len - 1:
                    ltp = float(data[gvars.i])
        except Exception as err: 
            print(err)
            # ltp = float(input("Enter current price:\n"))
        return ltp

    def __get_oder_status(self, orderid):
        lg.info(f"{self.usr} stub broker class getting order status")
        return "complete"

    def __get_trade_margin(self):
        return 5000.00

###############################################################################

    def get_user_data(self):
        usr = self._instance.get_user_data()
        return usr

    def get_trade_margin(self):
        if self.mode.value == 1 or self.mode.value == 2:
            margin = self._instance.get_trade_margin()
        else:
            margin = self.__get_trade_margin()
        return margin

    def get_current_price(self, ticker, exchange):
        if self.mode.value == 1 or self.mode.value == 2:
            cp = self._instance.get_current_price(ticker, exchange)
        elif self.mode.value == 3:
            cp = fetch_current_price_bt()
        else:
            cp = self.__read_dummy_ltp()
        self.cp = cp
        return cp

    def hist_data_daily(self, ticker, duration, exchange):
        print(self.mode)
        if self.mode.value == 1 or self.mode.value == 2:
            historical_data = self._instance.hist_data_daily(ticker, duration, exchange)
        else:
            if self._instance is None:
                end_date = datetime.today()
                start_date = end_date - timedelta(days=10 * 30)  # Approximate 10 months as 300 days
                # Get the historical data
                historical_data = fetch_historical_data(self.ticker, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            else:
                historical_data = self._instance.hist_data_daily(ticker, duration, exchange)
        if historical_data is not None:
            return historical_data
        else:
            lg.error("Failed to fetch historical data.")

    def hist_data_intraday(self, ticker, exchange, datestamp):
        if self.mode.value == 1 or self.mode.value == 2:
            intraday_data = self._instance.hist_data_intraday(ticker, exchange, datestamp)
        else:
            if self._instance is None:
                # Get the historical data
                intraday_data = fetch_intraday_data(self.ticker, datestamp)
            else:
                intraday_data = self._instance.hist_data_intraday(ticker, exchange, datestamp)
        if intraday_data is not None:
            return intraday_data
        else:
            lg.error("Failed to fetch historical data.")

    def place_buy_order(self, ticker, quantity, exchange):
        buy_sell = "BUY"
        if self.mode.value == 1:
            orderid = self._instance.place_buy_order(ticker, quantity, exchange)
            self.__wait_till_order_fill(orderid, buy_sell)
            status = self._instance.get_oder_status(orderid)
            print("Order status : ", status)
            x = input("Debug stop:\n")
            if status == 'complete':
                return True
            else:
                return False
        else:
            orderid = self.__place_buy_order(ticker, quantity, exchange)
            self.__wait_till_order_fill(orderid, buy_sell)
            status = self.__get_oder_status(orderid)
            if status == 'complete':
                return True
            else:
                return False

    def place_sell_order(self, ticker, quantity, exchange):
        buy_sell = "SELL"
        if self.mode.value == 1:
            orderid = self._instance.place_sell_order(ticker, quantity, exchange)
            self.__wait_till_order_fill(orderid, buy_sell)
            status = self._instance.get_oder_status(orderid)
            if status == 'complete':
                return True
            else:
                return False
        else:
            orderid = self.__place_sell_order(ticker, quantity, exchange)
            self.__wait_till_order_fill(orderid, buy_sell)
            status = self.__get_oder_status(orderid)
            if status == 'complete':
                return True
            else:
                return False

    def verify_position(self, sym, qty, exit=False):
        if self.mode.value == 1:
            pass
        else:
            return True

    def verify_holding(self, sym, qty):
        if self.mode.value == 1:
            pass
        else:
            return True

    def get_entry_exit_price(self, sym, _exit=False):
        if self.mode.value == 1:
            ep = self._instance.get_entry_exit_price(sym, _exit)
        else:
            ep = self.cp
        return ep
