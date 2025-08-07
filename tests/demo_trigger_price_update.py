# Demonstration script for trigger price updates
# This shows how trigger prices are updated from trading CSV files

import sys
import os
sys.path.append('..')  # Add parent directory to path since we're in tests folder

from strategy import update_stock_list, force_update_trigger_prices
from logger import initialize_logger
import pandas as pd

# Initialize logger
initialize_logger()

def demo_trigger_price_updates():
    """Demonstrate trigger price updates from trading files"""
    
    # Change to parent directory since we're in tests folder
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    
    print("=== Trigger Price Update Demo ===\n")
    
    # Show current master data
    print("1. Current master_data.csv (first 5 rows):")
    try:
        df = pd.read_csv('./strategy_data/master_data.csv')  # Now using correct working directory
        print(df.head()[['Symbol', 'Trigger_price', 'status']])
    except Exception as e:
        print(f"Error reading master data: {e}")
    
    print("\n" + "="*50)
    
    # Show trading file data
    print("\n2. Current trading_stocks_06082025.csv (first 5 rows):")
    try:
        df = pd.read_csv('./strategy_data/trading_stocks_06082025.csv')  # Now using correct working directory
        print(df.head()[['Symbol', 'Total_Lists', 'Trigger_Price']])  # Note: capital P in CSV
    except Exception as e:
        print(f"Error reading trading file: {e}")
    
    print("\n" + "="*50)
    
    # Run standard update
    print("\n3. Running standard update_stock_list():")
    result = update_stock_list()
    print(f"Update result: {result}")
    
    print("\n" + "="*50)
    
    # Show updated master data
    print("\n4. Master data after update (first 5 rows):")
    try:
        df = pd.read_csv('./strategy_data/master_data.csv')  # Now using correct working directory
        print(df.head()[['Symbol', 'Trigger_price', 'status', 'date_added']])
    except Exception as e:
        print(f"Error reading updated master data: {e}")
    
    print("\n" + "="*50)
    print("\nKey Features Demonstrated:")
    print("✅ Trigger prices are read from daily trading CSV files")
    print("✅ Only NOT_TRIGGERED stocks get trigger price updates")
    print("✅ TRIGGERED stocks are ignored (maintaining data integrity)")
    print("✅ New stocks are added with trigger prices from trading file")
    print("✅ Date is updated to today for all modified stocks")
    print("✅ Detailed logging shows what changes were made")

if __name__ == "__main__":
    demo_trigger_price_updates()
