# -*- coding: utf-8 -*-
"""
Created on Fri Jun 21 20:58:12 2024

@author: ashwe
"""
import time

from autotick import *
from test import *

def main():
    initialize_logger()
    
    lg.info("Trading Bot running ... ! \n")
    send_to_telegram("Trading Bot running ... ! \n")

    ticker = "NIFTYBEES-EQ"
    exchange = "NSE"
    # run_test(ticker, exchange)
    # ltp_test(ticker, exchange)
    
    # ticker = "GOLDPETAL24JULFUT"
    # exchange = "MCX"
    # run_test(ticker, exchange)
    # ltp_test(ticker, exchange)
    
    obj = autotick(ticker, exchange)
    obj.set_stoploss(5.00)
    obj.set_takeprofit(10.00)

    obj.run()

    lg.info("Trading Bot done ...")
    send_to_telegram("Trading Bot done ...")

if __name__ == '__main__':
    main()