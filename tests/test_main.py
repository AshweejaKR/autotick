import sys, os
import time
from enum import Enum

cwd = os.getcwd()
os.chdir("..")
main_path = os.getcwd()
sys.path.append(main_path)

from broker_angleone import *
from broker_aliceblue import *
from broker_stub import *
from logger import *

class Mode(Enum):
    LIVE_TRADE = 1
    PAPER_TRADE = 2
    BACKTEST = 3
    USER_TEST = 4

def main():
    initialize_logger()
    print("Hello")
    start = time.time()
    print("T0 : {}".format(start))

    obj_1 = angleone()
    obj_2 = aliceblue()

    mode = Mode.BACKTEST
    obj_stub = stub(mode)
    broker_objs = [obj_1, obj_2, obj_stub]

    x = int(input("Select No for Broker:\n1. ANGELONE\n2. ALICEBLUE\n3. NOBROKER\n4. ALL\n\nEnter:\n"))

    exchange = "NSE"
    stock = "INFY-EQ"
    datestamp = dt.date.today()
    duration = 10
    quantity = 1
    stock = "INFY-EQ"
    quantity = 1

    x = x - 1
    if x < len(broker_objs):
        test_obj = broker_objs[x]
        for i in broker_objs[:]:
            if i != test_obj:
                broker_objs.remove(i)

    for i in broker_objs:
        user_data = i.get_user_data()
        print("angleone user data : ", user_data)
        print("---------------------------------------------------------\n")

        user_amt = i.get_available_margin()
        print("angleone available margin : ", user_amt)
        print("---------------------------------------------------------\n")

        current_price = i.get_current_price(stock, exchange)
        print("angleone current_price : ", current_price)
        print("---------------------------------------------------------\n")

        data1 = i.hist_data_daily(stock, duration, exchange, datestamp)
        print("angleone data : ", data1)
        print("---------------------------------------------------------\n")

        data4 = i.hist_data_intraday(stock, exchange, datestamp)
        print("angleone data : ", data4)
        print("---------------------------------------------------------\n")

        oid = i.place_buy_order(stock, quantity, exchange)
        print("angleone Order ID : ", oid)
        print("---------------------------------------------------------\n")

        status = i.get_oder_status(oid)
        print("angleone Order status : ", status)
        print("angleone Order status error : ", obj_1.error_msg)
        print("---------------------------------------------------------\n")

        oid = i.place_sell_order(stock, quantity, exchange)
        print("angleone Order ID : ", oid)
        print("---------------------------------------------------------\n")

        status = i.get_oder_status(oid)
        print("angleone Order status : ", status)
        print("angleone Order status error : ", obj_1.error_msg)
        print("---------------------------------------------------------\n")

        status = i.verify_position(stock, quantity)
        print("angleone Position status : ", status)
        print("---------------------------------------------------------\n")

        status = i.verify_position(stock, quantity, True)
        print("angleone Position status : ", status)
        print("---------------------------------------------------------\n")

        status = i.verify_holding(stock, quantity)
        print("angleone holding status : ", status)
        print("---------------------------------------------------------\n")

        price = i.get_entry_exit_price(stock)
        print("angleone Entry Price : ", price)
        print("---------------------------------------------------------\n")

        price = i.get_entry_exit_price(stock, True)
        print("angleone Exit Price : ", price)
        print("---------------------------------------------------------\n")

    del obj_1
    del obj_2
    del obj_stub
    #######################################################################

    print("Done ...")
    end = time.time()
    print("T1 : {}".format(end))
    diff = end - start
    print("T: {} \n".format(time.strftime('%H:%M:%S', time.gmtime(diff))))

if __name__ == "__main__":
    main()
