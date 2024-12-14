# -*- coding: utf-8 -*-
"""
Created on Sat Nov 30 18:21:09 2024

@author: ashwe
"""

import time

from broker import *
from utils import *

import gvars

###############################################################################
###################### dummy var ##############################################
###############################################################################

class autotick:
    def __init__(self, ticker, exchange, mode, datestamp=dt.date.today()):
        lg.info("autotick class constructor called")
        self.name = "autotick"
        self.mode = mode
        self.current_trade = "NA"
        self.ticker = ticker
        self.interval = 1
        self.exchange = exchange
        self.obj = broker(self.ticker, self.name, self.mode, datestamp)
        self.quantity = None
        self.entry_price = None
        self.takeprofit_price = None
        self.stoploss_price = None
        self.trigger_price = None
        self.stoploss_p = 0.05
        self.target_p = 0.1
        self.trailSL = False
        self.capital_per_trade = 1000.00

        if self.mode.value == 3:
            self.interval = 0.001

    def __del__(self):
        lg.info("autotick class destructor called")

    def __set_stoploss(self):
        self.stoploss_price = self.entry_price - (self.entry_price * self.stoploss_p)

    def __set_takeprofit(self):
        self.takeprofit_price = self.entry_price + (self.entry_price * self.target_p)
        self.trigger_price = self.entry_price + (self.entry_price * self.target_p * 1.5)

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

    def trail_SL(self, stoploss, trigger, cur_price, trail_percent):
        print("Trailing the SL ...")

        lg.info("cur_price : {} ".format(cur_price))
        lg.info("trigger : {} ".format(trigger))
        lg.info("Stoploss : {} ".format(stoploss))
        lg.info("trail_percent : {} ".format(trail_percent))

        if cur_price > trigger:
            new_stoploss = cur_price * (1 - trail_percent / 100)
            lg.info("new_stoploss : {} ".format(new_stoploss))

            # Only update the stoploss if the new stoploss is greater than the current one
            if new_stoploss > stoploss:
                self.stoploss_price = new_stoploss
                print(f"Stoploss updated to: {self.stoploss_price}")
                save_positions(self.ticker, self.quantity, self.current_trade, self.entry_price, self.stoploss_price, self.takeprofit_price)
            else:
                print(f"Stoploss remains unchanged: {self.stoploss_price}")

    def __get_cur_price(self):
        cp = self.obj.get_current_price(self.ticker, self.exchange)
        return cp

    def __load_positions(self):
        data = load_positions(self.ticker)
        if data is not None:
            try:
                if self.ticker == data['ticker']:
                    self.quantity = data['quantity']
                    res = self.obj.verify_holding(self.ticker, self.quantity)

                    if res:
                        self.current_trade = data['order_type']
                        self.entry_price = data['entryprice']
                        self.stoploss_price = data['stoploss']
                        self.takeprofit_price = data['takeprofit']
                        self.trigger_price = self.entry_price + (self.entry_price * self.target_p * 1.5)

            except Exception as err:
                template = "An exception of type {0} occurred. error message:{1!r}"
                message = template.format(type(err).__name__, err.args)
                lg.error("ERROR: {}".format(message))

    def init_strategy(self):
        self.init_1()

    def run_strategy(self):
        self.init_strategy()
        wait_till_market_open(self.mode)
        self.__load_positions()

        while is_market_open(self.mode):
            try:
                lg.info("Running Trade For {} ... {} ".format(self.ticker, gvars.i))
                self.__load_positions()
                cur_price = self.__get_cur_price()
                ret = "NA"
                if self.current_trade == "NA":
                    ret = self.strategy(cur_price)

                if self.current_trade == "BUY":
                    if self.trailSL:
                        tsl_change = self.trail_SL(self.stoploss_price, self.trigger_price, cur_price, 10)
                    lg.info('SL %.2f <-- %.2f --> %.2f TP' % (self.stoploss_price, cur_price, self.takeprofit_price))

                if self.current_trade == "NA" and (ret == "BUY"):
                    lg.info("Entering Trade")
                    amt = self.obj.get_trade_margin()
                    lg.info("cash available: {} ".format(amt))
                    amt_for_trade = min(amt, self.capital_per_trade)
                    lg.info("cash using for trade: {} ".format(amt_for_trade))
                    self.quantity = int(amt_for_trade / cur_price)
                    lg.info("quantity: {} ".format(self.quantity))
                    status = self.obj.place_buy_order(self.ticker, self.quantity, self.exchange)
                    lg.info("status: {} ".format(status))
                    if status:
                        res = self.obj.verify_position(self.ticker, self.quantity)
                        self.entry_price = self.obj.get_entry_exit_price(self.ticker)
                        self.__set_stoploss()
                        self.__set_takeprofit()
                        self.current_trade = "BUY"
                        save_positions(self.ticker, self.quantity, self.current_trade, self.entry_price, self.stoploss_price, self.takeprofit_price)
                        save_trade_in_csv(self.ticker, self.quantity, "BUY", self.entry_price)
                        lg.info('Submitted {} Order for {}, Qty = {} at price: {}'.format("BUY",
                                                                                            self.ticker,
                                                                                            self.quantity,
                                                                                            self.entry_price))

                elif (self.current_trade == "BUY") and (ret == "SELL"):
                    lg.info("Exiting Trade")
                    status = self.obj.place_sell_order(self.ticker, self.quantity, self.exchange)
                    lg.info("status: {} ".format(status))
                    if status:
                        res = self.obj.verify_position(self.ticker, self.quantity)
                        exit_price = self.obj.get_entry_exit_price(self.ticker, True)
                        self.current_trade = "NA"
                        remove_positions(self.ticker)
                        save_trade_in_csv(self.ticker, self.quantity, "SELL", exit_price)
                        lg.info('Submitted {} Order for {}, Qty = {} at price: {}'.format("SELL",
                                                                                            self.ticker,
                                                                                            self.quantity,
                                                                                            exit_price))

                elif (self.current_trade == "BUY") and (cur_price > self.takeprofit_price) and not self.trailSL:
                    lg.info("Exiting Trade")
                    status = self.obj.place_sell_order(self.ticker, self.quantity, self.exchange)
                    lg.info("status: {} ".format(status))
                    if status:
                        res = self.obj.verify_position(self.ticker, self.quantity)
                        exit_price = self.obj.get_entry_exit_price(self.ticker, True)
                        self.current_trade = "NA"
                        remove_positions(self.ticker)
                        save_trade_in_csv(self.ticker, self.quantity, "SELL", exit_price)
                        lg.info('Submitted {} Order for {}, Qty = {} at price: {}'.format("SELL",
                                                                                            self.ticker,
                                                                                            self.quantity,
                                                                                            exit_price))

                elif (self.current_trade == "BUY") and (cur_price < self.stoploss_price):
                    lg.info("Exiting Trade")
                    status = self.obj.place_sell_order(self.ticker, self.quantity, self.exchange)
                    lg.info("status: {} ".format(status))
                    if status:
                        res = self.obj.verify_position(self.ticker, self.quantity)
                        exit_price = self.obj.get_entry_exit_price(self.ticker, True)
                        self.current_trade = "NA"
                        remove_positions(self.ticker)
                        save_trade_in_csv(self.ticker, self.quantity, "SELL", exit_price)
                        lg.info('Submitted {} Order for {}, Qty = {} at price: {}'.format("SELL",
                                                                                            self.ticker,
                                                                                            self.quantity,
                                                                                            exit_price))

                lg.info("------------------------------------------------------\n")
                time.sleep(self.interval)

            except KeyboardInterrupt:
                lg.error("Bot stop request by user")
                break

            except Exception as err:
                template = "An exception of type {0} occurred. error message:{1!r}"
                message = template.format(type(err).__name__, err.args)
                lg.error("{}".format(message))
                break

###############################################################################
###################### dummy Init fun #########################################
    def init_1(self):
        try:
            hist_data = self.obj.hist_data_daily(self.ticker, 3, self.exchange)
            print(hist_data)
            self.prev_high = hist_data['High'].iloc[1]
            self.prev_low = hist_data['Low'].iloc[1]
        except Exception as err: lg.error("{}".format(err))

###############################################################################

########################### dummy strategy ####################################
    def strategy(self, cur_price):
        lg.info("current price: {} < prev high: {}".format(cur_price, self.prev_high))
        if cur_price < self.prev_high:
            return "BUY"
        else:
            return "NA"
###############################################################################
###############################################################################
