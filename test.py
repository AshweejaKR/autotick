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
    res = "NA"
    print("starting ...")
    time.sleep(delay)
    obj = broker()
    while True:
        x = obj.get_current_price(ticker, exchange)
        try:
            print("Current price: ", x)
            c = c + 1
            print("waiting ...")
            time.sleep(delay)

            if c > 2:
                print("THE END ...")
                time.sleep(delay)
                del obj
                res = "PASS"
                break

        except KeyboardInterrupt:
            print("bot stop request by user")
            res = "PASS"
            break

        except Exception as err:
            print(err)
            res = "FAIL"

    print("ltp test result: {}".format(res))

def run_test(ticker, exchange):
    res = "NA"
    try:
        print("running the test ...")
        time.sleep(delay)

        obj = broker()
        
        data = obj.get_user_data()
        print(data)
        print("----------------------------------\n")
        time.sleep(delay)
        
        amt = obj.get_margin()
        print(amt)
        print("----------------------------------\n")
        time.sleep(delay)
        
        x = obj.get_current_price(ticker, exchange)
        print("Current price: ", x)
        print("----------------------------------\n")
        time.sleep(delay)
    
        duration = 5
        data = obj.hist_data_daily(ticker, duration, exchange)
        print(data, '\n')
        print("----------------------------------\n")
        time.sleep(delay)
    
        data = obj.hist_data_intraday(ticker, exchange)
        print(data)
        print("----------------------------------\n")
        time.sleep(delay)
        
        oid = obj.place_buy_order(ticker, 10, exchange)
        print(oid)
        print("----------------------------------\n")
        time.sleep(delay)

        stat = obj.get_oder_status(oid)
        print(stat)
        print("----------------------------------\n")
        time.sleep(delay)
        
        oid = obj.place_sell_order(ticker, 10, exchange)
        print(oid)
        print("----------------------------------\n")
        time.sleep(delay)

        stat = obj.get_oder_status(oid)
        print(stat)
        print("----------------------------------\n")
        time.sleep(delay)
        
        del obj
        res = "PASS"
        print("running the test: DONE")
    except Exception as err:
        print(err)
        res = "FAIL"

    print("test result: {}".format(res))