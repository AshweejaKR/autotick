# -*- coding: utf-8 -*-
"""
Created on Fri Jun 21 23:34:15 2024

@author: ashwe
"""
from SmartApi import SmartConnect
from pyotp import TOTP

get_live_data = False

import pandas as pd
import datetime as dt
import time

from config import *
from utils import *

delay = 1.2

data_path = 'api_data/'
if not os.path.isdir(data_path):
    os.mkdir(data_path)
    get_live_data = True

class broker:
    def __init__(self):
        lg.info("broker class constructor called")
        send_to_telegram("broker class constructor called")
        
        self._instance = None
        logfile = 'logs/broker_api_log_' + '.txt'
        self.broker_api_log = open(logfile, 'w')
        self.broker_api_log.write("log file init\n")
        self.__login()
        self.instrument_list = load_instrument_list()
        self.__i = 0
        self.__ltp = 0.0
    
    def __del__(self):
        lg.info("broker class destructor called")
        send_to_telegram("broker class destructor called")
        self.__logout()
        self.broker_api_log.write("log file close\n")
        self.broker_api_log.flush()
        self.broker_api_log.close()
    
    def __get_hist(self, ticker, interval, fromdate, todate, exchange):
        params = {
            "exchange" : exchange,
            "symboltoken" : token_lookup(ticker, self.instrument_list, exchange),
            "interval" : interval,
            "fromdate" : fromdate,
            "todate" : todate
                    }
        try:
            self.__log_api_data(params)
            lg.debug(str((params)))
            json_path = data_path + "getCandleData.json"
            if get_live_data:
                time.sleep(delay)
                hist_data = self._instance.getCandleData(params)
                print(hist_data)
                write_to_json(hist_data, json_path)
            else:
                hist_data = read_from_json(json_path)
            self.__log_api_data(hist_data)
            lg.debug(str((hist_data)))
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            time.sleep(delay)
            hist_data = self.__get_hist(ticker, interval, fromdate, todate, exchange)
        return hist_data

    def __place_order(self, ticker, quantity, buy_sell, exchange):
        orderid = None

        try:
            params = {
                "variety" : "NORMAL",
                "tradingsymbol" : "{}".format(ticker),
                "symboltoken" : token_lookup(ticker, self.instrument_list, exchange),
                "transactiontype" : buy_sell,
                "exchange" : exchange,
                "ordertype" : "MARKET",
                "producttype" : "DELIVERY",
                "duration" : "DAY",
                "quantity" : quantity
            }

            try:
                self.__log_api_data(params)
                lg.debug(str((params)))
                json_path = data_path + "placeOrder.json"
                if get_live_data:
                    time.sleep(delay)
                    orderid = self._instance.placeOrder(params)
                    print(orderid)
                    write_to_json(orderid, json_path)
                else:
                    orderid = read_from_json(json_path)
                    if debug == 2:
                        try:
                            # stub buy orderID
                            if buy_sell == "BUY":
                                stub_file = "place_buy_order.txt"
                                data = read_stub_data(stub_file)
                                if data is not None:
                                    orderid = data[0]

                            # stub sell orderID
                            elif buy_sell == "SELL":
                                stub_file = "place_sell_order.txt"
                                data = read_stub_data(stub_file)
                                if data is not None:
                                    orderid = data[0]
                        except Exception: pass

                self.__log_api_data(orderid)
            except Exception as err:
                template = "An exception of type {0} occurred. error message:{1!r}"
                message = template.format(type(err).__name__, err.args)
                lg.error("{}".format(message))
                time.sleep(delay)
                orderid = self.__place_order(ticker, quantity, buy_sell, exchange)
            lg.info("{} orderid: {} for {}".format(buy_sell, orderid, ticker))
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            send_to_telegram(message)

        return orderid

    def __wait_till_order_fill(self, orderid):
        count = 0
        while self.get_oder_status(orderid) == 'open':
            lg.info('Buy order is in open, waiting ... %d ' % count)
            count = count + 1

    def __get_oder_status(self):
        try:
            json_path = data_path + "orderBook.json"
            if get_live_data:
                time.sleep(delay)
                order_history_response = self._instance.orderBook()
                print(order_history_response)
                write_to_json(order_history_response, json_path)
            else:
                order_history_response = read_from_json(json_path)
                if debug == 2:
                    try:
                        # stub order status
                        stub_file = "get_oder_status.txt"
                        data = read_stub_data(stub_file)
                        if data is not None:
                            for i in order_history_response['data']:
                                # for buy
                                if i['transactiontype'] == "BUY":
                                    i['status'] = data[0]

                                # for sell
                                elif i['transactiontype'] == "SELL":
                                    i['status'] = data[0]
                    except Exception: pass

                    # stub buy orderID
                    stub_file = "place_buy_order.txt"
                    data = read_stub_data(stub_file)
                    if data is not None:
                        for i in order_history_response['data']:
                            if i['transactiontype'] == "BUY":
                                i['orderid'] = data[0]

                    # stub sell orderID
                    stub_file = "place_sell_order.txt"
                    data = read_stub_data(stub_file)
                    if data is not None:
                        for i in order_history_response['data']:
                            if i['transactiontype'] == "SELL":
                                i['orderid'] = data[0]

            self.__log_api_data(order_history_response)
            lg.debug(str((order_history_response)))
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            time.sleep(delay)
            order_history_response = self.__get_oder_status()
        return order_history_response

    def __get_margin(self):
        try:
            json_path = data_path + "rmsLimit.json"
            if get_live_data:
                res = self._instance.rmsLimit()
                print(res)
                write_to_json(res, json_path)
            else:
                res = read_from_json(json_path)
                if debug == 2:
                    try:
                        # stub net amt
                        stub_file = "get_margin.txt"
                        data = read_stub_data(stub_file)
                        if data is not None:
                            res['data']['net'] = data[0]
                    except Exception: pass

            self.__log_api_data(res)
            lg.debug(str((res)))
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            time.sleep(delay)
            res = self.__get_margin()
        return res
    
    def __login(self):
        try:
            json_path = data_path + "generateSession.json"
            if get_live_data:
                self._instance = SmartConnect(API_KEY)
                totp = TOTP(TOTP_TOKEN).now()
                time.sleep(delay)
                data = self._instance.generateSession(CLIENT_ID, PASSWORD, totp)
                print(data)
                write_to_json(data, json_path)
            else:
                data = read_from_json(json_path)
            self.__log_api_data(data)
            lg.debug(str((data)))
            self.refreshToken = data['data']['refreshToken']
            if data['status'] and data['message'] == 'SUCCESS':
                lg.info('Login success ... !')
                send_to_telegram('Login success ... !')
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            time.sleep(5)
            self.__login()

    def __logout(self):
        try:
            json_path = data_path + "terminateSession.json"
            if get_live_data:
                time.sleep(delay)
                data = self._instance.terminateSession(CLIENT_ID)
                print(data)
                write_to_json(data, json_path)
            else:
                data = read_from_json(json_path)
            self.__log_api_data(data)
            lg.debug(str((data)))
            if data['status'] and data['message'] == 'SUCCESS':
                lg.info('Logout success ... !')
                send_to_telegram('Logout success ... !')
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            time.sleep(delay)
            self.__logout()

    def __get_positions(self):
        try:
            json_path = data_path + "position.json"
            if get_live_data:
                time.sleep(delay)
                position = self._instance.position()
                print(position)
                write_to_json(position, json_path)
            else:
                position = read_from_json(json_path)
                if debug == 2:
                    try:
                        stub_file = "get_entry_exit_price.txt"
                        data = read_stub_data(stub_file)
                        if data is not None:
                            for i in position['data']:
                                # stub entry price
                                # i['buyavgprice'] = data[0]
                                i['buyavgprice'] = self.read_dummy_ltp()
                                # stub exit price
                                # i['sellavgprice'] = data[1]
                                i['sellavgprice'] = self.read_dummy_ltp()
            
                        stub_file = "verify_position.txt"
                        data = read_stub_data(stub_file)
                        if data is not None:
                            for i in position['data']:
                                # stub symbol
                                i['tradingsymbol'] = data[0]
                                # stub qty
                                i['buyqty'] = data[1]
                                i['sellqty'] = data[1]
                    except Exception: pass

            self.__log_api_data(position)
            lg.debug(str((position)))
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            time.sleep(delay)
            position = self.__get_positions()
        
        return position
    
    def __get_holdings(self):
        try:
            json_path = data_path + "holding.json"
            if get_live_data:
                time.sleep(delay)
                holdings = self._instance.holding()
                print(holdings)
                write_to_json(holdings, json_path)
            else:
                holdings = read_from_json(json_path)
                if debug == 2:
                    try:
                        stub_file = "verify_holding.txt"
                        data = read_stub_data(stub_file)
                        if data is not None:
                            for i in holdings['data']:
                                # stub symbol
                                i['tradingsymbol'] = data[0]
                                # stub qty
                                i['quantity'] = data[1]
                    except Exception: pass

            self.__log_api_data(holdings)
            lg.debug(str((holdings)))
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            time.sleep(delay)
            holdings = self.__get_holdings()
        
        return holdings

    def __log_api_data(self, _msg):
        try:
            msg = str(_msg) + "\n"
            self.broker_api_log.write(msg)
        except Exception:
            pass

    def read_dummy_ltp(self):
        try:
            with open("../ltp.txt") as file:
                data = file.readlines()
                if self.__i > len(data) - 1:
                    self.__i = 0
                self.__ltp = float(data[self.__i])
                self.__i = self.__i + 1
        except Exception as err:
            print(err)
        return self.__ltp

###############################################################################
    def get_user_data(self):
        json_path = data_path + "getProfile.json"
        if get_live_data:
            res = self._instance.getProfile(self.refreshToken)
            print(res)
            write_to_json(res, json_path)
        else:
            res = read_from_json(json_path)
        self.__log_api_data(res)
        lg.debug(str((res)))
        return res

    def get_margin(self):
        res = self.__get_margin()
        lg.debug(res)
        margin = float(res['data']['net'])
        return margin

    def get_current_price(self, ticker, exchange):
        lg.debug("GETTING LTP DATA")
        try:
            json_path = data_path + "ltpData.json"
            if get_live_data:
                time.sleep(delay)
                data = self._instance.ltpData(exchange=exchange, tradingsymbol=ticker, symboltoken=token_lookup(ticker, self.instrument_list, exchange))
                print(data)
                write_to_json(data, json_path)
            else:
                data = read_from_json(json_path)
                if debug == 2:
                    try:
                        new_ltp = self.read_dummy_ltp()
                        data['data']['ltp'] = new_ltp
                    except Exception: pass
            self.__log_api_data(data)
            lg.debug(str((data)))
            ltp = float(data['data']['ltp'])
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            time.sleep(delay)
            ltp = self.get_current_price(ticker, exchange)
        lg.debug("GETTING LTP DATA: DONE")
        return ltp

    def hist_data_daily(self, ticker, duration, exchange):
        interval = "ONE_DAY"
        fromdate = (dt.date.today() - dt.timedelta(duration)).strftime('%Y-%m-%d %H:%M')
        todate = dt.date.today().strftime('%Y-%m-%d %H:%M')
        hist_data = self.__get_hist(ticker, interval, fromdate, todate, exchange)
        df_data = pd.DataFrame(hist_data["data"],
                               columns=["date", "open", "high", "low", "close", "volume"])
        df_data.set_index("date", inplace=True)
        df_data.index = pd.to_datetime(df_data.index)
        df_data.index = df_data.index.tz_localize(None)
        return df_data

    def hist_data_intraday(self, ticker, exchange, datestamp=dt.date.today()):
        interval = 'FIVE_MINUTE'
        fromdate = datestamp.strftime("%Y-%m-%d")+ " 09:15"
        todate = datestamp.strftime("%Y-%m-%d") + " 15:30" 
        hist_data = self.__get_hist(ticker, interval, fromdate, todate, exchange)
        df_data = pd.DataFrame(hist_data["data"],
                               columns = ["date", "open", "high", "low", "close", "volume"])
        df_data.set_index("date",inplace=True)
        df_data.index = pd.to_datetime(df_data.index)
        df_data.index = df_data.index.tz_localize(None)
        return df_data

    def place_buy_order(self, ticker, quantity, exchange):
        buy_sell = "BUY"
        orderid = self.__place_order(ticker, quantity, buy_sell, exchange)
        self.__wait_till_order_fill(orderid)
        return orderid

    def place_sell_order(self, ticker, quantity, exchange):
        buy_sell = "SELL"
        orderid = self.__place_order(ticker, quantity, buy_sell, exchange)
        self.__wait_till_order_fill(orderid)
        return orderid

    def get_oder_status(self, orderid):
        order_history_response = self.__get_oder_status()
        status = "NA"

        try:
            for i in order_history_response['data']:
                if i['orderid'] == orderid:
                    status = i['status']  # complete/rejected/open/cancelled
                    break
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            send_to_telegram(message)

        return status

    def verify_position(self, sym, qty, exit=False):
        res_positions = self.__get_positions()
        try:
            for i in res_positions['data']:
                if exit:
                    if i['tradingsymbol'] == sym and int(i['sellqty']) == qty:
                        return True
                    else:
                        return False
                else:
                    if i['tradingsymbol'] == sym and int(i['buyqty']) == qty:
                        return True
                    else:
                        return False

        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            return False

    def verify_holding(self, sym, qty):
        res_holdings = self.__get_holdings()
        try:
            for i in res_holdings['data']:    
                if i['tradingsymbol'] == sym and int(i['quantity']) == qty:
                    return True
                else:
                    return False

        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            return False

    def get_entry_exit_price(self, sym, exit=False):
        res_positions = self.__get_positions()
        price = 0.0
        try:
            for i in res_positions['data']:
                if i['tradingsymbol'] == sym:
                    if exit:
                        price = float(i['sellavgprice'])
                    else:
                        price = float(i['buyavgprice'])

        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
        return price
