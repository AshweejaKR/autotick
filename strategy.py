# -*- coding: utf-8 -*-
"""
Created on Sat May 17 16:48:59 2025

@author: ashwe
"""
from logger import *
from utils import *
import csv
import os
import datetime as dt

global trigger_prices
trigger_prices = {}

def update_stock_list():
    """
    Update stock list by reading from daily trading file and updating master_data.csv
    - Reads CSV file: trading_stocks_%d%m%Y (e.g., trading_stocks_05082025)
    - Updates master_data.csv with columns: Symbol, Total_Lists, Trigger_price, date_added, status
    - Default values: date_added=today, status=NOT_TRIGGERED
    - Logic: If symbol exists and status=NOT_TRIGGERED, update date_added; if TRIGGERED, ignore
    """
    try:
        # Calculate previous trading day (assuming previous day for now)
        yesterday = dt.date.today() - dt.timedelta(days=1)
        trading_file_date = yesterday.strftime("%d%m%Y")
        trading_filename = f"trading_stocks_{trading_file_date}.csv"
        
        strategy_data_path = './strategy_data/'
        trading_file_path = strategy_data_path + trading_filename
        master_file_path = strategy_data_path + 'master_data.csv'
        
        lg.info(f"Reading trading stocks from: {trading_filename}")
        
        # Check if trading file exists
        if not os.path.isfile(trading_file_path):
            lg.error(f"Trading stocks file not found: {trading_filename}")
            return False
        
        # Read trading stocks data
        trading_stocks = []
        with open(trading_file_path, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                trading_stocks.append({
                    'Symbol': row.get('Symbol', '').strip(),
                    'Total_Lists': row.get('Total_Lists', '').strip(),
                    'Trigger_price': row.get('Trigger_price', '').strip()
                })
        
        lg.info(f"Read {len(trading_stocks)} stocks from trading file")
        
        # Read existing master data if file exists
        existing_master_data = {}
        fieldnames = ['Symbol', 'Total_Lists', 'Trigger_price', 'date_added', 'status']
        
        if os.path.isfile(master_file_path):
            with open(master_file_path, mode='r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    existing_master_data[row['Symbol']] = {
                        'Total_Lists': row['Total_Lists'],
                        'Trigger_price': row['Trigger_price'],
                        'date_added': row['date_added'],
                        'status': row['status']
                    }
        
        # Today's date string
        today_str = dt.date.today().strftime("%d-%m-%Y")
        
        # Process trading stocks and update master data
        updated_count = 0
        ignored_count = 0
        new_count = 0
        
        for stock in trading_stocks:
            symbol = stock['Symbol']
            if not symbol:  # Skip empty symbols
                continue
                
            if symbol in existing_master_data:
                # Symbol exists, check status
                if existing_master_data[symbol]['status'] == 'NOT_TRIGGERED':
                    # Update date_added to today
                    existing_master_data[symbol]['Total_Lists'] = stock['Total_Lists']
                    existing_master_data[symbol]['Trigger_price'] = stock['Trigger_price']
                    existing_master_data[symbol]['date_added'] = today_str
                    updated_count += 1
                    lg.info(f"Updated NOT_TRIGGERED stock: {symbol}")
                else:  # status is TRIGGERED
                    # Ignore this stock
                    ignored_count += 1
                    lg.info(f"Ignored TRIGGERED stock: {symbol}")
            else:
                # New symbol, add to master data
                existing_master_data[symbol] = {
                    'Total_Lists': stock['Total_Lists'],
                    'Trigger_price': stock['Trigger_price'],
                    'date_added': today_str,
                    'status': 'NOT_TRIGGERED'
                }
                new_count += 1
                lg.info(f"Added new stock: {symbol}")
        
        # Write updated master data back to file
        with open(master_file_path, mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            
            for symbol, data in existing_master_data.items():
                writer.writerow({
                    'Symbol': symbol,
                    'Total_Lists': data['Total_Lists'],
                    'Trigger_price': data['Trigger_price'],
                    'date_added': data['date_added'],
                    'status': data['status']
                })
        
        lg.info(f"Stock list update completed: {new_count} new, {updated_count} updated, {ignored_count} ignored")
        return True
        
    except Exception as err:
        template = "An exception of type {0} occurred in function update_stock_list(). error message:{1!r}"
        message = template.format(type(err).__name__, err.args)
        lg.error("{}".format(message))
        log_error()
        return False

def init_strategy(obj):
    """Initialize strategy by reading trigger prices from strategy_data/master_data.csv"""
    global trigger_prices
    lg.info(f"Initializing Strategy for Stock {obj.ticker} in {obj.Exchange} exchange ... ")
    
    # Get trigger price from strategy_data/master_data.csv
    trigger_price = get_highPrice_from_csv(obj.ticker)
    trigger_prices[obj.ticker] = trigger_price
    
    cur_price = obj.broker_obj.get_current_price(obj.ticker, obj.Exchange)
    lg.info(f"Trigger price for stock: {obj.ticker} : {trigger_prices[obj.ticker]} and Current price: {cur_price} ")

def run_strategy(obj):
    """
    Trading Strategy:
    - BUY if current price > trigger price
    - After BUY, reset trigger price to None
    - Return NA if trigger price is None or empty
    """
    global trigger_prices
    myPrint(f"Running Strategy for Stock {obj.ticker} in {obj.Exchange} exchange ... ")
    
    # Get current trigger price
    trigger_price = trigger_prices.get(obj.ticker)
    
    # Get current market price
    cur_price = obj.broker_obj.get_current_price(obj.ticker, obj.Exchange)
    myPrint(f"Current price for Stock {obj.ticker} = {cur_price} > Trigger price: {trigger_price} \n")

    # Return NA if trigger price is None or empty
    if not trigger_price:
        return "NA"
    
    # Check if price crosses trigger price
    if cur_price > trigger_price:
        # Reset trigger price to None and mark as TRIGGERED
        from utils import update_stock_status_in_csv
        
        # Mark stock as TRIGGERED in master_data.csv when buy signal is generated
        success = update_stock_status_in_csv(obj.ticker, new_status='TRIGGERED')
        if success:
            lg.info(f"Stock {obj.ticker} marked as TRIGGERED in master_data.csv")
            trigger_prices[obj.ticker] = None  # Reset trigger price in memory
        else:
            lg.error(f"Failed to update status for {obj.ticker} in master_data.csv")
        
        return "BUY"
    
    return "NA"

    # for testing only
    # lg.info(f"Running Strategy for Stock {obj.ticker} in {obj.Exchange} exchange ... ")
    # cur_price = obj.broker_obj.get_current_price(obj.ticker, obj.Exchange)
    # lg.info("current price: {} \n".format(cur_price))
    # filename = "C:\\user\\ashwee\\stub_test.txt"
    # signal = None
    # try:
    #     with open(filename) as file:
    #         data = file.readlines()
    #         x = int(data[0])
    #         if x == 1:
    #             signal = "BUY"
    #         if x == 2:
    #             signal = "SELL"
    # except Exception as err: 
    #     print(err)
    # return signal
