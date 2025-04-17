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
            return False

        if cur_time > gvars.startTime:
            break

        lg.info("Market is NOT opened waiting ... !")
        time.sleep(gvars.sleepTime)

    lg.info("Market is Opened ...")
    return True

def is_market_open(mode_):
    gvars.i = gvars.i + 1
    if mode_.value == 3 or mode_.value == 4:
        if gvars.i > gvars.max_len - 1:
            return False
        return True

    cur_time = dt.datetime.now(pytz.timezone("Asia/Kolkata")).time()
    if gvars.startTime <= cur_time <= gvars.endTime:
        return True
    else:
        lg.info('Market is closed. \n')
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

def save_trade_count(ticker, trade_count):
    pos_path = './data/'
    try:
        os.mkdir(pos_path)
    except Exception as err:
        pass
    trade_count_filename = ticker.upper().split("-")[0] + "_COUNT.TXT"
    currentpos_path = pos_path + trade_count_filename

    try:
        with open(currentpos_path, "w") as f:
            f.write(str(trade_count))
            f.flush()
    except Exception as err:
        template = "An exception of type {0} occurred. error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error("{}".format(message))
    
def load_trade_count(ticker):
    trade_count_filename = ticker.upper().split("-")[0] + "_COUNT.TXT"
    trade_count = 0
    try:
        pos_path = './data/'
        currentpos_path = pos_path + trade_count_filename
        count = open(currentpos_path, "r").read()
        trade_count = int(count)
    except Exception as err:
        template = "An exception of type {0} occurred. error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.debug("{}".format(message))
    
    return trade_count

def save_positions(filename, trade_count, ticker, quantity, order_type, entryprice, stoploss, takeprofit):
    pos_path = './data/'
    try:
        os.mkdir(pos_path)
    except Exception as err:
        pass
    pos_file_name = filename + "_trade_data_" + str(trade_count) + ".json"
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

def load_positions(filename, trade_count):
    pos_path = './data/'
    pos_file_name = filename + "_trade_data_" + str(trade_count) + ".json"
    currentpos_path = pos_path + pos_file_name
    data = None
    
    if os.path.exists(currentpos_path):
        data = read_from_json(currentpos_path)

    return data

def remove_positions(filename, trade_count):
    pos_path = './data/'
    pos_file_name = filename + "_trade_data_" + str(trade_count) + ".json"
    currentpos_path = pos_path + pos_file_name
    
    try:
        os.remove(currentpos_path)
    except Exception as err:
        template = "An exception of type {0} occurred. error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.debug("{}".format(message))

def save_trade_in_csv(filename_, ticker, quantity, order_type, price, datetime):
    # datetime =  dt.datetime.now().strftime('%Y-%m-%d %H:%M')
    filename = filename_ + "_trade_report.csv"
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
        template = "An exception of type {0} occurred. error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error("{}".format(message))
        data = "datetime,ticker,quantity,order_type,price\n"
    
    data = data + str(datetime) + "," + str(ticker) + "," + str(quantity) + "," + str(order_type) + "," + str(price) + "\n"
    try:
        with open(currentpos_path, "w") as f:
            f.write(data)
            f.flush()
    except Exception as err:
        template = "An exception of type {0} occurred. error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error("{}".format(message))

# Function to extract values from a specific column
def extract_column_value(df, attrb_column_name, value_in_list=False):
    values = df.loc[df['ATTRB'] == attrb_column_name, 'VALUE'].values
    if value_in_list:
        values = values.tolist()
        return values
    else:
        return values[0] if len(values) > 0 else None

def get_date_range(from_date, to_date):
    dates = []
    start_date = dt.datetime.strptime(from_date, "%Y-%m-%d")
    end_date = dt.datetime.strptime(to_date, "%Y-%m-%d")
    
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date.strftime("%Y-%m-%d"))
        current_date += dt.timedelta(days=1)
    
    return dates

def get_re_entry(ticker):
    filename = ticker + "_re_entry.txt"
    pos_path = './data/'
    currentpos_path = pos_path + filename
    re_entry = 1
    try:
        os.mkdir(pos_path)
    except Exception as err:
        pass

    try:
        with open(currentpos_path) as f:
            data = f.read()
            re_entry = int(data)
    except FileNotFoundError:
        with open(currentpos_path, "w") as f:
            f.write(str(re_entry))
    except Exception as err:
        template = "An exception of type {0} occurred. error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.debug("{}".format(message))
        data = "datetime,ticker,quantity,order_type,price\n"
    
    return re_entry
