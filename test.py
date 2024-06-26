# -*- coding: utf-8 -*-
"""
Created on Fri Jun 21 23:36:16 2024

@author: ashwe
"""

from broker import *
# from broker_stub import *

delay = 1.2

def ltp_test(ticker, exchange):
    c = 0
    obj = broker()
    while True:
        try:
            x = obj.get_current_price(ticker, exchange)
            print("Current price: ", x)
            c = c + 1
            time.sleep(delay)

            if c > 2:
                break
        except KeyboardInterrupt:
            print("bot stop request by user")
            break
        except Exception as err:
            print(err)

def run_test(ticker, exchange):
    res = "NA"
    try:
        obj = broker()
        
        data = obj.get_user_data()
        print(data)
        time.sleep(delay)
        
        amt = obj.get_margin()
        print(amt)
        time.sleep(delay)
        
        x = obj.get_current_price(ticker, exchange)
        print("Current price: ", x)
        time.sleep(delay)
    
        duration = 5
        data = obj.hist_data_daily(ticker, duration, exchange)
        print(data, '\n')
        time.sleep(delay)
    
        data = obj.hist_data_intraday(ticker, exchange)
        print(data)
        time.sleep(delay)
        
        oid = obj.place_buy_order(ticker, 10, exchange)
        print(oid)
        time.sleep(delay)

        stat = obj.get_oder_status(oid)
        print(stat)
        time.sleep(delay)
        
        oid = obj.place_sell_order(ticker, 10, exchange)
        print(oid)
        time.sleep(delay)

        stat = obj.get_oder_status(oid)
        print(stat)
        time.sleep(delay)
        
        del obj
        res = "PASS"
    except Exception as err:
        print(err)
        res = "FAIL"

    print("test result: {}".format(res))