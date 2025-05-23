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
    except Exception as err: 
        print(err)
        # ltp = float(input("Enter current price:\n"))
        ltp = 0.001
    return ltp

class stub:
    def __init__(self):
        self.cp = None
        self.error_msg = ""
        self.__login()

    def __del__(self):
        self.__logout()

    def __login(self):
        lg.done('Login success ... !')

    def __logout(self):
        lg.done('Logout success ... !')

###############################################################################

    def hist_data_daily(self, ticker, duration, exchange, datestamp):
        end_date = datetime.today()
        start_date = end_date - timedelta(days=duration)
        df_data = fetch_historical_data(ticker, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        return df_data

    def hist_data_intraday(self, ticker, exchange, datestamp):
        df_data = fetch_intraday_data(ticker, datestamp)
        return df_data

    def get_current_price(self, ticker, exchange):
        ltp = read_dummy_ltp() 
        # ltp = fetch_current_price(ticker)
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

    def verify_position(self, ticker, quantity, trade_direction, exit_=False):
        return True

    def verify_holding(self, ticker, quantity):
        return True

    def get_entry_exit_price(self, ticker, trade_direction, exit_=False):
        price = self.cp
        return price
