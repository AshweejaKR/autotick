import sys, os
import time

main_path = 'C:/user/ashwee/autotick'
sys.path.append(main_path)
os.chdir(main_path)

from angleone_broker import *
from aliceblue_broker import *
from logger import *

def main():
    initialize_logger()
    print("Hello")
    start = time.time()
    print("T0 : {}".format(start))

    obj_1 = angleone()
    obj_2 = aliceblue()

    exchange = "NSE"
    stock = "INFY-EQ"
    datestamp = dt.date.today()
    duration = 10

    user_data = obj_1.get_user_data()
    print("angleone user data : ", user_data)
    print("---------------------------------------------------------\n")

    user_data = obj_2.get_user_data()
    print("aliceblue user data : ", user_data)
    print("---------------------------------------------------------\n")

    user_amt = obj_1.get_available_margin()
    print("angleone available margin : ", user_amt)
    print("---------------------------------------------------------\n")

    user_amt = obj_2.get_available_margin()
    print("aliceblue available margin : ", user_amt)
    print("---------------------------------------------------------\n")

    current_price = obj_1.get_current_price(stock, exchange)
    print("angleone current_price : ", current_price)
    print("---------------------------------------------------------\n")

    current_price = obj_2.get_current_price(stock, exchange)
    print("aliceblue current_price : ", current_price)
    print("---------------------------------------------------------\n")

    data1 = obj_1.hist_data_daily(stock, duration, exchange, datestamp)
    print("angleone data : ", data1)
    print("---------------------------------------------------------\n")

    data2 = obj_2.hist_data_daily(stock, duration, exchange, datestamp)
    print("aliceblue data : ", data2)
    print("---------------------------------------------------------\n")

    data3 = obj_1.hist_data_intraday(stock, exchange, datestamp)
    print("angleone data : ", data3)
    print("---------------------------------------------------------\n")

    data4 = obj_2.hist_data_intraday(stock, exchange, datestamp)
    print("aliceblue data : ", data4)
    print("---------------------------------------------------------\n")

    quantity = 1

    oid = obj_1.place_buy_order(stock, quantity, exchange)
    print("angleone Order ID : ", oid)
    print("---------------------------------------------------------\n")

    status = obj_1.get_oder_status(oid)
    print("angleone Order status : ", status)
    print("angleone Order status error : ", obj_1.error_msg)
    print("---------------------------------------------------------\n")

    oid = obj_2.place_buy_order(stock, quantity, exchange)
    print("aliceblue Order ID : ", oid)
    print("---------------------------------------------------------\n")

    status = obj_2.get_oder_status(oid)
    print("aliceblue Order status : ", status)
    print("aliceblue Order status error : ", obj_2.error_msg)
    print("---------------------------------------------------------\n")

    oid = obj_1.place_sell_order(stock, quantity, exchange)
    print("angleone Order ID : ", oid)
    print("---------------------------------------------------------\n")

    status = obj_1.get_oder_status(oid)
    print("angleone Order status : ", status)
    print("angleone Order status error : ", obj_1.error_msg)
    print("---------------------------------------------------------\n")

    oid = obj_2.place_sell_order(stock, quantity, exchange)
    print("aliceblue Order ID : ", oid)
    print("---------------------------------------------------------\n")

    status = obj_2.get_oder_status(oid)
    print("aliceblue Order status : ", status)
    print("aliceblue Order status error : ", obj_2.error_msg)
    print("---------------------------------------------------------\n")

    stock = "INFY-EQ"
    quantity = 1

    status = obj_1.verify_position(stock, quantity)
    print("angleone Position status : ", status)
    print("---------------------------------------------------------\n")

    status = obj_1.verify_position(stock, quantity, True)
    print("angleone Position status : ", status)
    print("---------------------------------------------------------\n")

    status = obj_1.verify_holding(stock, quantity)
    print("angleone holding status : ", status)
    print("---------------------------------------------------------\n")

    status = obj_2.verify_position(stock, quantity)
    print("aliceblue Position status : ", status)
    print("---------------------------------------------------------\n")

    status = obj_2.verify_position(stock, quantity, True)
    print("aliceblue Position status : ", status)
    print("---------------------------------------------------------\n")

    status = obj_2.verify_holding(stock, quantity)
    print("aliceblue holding status : ", status)
    print("---------------------------------------------------------\n")

    stock = "INFY-EQ"

    price = obj_1.get_entry_exit_price(stock)
    print("angleone Entry Price : ", price)
    print("---------------------------------------------------------\n")

    price = obj_1.get_entry_exit_price(stock, True)
    print("angleone Exit Price : ", price)
    print("---------------------------------------------------------\n")

    price = obj_2.get_entry_exit_price(stock)
    print("aliceblue Entry Price : ", price)
    print("---------------------------------------------------------\n")

    price = obj_2.get_entry_exit_price(stock, True)
    print("aliceblue Exit Price : ", price)
    print("---------------------------------------------------------\n")

    del obj_1
    del obj_2
    #######################################################################

    print("Done ...")
    end = time.time()
    print("T1 : {}".format(end))
    diff = end - start
    print("T: {} \n".format(time.strftime('%H:%M:%S', time.gmtime(diff))))

if __name__ == "__main__":
    main()
