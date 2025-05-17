# -*- coding: utf-8 -*-
"""
Created on Sat Nov 30 18:11:42 2024

@author: ashwe
"""

import sys
from enum import Enum

from logger import *
# from autotick import *

from broker import *

def main():

    initialize_logger()
    lg.info("Trading Bot running ... ! \n")

    start = time.time()

    ###########################################################################
    datestamp = dt.date.today()
    ###########################
    ###########################################################################
    obj = Broker(0, "ANGELONE")
    stock = "INFY-EQ"
    exchange = "NSE"
    duration = 10
    quantity = 1

    user_data = obj.get_user_data()
    print("angleone user data : ", user_data)
    print("---------------------------------------------------------\n")

    user_amt = obj.get_available_margin()
    print("angleone available margin : ", user_amt)
    print("---------------------------------------------------------\n")

    current_price = obj.get_current_price(stock, exchange)
    print("angleone current_price : ", current_price)
    print("---------------------------------------------------------\n")

    data1 = obj.hist_data_daily(stock, duration, exchange, datestamp)
    print("angleone data : ", data1)
    print("---------------------------------------------------------\n")

    data4 = obj.hist_data_intraday(stock, exchange, datestamp)
    print("angleone data : ", data4)
    print("---------------------------------------------------------\n")

    oid = obj.place_buy_order(stock, quantity, exchange)
    print("angleone Order ID : ", oid)
    print("---------------------------------------------------------\n")

    status = obj.get_oder_status(oid)
    print("angleone Order status : ", status)
    print("angleone Order status error : ", obj.error_msg)
    print("---------------------------------------------------------\n")

    oid = obj.place_sell_order(stock, quantity, exchange)
    print("angleone Order ID : ", oid)
    print("---------------------------------------------------------\n")

    status = obj.get_oder_status(oid)
    print("angleone Order status : ", status)
    print("angleone Order status error : ", obj.error_msg)
    print("---------------------------------------------------------\n")

    status = obj.verify_position(stock, quantity)
    print("angleone Position status : ", status)
    print("---------------------------------------------------------\n")

    status = obj.verify_position(stock, quantity, True)
    print("angleone Position status : ", status)
    print("---------------------------------------------------------\n")

    status = obj.verify_holding(stock, quantity)
    print("angleone holding status : ", status)
    print("---------------------------------------------------------\n")

    price = obj.get_entry_exit_price(stock)
    print("angleone Entry Price : ", price)
    print("---------------------------------------------------------\n")

    price = obj.get_entry_exit_price(stock, True)
    print("angleone Exit Price : ", price)
    print("---------------------------------------------------------\n")

    del obj

    # obj = Broker(0, "NOBROKER")
    # del obj
    ###########################################################################
    # obj = autotick(datestamp)
    # obj.run_trade()
    # del obj
    ###########################################################################
    end = time.time()
    diff = end - start
    lg.info("Total time taken : {} \n".format(time.strftime('%H:%M:%S', time.gmtime(diff))))

    lg.done("Trading Bot done ...")
    
if __name__ == "__main__":
    main()
