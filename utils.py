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

def is_market_open(mode_, ticker):
    # Increment ticker-specific index
    current_index = gvars.ticker_index.get(ticker, 0)
    gvars.ticker_index[ticker] = current_index + 1
    
    if mode_ == 3 or mode_ == 4:
        max_len = gvars.ticker_max_len.get(ticker, 0)
        if gvars.ticker_index[ticker] > max_len - 1:
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
        template = "An exception of type {0} occurred in function write_to_json(). error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error("{}".format(message))
        log_error()

# Function to read data from a JSON file
def read_from_json(filename):
    data = None
    try:
        with open(filename, 'r') as json_file:
            data = json.load(json_file)
    except Exception as err:
        template = "An exception of type {0} occurred in function read_from_json(). error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error("{}".format(message))
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
        template = "An exception of type {0} occurred in function save_trade_count(). error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error("{}".format(message))
        log_error()
    
def load_trade_count(ticker):
    trade_count_filename = ticker.upper().split("-")[0] + "_COUNT.TXT"
    trade_count = 0
    try:
        pos_path = './data/'
        currentpos_path = pos_path + trade_count_filename
        count = open(currentpos_path, "r").read()
        trade_count = int(count)
    except Exception as err:
        template = "An exception of type {0} occurred in function load_trade_count(). error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.debug("{}".format(message))
        log_error()
    
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
        template = "An exception of type {0} occurred in function remove_positions(). error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error("{}".format(message))
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
        template = "An exception of type {0} occurred in function save_trade_in_csv(). error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error("{}".format(message))
        log_error()
        data = "datetime,ticker,quantity,order_type,price,comment\n"
    
    data = data + str(datetime) + "," + str(ticker) + "," + str(quantity) + "," + str(order_type) + "," + str(price) + "," + str(comment)+ "\n"
    try:
        with open(currentpos_path, "w") as f:
            f.write(data)
            f.flush()
    except Exception as err:
        template = "An exception of type {0} occurred in function save_trade_in_csv(). error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error("{}".format(message))
        log_error()

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
        template = "An exception of type {0} occurred in function get_re_entry(). error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.debug("{}".format(message))
        log_error()
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
    except Exception as err:
        template = "An exception of type {0} occurred in function cast_value(). error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error("{}".format(message))
        log_error()
        return value  # Return as-is if casting fails

def get_stock_list():
    CSV_FILE = 'master_data.csv'
    strategy_data_path = './strategy_data/'
    currentstocklist_path = strategy_data_path + CSV_FILE
    stock_list = []
    try:
        with open(currentstocklist_path, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Only include stocks with NOT_TRIGGERED status
                if row['status'] == 'NOT_TRIGGERED':
                    stock_list.append(row['Symbol'])
        return stock_list
    except Exception as err:
        template = "An exception of type {0} occurred in function get_stock_list(). error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error("{}".format(message))
        log_error()

def get_highPrice_from_csv(stock_name):
    CSV_FILE = 'master_data.csv'
    strategy_data_path = './strategy_data/'
    currentstocklist_path = strategy_data_path + CSV_FILE
    try:
        with open(currentstocklist_path, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['Symbol'].strip().upper() == stock_name.strip().upper():
                # Parse the date and check age
                    date_added = dt.datetime.strptime(row['date_added'], "%d-%m-%Y")
                    days_diff = (dt.datetime.today() - date_added).days
                    print(f"days_diff for stock {stock_name}: {days_diff}")
                    if days_diff > 10:
                        return None
                    # Check if status is NOT_TRIGGERED
                    if row['status'] != 'NOT_TRIGGERED':
                        return None
                    print(f"trigger price for stock {stock_name}: {row['Trigger_price']}")
                    return float(row['Trigger_price']) if row['Trigger_price'] else None
    except Exception as err:
        template = "An exception of type {0} occurred in function get_highPrice_from_csv(). error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error("{}".format(message))
        log_error()
        return None  # if stock not found

def update_stock_status_in_csv(stock_name, new_status=None, new_price=None, update_date=True):
    """
    Update stock status, price, and date in master_data.csv
    
    Parameters:
    - stock_name: Stock symbol to update
    - new_status: New status to set ('TRIGGERED', 'NOT_TRIGGERED', etc.)
    - new_price: New trigger price to set (optional)
    - update_date: Whether to update date_added to today (default: True)
    
    Usage examples:
    - Mark stock as triggered: update_stock_status_in_csv('TITAN-EQ', new_status='TRIGGERED')
    - Update price only: update_stock_status_in_csv('TITAN-EQ', new_price=3300.50)
    - Reset stock: update_stock_status_in_csv('TITAN-EQ', new_status='NOT_TRIGGERED', new_price=3400.00)
    """
    today_str = dt.datetime.today().strftime("%d-%m-%Y")
    updated = False
    updated_rows = []

    CSV_FILE = 'master_data.csv'
    strategy_data_path = './strategy_data/'
    currentstocklist_path = strategy_data_path + CSV_FILE
    
    try:
        with open(currentstocklist_path, mode='r') as file:
            reader = csv.DictReader(file)
            updated_rows = list(reader)
    except FileNotFoundError:
        print("CSV file not found.")
        lg.error(f"Master data CSV file not found: {currentstocklist_path}")
        return False
    except Exception as err:
        template = "An exception of type {0} occurred in function update_stock_status_in_csv() while reading. error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error("{}".format(message))
        log_error()
        return False

    for row in updated_rows:
        if row['Symbol'].strip().upper() == stock_name.strip().upper():
            # Update status if provided
            if new_status is not None:
                row['status'] = new_status
                lg.info(f"Updated status for {stock_name} to: {new_status}")
            
            # Update trigger price if provided
            if new_price is not None:
                row['Trigger_price'] = str(new_price)
                lg.info(f"Updated trigger price for {stock_name} to: {new_price}")
            
            # Update date if requested
            if update_date:
                row['date_added'] = today_str
                lg.info(f"Updated date for {stock_name} to: {today_str}")
            
            updated = True
            break

    if not updated:
        lg.warning(f"Stock '{stock_name}' not found in CSV.")
        return False

    try:
        with open(currentstocklist_path, mode='w', newline='') as file:
            fieldnames = ['Symbol', 'Total_Lists', 'Trigger_price', 'date_added', 'status']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(updated_rows)
        
        lg.info(f"Successfully updated stock data for '{stock_name}' in master_data.csv")
        return True
        
    except Exception as err:
        template = "An exception of type {0} occurred in function update_stock_status_in_csv() while writing. error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error("{}".format(message))
        log_error()
        return False

# Legacy function for backward compatibility
def update_highPrice_in_csv(stock_name, price=None):
    """
    Legacy function for backward compatibility.
    Use update_stock_status_in_csv() for new implementations.
    """
    if price is None:
        # Mark as TRIGGERED when stock is bought (legacy behavior)
        return update_stock_status_in_csv(stock_name, new_status='TRIGGERED')
    else:
        # Update price (legacy behavior)
        return update_stock_status_in_csv(stock_name, new_price=price)

def mark_stock_as_triggered(stock_name):
    """
    Helper function to mark a stock as TRIGGERED when buy order is successful.
    This should be called from autotick.py after successful buy order execution.
    """
    try:
        success = update_stock_status_in_csv(stock_name, new_status='TRIGGERED')
        if success:
            lg.info(f"Successfully marked {stock_name} as TRIGGERED after buy order")
        else:
            lg.error(f"Failed to mark {stock_name} as TRIGGERED after buy order")
        return success
    except Exception as err:
        template = "An exception of type {0} occurred in function mark_stock_as_triggered(). error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error("{}".format(message))
        log_error()
        return False

def reset_stock_status(stock_name, new_trigger_price=None):
    """
    Helper function to reset a stock status to NOT_TRIGGERED.
    Optionally updates the trigger price as well.
    """
    try:
        success = update_stock_status_in_csv(stock_name, 
                                           new_status='NOT_TRIGGERED', 
                                           new_price=new_trigger_price)
        if success:
            lg.info(f"Successfully reset {stock_name} to NOT_TRIGGERED")
        else:
            lg.error(f"Failed to reset {stock_name} status")
        return success
    except Exception as err:
        template = "An exception of type {0} occurred in function reset_stock_status(). error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error("{}".format(message))
        log_error()
        return False

def remove_stock_from_list(stock_name):
    """
    Remove a stock completely from the master_data.csv file.
    This should be called after successful sell order completion.
    """
    try:
        CSV_FILE = 'master_data.csv'
        strategy_data_path = './strategy_data/'
        currentstocklist_path = strategy_data_path + CSV_FILE
        
        # Read existing data
        updated_rows = []
        stock_found = False
        
        try:
            with open(currentstocklist_path, mode='r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row['Symbol'].strip().upper() != stock_name.strip().upper():
                        updated_rows.append(row)
                    else:
                        stock_found = True
                        lg.info(f"Found and removing stock: {stock_name}")
        except FileNotFoundError:
            lg.error(f"Master data CSV file not found: {currentstocklist_path}")
            return False
        
        if not stock_found:
            lg.warning(f"Stock '{stock_name}' not found in master data for removal")
            return False
        
        # Write updated data back to file
        try:
            with open(currentstocklist_path, mode='w', newline='') as file:
                fieldnames = ['Symbol', 'Total_Lists', 'Trigger_price', 'date_added', 'status']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(updated_rows)
            
            lg.info(f"Successfully removed {stock_name} from master_data.csv after sell order")
            return True
            
        except Exception as err:
            template = "An exception of type {0} occurred in function remove_stock_from_list() while writing. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            log_error()
            return False
            
    except Exception as err:
        template = "An exception of type {0} occurred in function remove_stock_from_list(). error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error("{}".format(message))
        log_error()
        return False
