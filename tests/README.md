# Tests Directory

This directory contains all test files for the AutoTick trading system.

## Test Files

### test_stock_status.py
Tests the new stock status management functionality including:
- `update_stock_status_in_csv()` - Main function for updating stock status, price, and date
- `mark_stock_as_triggered()` - Helper to mark stocks as triggered after buy orders
- `reset_stock_status()` - Helper to reset stock status to NOT_TRIGGERED
- `update_stock_list()` - Function to update stock list from daily trading files

**Usage:**
```bash
cd /path/to/autotick
python tests/test_stock_status.py
```

### test_main.py
Tests for the main trading application functionality.

### test_websocket.py
Tests for websocket connectivity and data streaming.

## Running Tests

All tests should be run from the autotick root directory to ensure correct file paths:

```bash
cd /path/to/autotick
python tests/test_stock_status.py
python tests/test_main.py
python tests/test_websocket.py
```

## Notes

- Tests automatically change the working directory to the autotick root
- Ensure all dependencies are installed before running tests
- Tests use the actual strategy_data files, so results may vary based on current data
