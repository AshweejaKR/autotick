# -*- coding: utf-8 -*-
"""
Created on Fri Jun 21 23:36:16 2024

@author: ashwe
"""

from broker import *
if debug:
    from broker_stub import *

def ltp_test(ticker, exchange):
    c = 0
    res = "NA"
    print("starting ...")
    obj = broker()
    while True:
        x = obj.get_current_price(ticker, exchange)
        try:
            print("Current price: ", x)
            c = c + 1

            if c > 20:
                print("THE END ...")
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
        obj = broker()
        qty = 2
        
        x = obj.get_current_price(ticker, exchange)
        print("Current price: ", x)
        print("----------------------------------\n")

        amt = obj.get_margin()
        print("Available Amount: ", amt)
        print("----------------------------------\n")
        
        oid = obj.place_buy_order(ticker, qty, exchange)
        print("Order ID: ", oid)
        print("----------------------------------\n")
    
        x = obj.get_entry_exit_price(ticker)
        print("Entry price: ", x)
        print("----------------------------------\n")

        stat = obj.get_oder_status(oid)
        print("Order ID status: ", stat)
        print("----------------------------------\n")
        
        oid = obj.place_sell_order(ticker, qty, exchange)
        print("Order ID: ", oid)
        print("----------------------------------\n")

        x = obj.get_entry_exit_price(ticker, True)
        print("Exit price: ", x)
        print("----------------------------------\n")

        stat = obj.get_oder_status(oid)
        print("Order ID status: ", stat)
        print("----------------------------------\n")
        
        data = obj.get_user_data()
        print("User data: ", data)
        print("----------------------------------\n")
        
        duration = 5
        data = obj.hist_data_daily(ticker, duration, exchange)
        print("Hist daily data: ", data, '\n')
        print("----------------------------------\n")
    
        data = obj.hist_data_intraday(ticker, exchange)
        print("Hist Intraday data: ", data, '\n')
        print("----------------------------------\n")

        qty = 10
        data = obj.verify_holding(ticker, qty)
        print("verify holding: ", data)
        print("----------------------------------\n")

        data = obj.verify_position(ticker, qty)
        print("verify entry position: ", data)
        print("----------------------------------\n")
        
        data = obj.verify_position(ticker, qty, True)
        print("verify exit position: ", data)
        print("----------------------------------\n")
        
        print(dir(obj))
        del obj
        res = "PASS"
        print("running the test: DONE")
    except Exception as err:
        print(err)
        res = "FAIL"

    print("test result: {}".format(res))

def VERIFY(actual, expected):
    return (actual == expected)

def stub_test(ticker, exchange):
    print("Running the test for {}, {} ... \n".format(ticker, exchange))

    res = True
    test_done = False
    try:
        obj = broker()
        qty = 2
        
        x = obj.get_current_price(ticker, exchange)
        print("Current price: ", x)
        print("----------------------------------\n")
        res = res and VERIFY(x, 100.55)
        print("RESULT: {} \n".format(res))

        amt = obj.get_margin()
        print("Available Amount: ", amt)
        print("----------------------------------\n")
        res = res and VERIFY(amt, 5001.50)
        print("RESULT: {} \n".format(res))
        
        oid = obj.place_buy_order(ticker, qty, exchange)
        print("Order ID: ", oid)
        print("----------------------------------\n")
        res = res and VERIFY(oid, "12345")
        print("RESULT: {} \n".format(res))
    
        x = obj.get_entry_exit_price(ticker)
        print("Entry price: ", x)
        print("----------------------------------\n")
        res = res and VERIFY(x, 250)
        print("RESULT: {} \n".format(res))

        stat = obj.get_oder_status(oid)
        print("Order ID status: ", stat)
        print("----------------------------------\n")
        res = res and VERIFY(stat, "DONE")
        print("RESULT: {} \n".format(res))
        
        oid = obj.place_sell_order(ticker, qty, exchange)
        print("Order ID: ", oid)
        print("----------------------------------\n")
        res = res and VERIFY(oid, "54321")
        print("RESULT: {} \n".format(res))

        x = obj.get_entry_exit_price(ticker, True)
        print("Exit price: ", x)
        print("----------------------------------\n")
        res = res and VERIFY(x, 500)
        print("RESULT: {} \n".format(res))

        stat = obj.get_oder_status(oid)
        print("Order ID status: ", stat)
        print("----------------------------------\n")
        res = res and VERIFY(stat, "DONE")
        print("RESULT: {} \n".format(res))
        
        # data = obj.get_user_data()
        # print("User data: ", data)
        # print("----------------------------------\n")
        # res = res and VERIFY(actual, expected)
        
        qty = 10
        data = obj.verify_holding(ticker, qty)
        print("verify holding: ", data)
        print("----------------------------------\n")
        res = res and VERIFY(data, True)
        print("RESULT: {} \n".format(res))

        data = obj.verify_position(ticker, 2)
        print("verify entry position: ", data)
        print("----------------------------------\n")
        res = res and VERIFY(data, True)
        print("RESULT: {} \n".format(res))
        
        data = obj.verify_position(ticker, 2, True)
        print("verify exit position: ", data)
        print("----------------------------------\n")
        res = res and VERIFY(data, True)
        print("RESULT: {} \n".format(res))

        test_done = True
    except Exception as err:
        print(err)
        res = "FAIL"

    if (test_done):
        print("TEST EXECUTED SUCCESFULLY & TEST RESULT: {} \n".format(res))
    
    else:
        print("TEST DOES NOT EXECUTED, FAILED \n")

ticker = "NIFTYBEES-EQ"
exchange = "NSE"
run_test(ticker, exchange)
ltp_test(ticker, exchange)

stub_test(ticker, exchange)
