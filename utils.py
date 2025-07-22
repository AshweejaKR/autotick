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
import csv

from logger import *
import gvars

def wait_till_market_open(mode_):
    while True:
        if mode_ == 3 or mode_ == 4 or mode_ == 5:
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
    if mode_ == 3 or mode_ == 4:
        if gvars.i > gvars.max_len - 1:
            return False
        return True

    if mode_ == 5:
        return True

    cur_time = dt.datetime.now(pytz.timezone("Asia/Kolkata")).time()
    if gvars.startTime <= cur_time <= gvars.endTime:
        return True
    else:
        lg.warning('Market is closed. \n')
        return False

# Function to write data to a JSON file
def write_to_json(data, filename):
    try:
        with open(filename, 'w') as json_file:
            json.dump(data, json_file, indent=4)
    except Exception as err:
        lg.error(f"Error writing to JSON file {filename}: {err}")
        log_error()

# Function to read data from a JSON file
def read_from_json(filename):
    data = None
    try:
        with open(filename, 'r') as json_file:
            data = json.load(json_file)
    except Exception as err:
        lg.error(f"Error reading from JSON file {filename}: {err}")
        log_error()
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
        lg.error(f"Error removing file {currentpos_path}: {err}")
        log_error()

def save_trade_in_csv(filename_, datetime, ticker, quantity, order_type, price, comment):
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
    except FileNotFoundError as err:
        data = "datetime,ticker,quantity,order_type,price,comment\n"
    except Exception as err:
        template = "An exception of type {0} occurred. error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error("{}".format(message))
        data = "datetime,ticker,quantity,order_type,price,comment\n"
    
    data = data + str(datetime) + "," + str(ticker) + "," + str(quantity) + "," + str(order_type) + "," + str(price) + "," + str(comment)+ "\n"
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

# Function to cast string values to correct type
def cast_value(value, dtype):
    try:
        if dtype == 'str':
            return str(value)
        elif dtype == 'float':
            return float(value)
        elif dtype == 'int':
            return int(value)
        elif dtype == 'bool':
            return str(value).strip().lower() in ['yes', 'true', '1']
        else:
            return value
    except:
        return value  # Return as-is if casting fails

def get_stock_list():
    CSV_FILE = 'stocks.csv'
    config_path = './config/'
    currentstocklist_path = config_path + CSV_FILE
    stock_list = []
    try:
        with open(currentstocklist_path, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                stock_list.append(row['stock_name'])
        return stock_list
    except Exception as err:
        template = "An exception of type {0} occurred. error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error("{}".format(message))

def get_highPrice_from_csv(stock_name):
    CSV_FILE = 'stocks.csv'
    config_path = './config/'
    currentstocklist_path = config_path + CSV_FILE
    try:
        with open(currentstocklist_path, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['stock_name'].strip().upper() == stock_name.strip().upper():
                # Parse the date and check age
                    date_added = dt.datetime.strptime(row['date_added'], "%d-%m-%Y")
                    days_diff = (dt.datetime.today() - date_added).days
                    print(f"days_diff for stock {stock_name}: {days_diff}")
                    if days_diff > 10:
                        return None
                    print(f"high price for stock {stock_name}: {row['high_price']}")
                    return float(row['high_price']) if row['high_price'] else None
    except Exception as err:
        template = "An exception of type {0} occurred. error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error("{}".format(message))
        return None  # if stock not found

def update_highPrice_in_csv(stock_name, price=None):
    today_str = dt.datetime.today().strftime("%d-%m-%Y")
    updated = False
    updated_rows = []

    CSV_FILE = 'stocks.csv'
    config_path = './config/'
    currentstocklist_path = config_path + CSV_FILE
    try:
        with open(currentstocklist_path, mode='r') as file:
            reader = csv.DictReader(file)
            updated_rows = list(reader)
    except FileNotFoundError:
        print("CSV file not found.")
        return

    for row in updated_rows:
        if row['stock_name'].strip().upper() == stock_name.strip().upper():
            row['high_price'] = "" if price is None else str(price)
            row['date_added'] = today_str
            updated = True
            break

    if not updated:
        print(f"Stock '{stock_name}' not found in CSV.")
        return

    with open(CSV_FILE, mode='w', newline='') as file:
        fieldnames = ['stock_name', 'high_price', 'date_added']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)

    print(f"High price for '{stock_name}' updated to: {price if price is not None else 'None'}")
