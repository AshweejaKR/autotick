# -*- coding: utf-8 -*-
"""
Created on Sat Nov 30 23:01:41 2024

@author: ashwe
"""

import json
import os
import datetime as dt
import pytz
import time

from logger import *
import gvars

def wait_till_market_open(mode_):
    while True:
        if mode_.value == 3 or mode_.value == 4:
            break

        cur_time = dt.datetime.now(pytz.timezone("Asia/Kolkata")).time()
        if cur_time > gvars.endTime or cur_time < gvars.waitTime:
            lg.info('Market is closed. \n')
            return False

        if cur_time > gvars.startTime:
            break

        lg.info("Market is NOT opened waiting ... !")
        time.sleep(gvars.sleepTime)

    lg.info("Market is Opened ...")
    return True

def is_market_open(mode_):
    if mode_.value == 3 or mode_.value == 4:
        gvars.i = gvars.i + 1
        if gvars.i > gvars.max_len - 1:
            return False
        return True

    cur_time = dt.datetime.now(pytz.timezone("Asia/Kolkata")).time()
    if gvars.startTime <= cur_time <= gvars.endTime:
        return True
    else:
        return False

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

def save_positions(ticker, quantity, order_type, entryprice, stoploss, takeprofit):
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
        "stoploss" : stoploss,
        "takeprofit" : takeprofit,
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
    
    try:
        os.remove(currentpos_path)
    except Exception as err:
        template = "An exception of type {0} occurred. error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.debug("{}".format(message))

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

# Function to extract values from a specific column
def extract_column_value(df, attrb_column_name, value_in_list=False):
    values = df.loc[df['ATTRB'] == attrb_column_name, 'VALUE'].values
    if value_in_list:
        values = values.tolist()
        return values
    else:
        return values[0] if len(values) > 0 else None
