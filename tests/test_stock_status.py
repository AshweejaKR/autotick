# Test script to demonstrate the new stock status update functionality
# This can be run separately to test the functions

import sys
import os

# Add parent directory to path to import modules from autotick project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import update_stock_status_in_csv, mark_stock_as_triggered, reset_stock_status, remove_stock_from_list
from logger import initialize_logger

# Initialize logger for testing
initialize_logger()

def test_stock_status_updates():
    """Test the new stock status update functionality"""
    
    print("=== Testing Stock Status Update Functions ===")
    
    # Test 1: Mark a stock as triggered
    print("\n1. Testing mark_stock_as_triggered():")
    result = mark_stock_as_triggered('TITAN-EQ')
    print(f"Result: {result}")
    
    # Test 2: Update price and status together
    print("\n2. Testing update_stock_status_in_csv() with price and status:")
    result = update_stock_status_in_csv('HUDCO-EQ', new_status='TRIGGERED', new_price=250.00)
    print(f"Result: {result}")
    
    # Test 3: Reset a stock status
    print("\n3. Testing reset_stock_status():")
    result = reset_stock_status('TITAN-EQ', new_trigger_price=3300.00)
    print(f"Result: {result}")
    
    # Test 4: Update only price without changing status
    print("\n4. Testing price-only update:")
    result = update_stock_status_in_csv('ASTRAL-EQ', new_price=1900.00, update_date=False)
    print(f"Result: {result}")
    
    # Test 5: Test non-existent stock
    print("\n5. Testing with non-existent stock:")
    result = update_stock_status_in_csv('NONEXISTENT-EQ', new_status='TRIGGERED')
    print(f"Result: {result}")
    
    # Test 6: Test removing a stock from the list
    print("\n6. Testing remove_stock_from_list():")
    result = remove_stock_from_list('TECHM-EQ')
    print(f"Result: {result}")
    
    # Test 7: Test removing a non-existent stock
    print("\n7. Testing remove_stock_from_list() with non-existent stock:")
    result = remove_stock_from_list('REMOVED-EQ')
    print(f"Result: {result}")
    
    print("\n=== Test completed ===")
    print("Note: Run this test from the autotick root directory for correct file paths")

def test_update_stock_list():
    """Test the update_stock_list function from strategy module"""
    print("\n=== Testing update_stock_list() Function ===")
    
    try:
        from strategy import update_stock_list
        result = update_stock_list()
        print(f"update_stock_list() result: {result}")
    except Exception as e:
        print(f"Error testing update_stock_list(): {e}")

if __name__ == "__main__":
    # Change working directory to autotick root for correct file paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    autotick_root = os.path.dirname(script_dir)
    os.chdir(autotick_root)
    print(f"Changed working directory to: {autotick_root}")
    
    test_stock_status_updates()
    test_update_stock_list()
