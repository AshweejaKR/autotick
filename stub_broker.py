# -*- coding: utf-8 -*-
"""
Created on Sat Nov 30 22:07:10 2024

@author: ashwe
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import datetime as dt

from logger import *
from config import *
from utils import *

import gvars
global intraday_data
global ltp
intraday_data = []

# Fetch historical data using yfinance
def fetch_historical_data(ticker_, start, end):
    ticker = ticker_.replace("-EQ", ".NS")
    try:
        ticker_data = yf.Ticker(ticker)

        historical_data = ticker_data.history(start=start, end=end)
        return historical_data
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return None

# Function to fetch intraday data for a specific date
def fetch_intraday_data(ticker_, date):
    ticker = ticker_.replace("-EQ", ".NS")
    try:
        ticker_data = yf.Ticker(ticker)
        # Ensure date is a string before processing
        date = date.strftime("%Y-%m-%d")

        # Fetch data for the range covering the specific date
        start_date = (datetime.strptime(date, "%Y-%m-%d")).strftime("%Y-%m-%d")
        end_date = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        intraday_data = ticker_data.history(interval="1m", start=start_date, end=end_date)
        return intraday_data
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return None

# Function to fetch the current price of a stock
def fetch_current_price(ticker_):
    ticker = ticker_.replace("-EQ", ".NS")
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

def read_dummy_ltp():
    global ltp
    try:
        with open("../ltp.txt") as file:
            data = file.readlines()
            ltp = float(data[0])
            # gvars.max_len = len(data)
            # if gvars.i < gvars.max_len - 1:
            #     ltp = float(data[gvars.i])
    except Exception as err: 
        print(err)
        # ltp = float(input("Enter current price:\n"))
    return ltp

class stub:
    def __init__(self):
        self._instance = None
        self.cp = None
        self.__login()

    def __del__(self):
        self.__logout()

    def __login(self):
        print('Login success ... !')

    def __logout(self):
        print('Logout success ... !')

###############################################################################

    def init_test(self, ticker, exchange, datestamp):
        global intraday_data
        global ltp
        if self._instance is None:
            data = fetch_intraday_data(ticker, datestamp)

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

        if self._instance is None:
            ltp = fetch_current_price(ticker)

        try:
            with open("../ltp.txt", "w") as file:
                for i in range(5):
                    file.write(str(ltp + i) + "\n")
        except Exception as err: print("***", err)

        lg.info("Init done ... !")
        # lg.info(f"Trading Bot Mode: {self.mode.name}")

    def hist_data_daily(self, ticker, duration, exchange, datestamp):
        end_date = datetime.today()
        start_date = end_date - timedelta(days=duration)
        df_data = fetch_historical_data(ticker, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        return df_data

    def hist_data_intraday(self, ticker, exchange, datestamp):
        df_data = fetch_intraday_data(ticker, datestamp)
        return df_data

    def get_current_price(self, ticker, exchange):
        if len(intraday_data) > 0:
            ltp = fetch_current_price_bt()
        else:
            ltp = fetch_current_price(ticker)
        # ltp = read_dummy_ltp()
        # ltp = fetch_current_price(ticker)
        # ltp = float(input("Enter new Price:\n"))
        self.cp = ltp
        return ltp

    def __place_order(self, ticker, quantity, buy_sell, exchange):
        orderid = "TEST1_" + buy_sell
        print("{} orderid: {} for {}".format(buy_sell, orderid, ticker))
        return orderid

    def place_buy_order(self, ticker, quantity, exchange):
        buy_sell = "B"
        orderid = self.__place_order(ticker, quantity, buy_sell, exchange)
        return orderid

    def place_sell_order(self, ticker, quantity, exchange):
        buy_sell = "S"
        orderid = self.__place_order(ticker, quantity, buy_sell, exchange)
        return orderid

    def get_oder_status(self, orderid):
        status = 'complete'  # complete/rejected/open/cancelled 
        return status

    def get_user_data(self):
        res = "NA"
        return res

    def get_available_margin(self):
        margin = 5000.00
        return margin

    def verify_position(self, ticker, quantity, exit_=False):
        return True

    def verify_holding(self, ticker, quantity):
        return True

    def get_entry_exit_price(self, ticker, _exit=False):
        price = self.cp
        return price
