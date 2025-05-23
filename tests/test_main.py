import sys, os
import time
from enum import Enum

cwd = os.getcwd()
os.chdir("..")
main_path = os.getcwd()
sys.path.append(main_path)

# from broker_angleone import *
# from broker_aliceblue import *
# from broker_stub import *
from broker import *

from logger import *

def main():
    initialize_logger()
    lg.info("Hello Testing 1 2 3")
    start = time.time()
    print("T0 : {}".format(start))
    #######################################################################
    supported_broker_list = ["ANGELONE", "ALICEBLUE", "NOBROKER"]
    # supported_broker_list = ["NOBROKER"]
    for broker_name in supported_broker_list:
        broker_obj = Broker(0, broker_name)
        Exchange = "NSE"
        ticker = "NIFTYBEES-EQ"
        datestamp = dt.date.today()
        quantity = 1
        duration = 30
        trade_direction = "SELL"

        user_data = broker_obj.get_user_data()
        lg.info(f"{broker_name}: user data : {user_data}")
        lg.info("---------------------------------------------------------\n")

        user_amt = broker_obj.get_available_margin()
        lg.info(f"{broker_name}: available margin: {user_amt}")
        lg.info("---------------------------------------------------------\n")

        current_price = broker_obj.get_current_price(ticker, Exchange)
        lg.info(f"{broker_name}: {ticker} current_price: {current_price}")
        lg.info("---------------------------------------------------------\n")

        data1 = broker_obj.hist_data_daily(ticker, duration, Exchange, datestamp)
        lg.info(f"{broker_name}: {ticker} historical data 1D: {data1}")
        lg.info("---------------------------------------------------------\n")

        data2 = broker_obj.hist_data_intraday(ticker, Exchange, datestamp)
        lg.info(f"{broker_name}: {ticker} historical data 1m: {data2}")
        lg.info("---------------------------------------------------------\n")

        status = broker_obj.place_buy_order(ticker, quantity, Exchange)
        lg.info(f"{broker_name}: buy order status for {ticker}, {quantity} qty: {status}, err: {broker_obj.error_msg}")
        lg.info("---------------------------------------------------------\n")

        status = broker_obj.place_sell_order(ticker, quantity, Exchange)
        lg.info(f"{broker_name}: sell order status for {ticker}, {quantity} qty: {status}, err: {broker_obj.error_msg}")
        lg.info("---------------------------------------------------------\n")

        status = broker_obj.verify_position(ticker, quantity, trade_direction)
        lg.info(f"{broker_name}: Position status for {ticker}, {quantity} qty: {status}")
        lg.info("---------------------------------------------------------\n")

        status = broker_obj.verify_position(ticker, quantity, trade_direction, True)
        lg.info(f"{broker_name}: Position status for {ticker}, {quantity} qty: {status}")
        lg.info("---------------------------------------------------------\n")

        status = broker_obj.verify_holding(ticker, quantity)
        lg.info(f"{broker_name}: holding status for {ticker}, {quantity} qty: {status}")
        lg.info("---------------------------------------------------------\n")

        entry_price = broker_obj.get_entry_exit_price(ticker, trade_direction)
        lg.info(f"{broker_name}: {ticker} Entry Price: {entry_price}")
        lg.info("---------------------------------------------------------\n")

        exit_price = broker_obj.get_entry_exit_price(ticker, trade_direction, True)
        lg.info(f"{broker_name}: {ticker} Exit Price: {exit_price}")
        lg.info("---------------------------------------------------------\n")

        del broker_obj

    #######################################################################
    print("Done ...")
    end = time.time()
    print("T1 : {}".format(end))
    diff = end - start
    print("T: {} \n".format(time.strftime('%H:%M:%S', time.gmtime(diff))))

if __name__ == "__main__":
    main()
