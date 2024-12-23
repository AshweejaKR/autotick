# -*- coding: utf-8 -*-
"""
Created on Sat Nov 30 18:21:09 2024

@author: ashwe
"""

import time

from angleone_broker import *
from aliceblue_broker import *
# from broker import *
from utils import *

import gvars

global no_of_order_placed
no_of_order_placed = 0

def KillSwitch():
    global no_of_order_placed
    if no_of_order_placed > 5:
        lg.error("Kill Switch Activated!!")
        lg.error("Stopping the Trading Bot")
        sys.exit(-1)

class autotick:
    def __init__(self, ticker, exchange, mode, datestamp):
        self.ticker = ticker
        self.exchange = exchange
        self.mode = mode
        self.datestamp = datestamp
        self.interval = 10
        self.stoploss_p = 0.1
        self.target_p = 0.0005
        self.capital_per_trade = 10000.00
        self.current_trade = "NA"
        self.trailSL = False
        self.obj = angleone()
        # self.obj = aliceblue()

        cur_price = self.obj.get_current_price(self.ticker, self.exchange)
        while cur_price is None:
            cur_price = self.obj.get_current_price(self.ticker, self.exchange)
            lg.info(f"Checking current_price : {cur_price}")
            time.sleep(1)

        lg.info(f"Initialized autotick Trading Bot for Stock {self.ticker} in {exchange} exchange, running on {self.datestamp}")
    
    def __del__(self):
        pass

    def __load_positions(self):
        data = load_positions(self.ticker)
        if data is not None:
            try:
                if self.ticker == data['ticker']:
                    self.quantity = data['quantity']
                    res_h = self.obj.verify_holding(self.ticker, self.quantity)
                    res_p = self.obj.verify_position(self.ticker, self.quantity)

                    if res_h or res_p:
                        self.current_trade = data['order_type']
                        self.entry_price = data['entryprice']
                        self.stoploss_price = data['stoploss']
                        self.takeprofit_price = data['takeprofit']
                        self.trigger_price = self.entry_price + (self.entry_price * self.target_p * 1.5)

            except Exception as err:
                template = "An exception of type {0} occurred. error message:{1!r}"
                message = template.format(type(err).__name__, err.args)
                lg.info("ERROR: {}".format(message))

    def __wait_till_order_fill(self, orderid, order):
        count = 0
        lg.info('%s order is in open, waiting ... %d ' % (order, count))
        while self.obj.get_oder_status(orderid) == 'open':
            lg.info('%s order is in open, waiting ... %d ' % (order, count))
            count = count + 1

    def set_stoploss(self, sl_p):
        if sl_p < 1:
            self.stoploss_p = sl_p
        else:
            self.stoploss_p = sl_p / 100.00

    def set_takeprofit(self, tp_p):
        if tp_p < 1:
            self.target_p = tp_p
        else:
            self.target_p = tp_p / 100.00

    def run_trade(self):
        global no_of_order_placed
        self.init_strategy()
        wait_till_market_open(self.mode)
        self.__load_positions()
        res = "NA"

        while is_market_open(self.mode):
            start_time = time.time()
            try:
                KillSwitch()
                lg.info("Running Trade For {} ... ".format(self.ticker))
                cur_price = self.obj.get_current_price(self.ticker, self.exchange)
                if self.current_trade != "BUY":
                    res = self.run_strategy(cur_price)

                if self.current_trade == "BUY":
                    if self.trailSL:
                        tsl_change = self.trail_SL(self.stoploss_price, self.trigger_price, cur_price, 10)
                    lg.info('SL %.2f <-- %.2f --> %.2f TP' % (self.stoploss_price, cur_price, self.takeprofit_price))

                # x = input("debug stop")
                if self.current_trade != "BUY" and (res == "BUY"):
                    order_type = "BUY"
                    lg.info("Entering Trade")
                    amt = self.obj.get_available_margin()
                    lg.info("cash available: {} ".format(amt))
                    amt_for_trade = min(amt, self.capital_per_trade)
                    lg.info("cash using for trade: {} ".format(amt_for_trade))
                    self.quantity = int(amt_for_trade / cur_price)
                    lg.info("quantity: {} ".format(self.quantity))
                    if self.quantity > 0:
                        orderid = self.obj.place_buy_order(self.ticker, self.quantity, self.exchange)
                        no_of_order_placed = no_of_order_placed + 1
                        if orderid is not None:
                            self.__wait_till_order_fill(orderid, order_type)
                            status = self.obj.get_oder_status(orderid)
                            lg.info("{} Order status: {} ".format(order_type, status))
                            if status == 'complete':
                                x = self.obj.verify_position(self.ticker, self.quantity)
                                lg.info("Entered into Position Mode : ".format(x))
                                self.entry_price = self.obj.get_entry_exit_price(self.ticker)
                                self.stoploss_price = self.entry_price - (self.entry_price * self.stoploss_p)
                                self.takeprofit_price = self.entry_price + (self.entry_price * self.target_p)
                                self.trigger_price = self.entry_price + (self.entry_price * self.target_p * 1.5)
                                self.current_trade = order_type
                                save_positions(self.ticker, self.quantity, self.current_trade, self.entry_price, self.stoploss_price, self.takeprofit_price)
                                save_trade_in_csv(self.ticker, self.quantity, order_type, self.entry_price, self.datestamp)
                                lg.info('Submitted {} Order for {}, Qty = {} at price: {}'.format(order_type,
                                                                                                self.ticker,
                                                                                                self.quantity,
                                                                                                self.entry_price))
                            else:
                                lg.error('Failed to Submit {} Order for {}, Reason : {} '.format(order_type,
                                                                                                self.ticker,
                                                                                                self.obj.error_msg))
                        else:
                            lg.error("Order ID is NONE")
                    else:
                        lg.error("Insufficient funds")

                elif (self.current_trade == "BUY") and (res == "SELL"):
                    order_type = "SELL"
                    lg.info("Exiting Trade")
                    orderid = self.obj.place_sell_order(self.ticker, self.quantity, self.exchange)
                    no_of_order_placed = no_of_order_placed + 1
                    if orderid is not None:
                        self.__wait_till_order_fill(orderid, order_type)
                        status = self.obj.get_oder_status(orderid)
                        lg.info("{} Order status: {} ".format(order_type, status))
                        if status == 'complete':
                            x = self.obj.verify_position(self.ticker, self.quantity)
                            exit_price = self.obj.get_entry_exit_price(self.ticker)
                            self.current_trade = order_type
                            remove_positions(self.ticker)
                            save_trade_in_csv(self.ticker, self.quantity, order_type, exit_price, self.datestamp)
                            lg.info('Submitted {} Order for {}, Qty = {} at price: {}'.format(order_type,
                                                                                            self.ticker,
                                                                                            self.quantity,
                                                                                            exit_price))
                        else:
                            lg.error('Failed to Submit {} Order for {}, Reason : {} '.format(order_type,
                                                                                            self.ticker,
                                                                                            self.obj.error_msg))
                    else:
                        lg.error("Order ID is NONE")

                elif (self.current_trade == "BUY"):
                    if (cur_price > self.takeprofit_price) or (cur_price < self.stoploss_price):
                        order_type = "SELL"
                        lg.info("Exiting Trade")
                        orderid = self.obj.place_sell_order(self.ticker, self.quantity, self.exchange)
                        no_of_order_placed = no_of_order_placed + 1
                        if orderid is not None:
                            self.__wait_till_order_fill(orderid, order_type)
                            status = self.obj.get_oder_status(orderid)
                            lg.info("{} Order status: {} ".format(order_type, status))
                            if status == 'complete':
                                x = self.obj.verify_position(self.ticker, self.quantity)
                                exit_price = self.obj.get_entry_exit_price(self.ticker)
                                self.current_trade = order_type
                                remove_positions(self.ticker)
                                save_trade_in_csv(self.ticker, self.quantity, order_type, exit_price, self.datestamp)
                                lg.info('Submitted {} Order for {}, Qty = {} at price: {}'.format(order_type,
                                                                                                self.ticker,
                                                                                                self.quantity,
                                                                                                self.entry_price))
                            else:
                                lg.error('Failed to Submit {} Order for {}, Reason : {} '.format(order_type,
                                                                                                self.ticker,
                                                                                                self.obj.error_msg))
                        else:
                            lg.error("Order ID is NONE")

                lg.info("------------------------------------------------------\n")
                end_time = time.time()
                taken_time = end_time - start_time
                if self.interval - taken_time > 0:
                    taken_time = self.interval - taken_time
                else:
                    taken_time = self.interval
                time.sleep(taken_time)

            except KeyboardInterrupt:
                lg.error("Bot stop request by user")
                break

            except Exception as err:
                template = "An exception of type {0} occurred. error message:{1!r}"
                message = template.format(type(err).__name__, err.args)
                lg.error("{}".format(message))
                break

###############################################################################
    def init_strategy(self):
        try:
            hist_data = self.obj.hist_data_daily(self.ticker, 8, self.exchange, self.datestamp)
            self.prev_high = hist_data['High'].iloc[1]
            self.prev_low = hist_data['Low'].iloc[1]
            lg.info(f"High : {self.prev_high}, Low : {self.prev_low}")
        except Exception as err: lg.info("init_strategy Error: {}".format(err))

    def run_strategy(self, cur_price):
        buy_p = 0.999

        lg.info("current price: {} < prev high: {} \n".format(cur_price, (buy_p * self.prev_high)))
        if cur_price < (buy_p * self.prev_high):
            return "BUY"
        else:
            return "NA"
###############################################################################
