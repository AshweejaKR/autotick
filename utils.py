# -*- coding: utf-8 -*-
"""
Created on Fri Jun 21 21:05:13 2024

@author: ashwe
"""

import json
import urllib
import os
import datetime as dt
import pytz
import time

from logger import *

waitTime = dt.time(8, 59)
startTime = dt.time(9, 15)
endTime = dt.time(15, 15)
sleepTime = 5

def save_trade_in_csv(ticker, quantity, order_type, price):
    datetime =  dt.datetime.now().strftime('%Y-%m-%d %H:%M')
    filename = ticker + "_trade_report.csv"
    pos_path = './data/'
    currentpos_path = pos_path + filename
    try:
        os.mkdir(pos_path)
    except Exception as err:
        pass

    try:
        with open(currentpos_path) as f:
            data = f.read()
    except Exception as err:
        print(err)
        data = "datetime,ticker,quantity,order_type,price\n"
    
    data = data + str(datetime) + "," + str(ticker) + "," + str(quantity) + "," + str(order_type) + "," + str(price) + "\n"
    try:
        with open(currentpos_path, "w") as f:
            f.write(data)
            f.flush()
    except Exception as err:
        print(err)

# Function to write data to a JSON file
def write_to_json(data, filename):
    try:
        with open(filename, 'w') as json_file:
            json.dump(data, json_file, indent=4)
    except Exception as err:
        template = "An exception of type {0} occurred. error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error("{}".format(message))

# Function to read data from a JSON file
def read_from_json(filename):
    data = None
    try:
        with open(filename, 'r') as json_file:
            data = json.load(json_file)
    except Exception as err:
        template = "An exception of type {0} occurred. error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error("{}".format(message))
    return data

# Function to extract values from a specific column
def extract_column_value(df, attrb_column_name):
    value = df.loc[df['ATTRB'] == attrb_column_name, 'VALUE'].values
    return value[0] if len(value) > 0 else None

def load_instrument_list():
    filename = "instrument_list_file.json"
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

def save_positions(ticker, quantity, order_type, entryprice):
    pos_path = './data/'
    try:
        os.mkdir(pos_path)
    except Exception as err:
        pass
    pos_file_name = ticker + "_trade_data.json"
    currentpos_path = pos_path + pos_file_name

    data = {
        "ticker" : ticker,
        "quantity" : quantity,
        "order_type" : order_type,
        "entryprice" : entryprice,
    }

    write_to_json(data, currentpos_path)

def load_positions(ticker):
    pos_path = './data/'
    pos_file_name = ticker + "_trade_data.json"
    currentpos_path = pos_path + pos_file_name
    data = None
    
    if os.path.exists(currentpos_path):
        data = read_from_json(currentpos_path)

    return data

def remove_positions(ticker):
    pos_path = './data/'
    pos_file_name = ticker + "_trade_data.json"
    currentpos_path = pos_path + pos_file_name
    os.remove(currentpos_path)
    
def wait_till_market_open():
    while True:
        cur_time = dt.datetime.now(pytz.timezone("Asia/Kolkata")).time()
        if cur_time > endTime or cur_time < waitTime:
            lg.info('Market is closed. \n')
            return

        if cur_time > startTime:
            break

        lg.info("Market is NOT opened waiting ... !")
        time.sleep(sleepTime)

    lg.info("Market is Opened ...")


def is_market_open(mode='None'):
    cur_time = dt.datetime.now(pytz.timezone("Asia/Kolkata")).time()
    if startTime <= cur_time <= endTime:
        return True
    else:
        return False
