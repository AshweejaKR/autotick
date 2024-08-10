# -*- coding: utf-8 -*-
"""
Created on Fri Jun 21 20:52:24 2024

@author: ashwe
"""

import time

from broker import *
# from broker_stub import *

class autotick:
    def __init__(self, ticker, exchange):
        lg.info("autotick class constructor called")
        send_to_telegram("autotick class constructor called")
        self.name = "autotick"
        self.interval = 1
        self.trade = "NA"
        self.quantity = 0
        self.entry_price = 0.0
        self.exit_price = 0.0
        self.stoploss_p = 1.0
        self.target_p = 2.0
        self.ticker = ticker
        self.exchange = exchange
        self.obj = broker()
        self.PosOn = False
        
        stock_data = self.obj.hist_data_daily(ticker, 4, self.exchange)
        self.prev_high = max(stock_data.iloc[-1]['high'], stock_data.iloc[-2]['high'])
        self.prev_low = min(stock_data.iloc[-1]['low'], stock_data.iloc[-2]['low'])
        ltp = 0.0
        while ltp <= 1.0:
            ltp = self.obj.get_current_price(self.ticker, self.exchange)
        lg.info("prev high: {}, prev low: {}, current price: {}".format(self.prev_high, self.prev_low, ltp))
        send_to_telegram("prev high: {}, prev low: {}, current price: {}".format(self.prev_high, self.prev_low, ltp))
        
        data = load_positions(self.ticker)
        if data is not None:
            try:
                if ticker == data['ticker']:
                    self.quantity = data['quantity']
                    res = self.obj.verify_holding(ticker, self.quantity)
                    lg.debug("verify_holding: {} ".format(str(res)))

                    if res:
                        self.trade = data['order_type']
                        self.entry_price = data['entryprice']
                        self.PosOn = True

            except Exception as err:
                template = "An exception of type {0} occurred. error message:{1!r}"
                message = template.format(type(err).__name__, err.args)
                lg.error("ERROR: {}".format(message))
                send_to_telegram(message)

    def __del__(self):
        lg.info("autotick class destructor called")
        send_to_telegram("autotick class destructor called")

    def __set_stoploss(self, entryprice, trend="long"):
        stoploss = entryprice - (entryprice * self.stoploss_p)
        return stoploss

    def __set_takeprofit(self, entryprice, trend="long"):
        takeprofit = entryprice + (entryprice * self.target_p)
        return takeprofit

    def __get_cur_price(self):
        c = self.obj.get_current_price(self.ticker, self.exchange)
        return c

###############################################################################

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

    def run(self):
        takeprofit = self.__set_takeprofit(self.entry_price)
        stoploss = self.__set_stoploss(self.entry_price)
        lg.info("takeprofit : {} ".format(takeprofit))
        lg.info("stoploss : {} ".format(stoploss))
        wait_till_market_open()
        try:
            global start_time, current_time
            start_time = time.time()
            while is_market_open():
                current_time = time.time()

                ret = self.strategy(self.PosOn)
                cur_price = self.__get_cur_price()
                
                if self.trade == "BUY":
                    lg.info('SL %.2f <-- %.2f --> %.2f TP' % (stoploss, cur_price, takeprofit))
                    if (current_time - start_time) >= 300:
                        send_to_telegram('SL %.2f <-- %.2f --> %.2f TP' % (stoploss, cur_price, takeprofit))

                if (self.trade == "NA") and (ret == "BUY"):
                    lg.info("\n*************** Entering Trade ********************\n")
                    # self.entry_price = self.__get_cur_price()
                    takeprofit = self.__set_takeprofit(self.entry_price)
                    stoploss = self.__set_stoploss(self.entry_price)
                    amt = self.obj.get_margin()
                    lg.info("cash available: {} ".format(amt))
                    self.quantity = int(amt / cur_price)
                    lg.info("quantity: {} ".format(self.quantity))
                    orderid = self.obj.place_buy_order(self.ticker, self.quantity, self.exchange)
                    lg.info("orderid: {} ".format(orderid))
                    status = self.obj.get_oder_status(orderid)
                    lg.info("status: {} ".format(status))
                    if status == 'complete':
                        lg.info('Submitting {} Order for {}, Qty = {} at price: {}'.format("BUY",
                                                                                               self.ticker,
                                                                                               self.quantity,
                                                                                               cur_price))
                        send_to_telegram('Submitting {} Order for {}, Qty = {} at price: {}'.format("BUY",
                                                                                               self.ticker,
                                                                                               self.quantity,
                                                                                               cur_price))
                        res = self.obj.verify_position(self.ticker, self.quantity)
                        self.entry_price = self.obj.get_entry_exit_price(self.ticker)
                        lg.debug("verify_position: {} ".format(str(res)))
                        self.trade = "BUY"
                        self.PosOn = True
                        save_positions(self.ticker, self.quantity, self.trade, self.entry_price)
                        save_trade_in_csv(self.ticker, self.quantity, "BUY", self.entry_price)

                elif (self.trade == "BUY") and (ret == "SELL"):
                    lg.info("\n*************** Exiting Trade ********************\n")
                    orderid = self.obj.place_sell_order(self.ticker, self.quantity, self.exchange)
                    lg.info("orderid: {} ".format(orderid))
                    status = self.obj.get_oder_status(orderid)
                    lg.info("status: {} ".format(status))
                    if status == 'complete':
                        lg.info('Submitting {} Order for {}, Qty = {} at price: {}'.format("SELL",
                                                                                               self.ticker,
                                                                                               self.quantity,
                                                                                               cur_price))
                        send_to_telegram('Submitting {} Order for {}, Qty = {} at price: {}'.format("SELL",
                                                                                               self.ticker,
                                                                                               self.quantity,
                                                                                               cur_price))
                        res = self.obj.verify_position(self.ticker, self.quantity)
                        self.exit_price = self.obj.get_entry_exit_price(self.ticker, True)
                        lg.debug("verify_position: {} ".format(str(res)))
                        self.trade = "NA"
                        self.PosOn = False
                        remove_positions(self.ticker)
                        save_trade_in_csv(self.ticker, self.quantity, "SELL", self.exit_price)

                elif (self.trade == "BUY") and (cur_price > takeprofit):
                    lg.info("\n*************** Exiting Trade ********************\n")
                    orderid = self.obj.place_sell_order(self.ticker, self.quantity, self.exchange)
                    lg.info("orderid: {} ".format(orderid))
                    status = self.obj.get_oder_status(orderid)
                    lg.info("status: {} ".format(status))
                    if status == 'complete':
                        lg.info('Submitting {} Order for {}, Qty = {} at price: {}'.format("SELL",
                                                                                               self.ticker,
                                                                                               self.quantity,
                                                                                               cur_price))
                        send_to_telegram('Submitting {} Order for {}, Qty = {} at price: {}'.format("SELL",
                                                                                               self.ticker,
                                                                                               self.quantity,
                                                                                               cur_price))
                        res = self.obj.verify_position(self.ticker, self.quantity)
                        self.exit_price = self.obj.get_entry_exit_price(self.ticker, True)
                        lg.debug("verify_position: {} ".format(str(res)))
                        self.trade = "NA"
                        self.PosOn = False
                        remove_positions(self.ticker)
                        save_trade_in_csv(self.ticker, self.quantity, "SELL", self.exit_price)

                elif (self.trade == "BUY") and (cur_price < stoploss):
                    lg.info("\n*************** Exiting Trade ********************\n")
                    orderid = self.obj.place_sell_order(self.ticker, self.quantity, self.exchange)
                    lg.info("orderid: {} ".format(orderid))
                    status = self.obj.get_oder_status(orderid)
                    lg.info("status: {} ".format(status))
                    if status == 'complete':
                        lg.info('Submitting {} Order for {}, Qty = {} at price: {}'.format("SELL",
                                                                                               self.ticker,
                                                                                               self.quantity,
                                                                                               cur_price))
                        send_to_telegram('Submitting {} Order for {}, Qty = {} at price: {}'.format("SELL",
                                                                                               self.ticker,
                                                                                               self.quantity,
                                                                                               cur_price))
                        res = self.obj.verify_position(self.ticker, self.quantity)
                        self.exit_price = self.obj.get_entry_exit_price(self.ticker, True)
                        lg.debug("verify_position: {} ".format(str(res)))
                        self.trade = "NA"
                        self.PosOn = False
                        remove_positions(self.ticker)
                        save_trade_in_csv(self.ticker, self.quantity, "SELL", self.exit_price)

                else:
                    if (current_time - start_time) >= 300:
                        lg.info("Doing nothing")

                time.sleep(self.interval)
                if (current_time - start_time) >= 300:
                    start_time = current_time

        except KeyboardInterrupt:
            lg.error("Bot stop request by user")
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            send_to_telegram(message)

    def strategy(self, ison):
        buy_p = 0.995

        if not ison:
            cur_price = self.__get_cur_price()
            lg.info("current price: {} < prev high: {}".format(cur_price, (buy_p * self.prev_high)))
            if (current_time - start_time) >= 300:
                send_to_telegram("current price: {} < prev high: {}".format(cur_price, (buy_p * self.prev_high)))
            if cur_price < (buy_p * self.prev_high):
                return "BUY"
            else:
                return "NA"
        else:
            return "NA"
