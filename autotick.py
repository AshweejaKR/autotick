# -*- coding: utf-8 -*-
"""
Created on Fri Jun 21 20:52:24 2024

@author: ashwe
"""

tel_time = 300

import time

from broker import *
if debug:
    from broker_stub import *

class autotick:
    def __init__(self, ticker, exchange):
        lg.info("autotick class constructor called")
        send_to_telegram("autotick class constructor called")
        self.name = "autotick"
        self.interval = 1
        self.trade = "NA"
        self.quantity = 0
        self.entry_price = 0.0
        self.target_price = 9999.99
        self.stoploss_price = 0.0
        self.exit_price = 0.0
        self.stoploss_p = 1.0
        self.target_p = 2.0
        self.ticker = ticker
        self.exchange = exchange
        self.obj = broker()
        self.PosOn = True
        self.Pos_count = 0
        self.Pos_max_count = 2 # set through config file
        self.capital_per_trade = 5000.00 # set through config file
        
        ############## Init call ######################################################
        stock_data = self.obj.hist_data_daily(ticker, 4, self.exchange)
        self.prev_high = max(stock_data.iloc[-1]['high'], stock_data.iloc[-2]['high'])
        self.prev_low = min(stock_data.iloc[-1]['low'], stock_data.iloc[-2]['low'])
        ###############################################################################

        ltp = 0.0
        while ltp <= 1.0:
            ltp = self.obj.get_current_price(self.ticker, self.exchange)
        lg.info("prev high: {}, prev low: {}, current price: {}".format(self.prev_high, self.prev_low, ltp))
        send_to_telegram("prev high: {}, prev low: {}, current price: {}".format(self.prev_high, self.prev_low, ltp))

        self.__load_positions()

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

    def __load_positions(self):
        self.Pos_count = load_trade_itr(self.ticker)
        lg.info("Trade Count: {}".format(self.Pos_count))
        load_ticker = self.ticker + "_" + str(self.Pos_count)
        data = load_positions(load_ticker)
        if data is not None:
            try:
                if self.ticker == data['ticker']:
                    self.quantity = data['quantity']
                    res = self.obj.verify_holding(self.ticker, self.quantity)
                    lg.debug("verify_holding: {} ".format(str(res)))

                    if debug:
                        res = True

                    if res:
                        self.trade = data['order_type']
                        self.entry_price = data['entryprice']
                        self.stoploss_price = data['stoploss']
                        self.target_price = data['takeprofit']

            except Exception as err:
                template = "An exception of type {0} occurred. error message:{1!r}"
                message = template.format(type(err).__name__, err.args)
                lg.error("ERROR: {}".format(message))
                send_to_telegram(message)

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

    def trail_SL(self, stoploss, trigger, cur_price, trail_percent):
        print("Trailing the SL ...")
        
        lg.info("cur_price : {} ".format(cur_price))
        lg.info("trigger : {} ".format(trigger))
        lg.info("Stoploss : {} ".format(stoploss))
        lg.info("trail_percent : {} ".format(trail_percent))
    
        # If the current price is above the trigger point, adjust the stoploss
        if cur_price > trigger:
            # new target price
            new_stoploss = cur_price * (1 - trail_percent / 100)
            new_target = self.__set_takeprofit(cur_price)
        
            lg.info("new_stoploss : {} ".format(new_stoploss))
        
            # Only update the stoploss if the new stoploss is greater than the current one
            if new_stoploss > stoploss:
                stoploss = new_stoploss
                print(f"Stoploss updated to: {stoploss}")
            else:
                print(f"Stoploss remains unchanged: {stoploss}")

            if new_target > self.target_price:
                self.target_price = new_target
        
        else:
            print(f"Current price {cur_price} has not reached trigger {trigger}. Stoploss remains at {stoploss}")

        self.stoploss_price = stoploss
        return stoploss

    def run(self):
        takeprofit = self.target_price
        stoploss = self.stoploss_price
        lg.info("Ticker Name : {} ".format(self.ticker))
        lg.info("Entry Price : {} ".format(self.entry_price))
        lg.info("Quantity : {} ".format(self.quantity))
        lg.info("Target Price : {} ".format(takeprofit))
        lg.info("Stoploss Price : {} ".format(stoploss))
        lg.info("Iteration Count : {} ".format(self.Pos_count))
        wait_till_market_open()

        message = "Running Trade For {}, Itr Count : {}".format(self.ticker, self.Pos_count)
        send_to_telegram(message)
        lg.info(message)

        try:
            global start_time, current_time
            start_time = time.time()
            while is_market_open():
                lg.info("Running Trade For {}, {}".format(self.ticker, self.Pos_count))
                current_time = time.time()

                if (current_time - start_time) >= tel_time:
                    message = "Running Trade For {}, Itr Count : {}".format(self.ticker, self.Pos_count)
                    send_to_telegram(message)

                if self.Pos_count > self.Pos_max_count:
                    self.PosOn = False
                else:
                    self.PosOn = True

                if self.Pos_count > 0:
                    self.trade = "BUY"
                else:
                    self.trade = "NA"

                self.__load_positions()

                ret = "NA"
                if self.PosOn:
                    ret = self.strategy()
                cur_price = self.__get_cur_price()

                if self.trade == "BUY":
                    trail_percent = 1
                    trigger = self.__set_takeprofit(self.entry_price)
                    self.trail_SL(stoploss, trigger, cur_price, trail_percent)
                    takeprofit = self.target_price
                    stoploss = self.stoploss_price

                if self.trade == "BUY":
                    lg.info('SL %.2f <-- %.2f --> %.2f TP' % (stoploss, cur_price, takeprofit))
                    if (current_time - start_time) >= tel_time:
                        send_to_telegram('SL %.2f <-- %.2f --> %.2f TP' % (stoploss, cur_price, takeprofit))

                if self.PosOn and (ret == "BUY"):
                    lg.info("*************** Entering Trade ********************")
                    amt = self.obj.get_margin()
                    lg.info("cash available: {} ".format(amt))
                    amt_for_trade = min(amt, self.capital_per_trade)
                    lg.info("cash using for trade: {} ".format(amt_for_trade))
                    self.quantity = int(amt_for_trade / cur_price)
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
                        takeprofit = self.__set_takeprofit(self.entry_price)
                        stoploss = self.__set_stoploss(self.entry_price)
                        lg.debug("verify_position: {} ".format(str(res)))
                        self.trade = "BUY"
                        self.Pos_count = self.Pos_count + 1
                        save_ticker = self.ticker + "_" + str(self.Pos_count)
                        save_positions(save_ticker, self.ticker, self.quantity, self.trade, self.entry_price, stoploss, takeprofit)
                        save_trade_itr(self.ticker, str(self.Pos_count))
                        save_trade_in_csv(self.ticker, self.quantity, "BUY", self.entry_price)

                elif (self.trade == "BUY") and (ret == "SELL"):
                    lg.info("*************** Exiting Trade ********************")
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
                        # self.trade = "NA"
                        save_ticker = self.ticker + "_" + str(self.Pos_count)
                        remove_positions(save_ticker)
                        self.Pos_count = self.Pos_count - 1
                        save_trade_itr(self.ticker, str(self.Pos_count))
                        save_trade_in_csv(self.ticker, self.quantity, "SELL", self.exit_price)

                elif (self.trade == "BUY") and (cur_price > takeprofit):
                    lg.info("*************** Exiting Trade ********************")
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
                        # self.trade = "NA"
                        save_ticker = self.ticker + "_" + str(self.Pos_count)
                        remove_positions(save_ticker)
                        self.Pos_count = self.Pos_count - 1
                        save_trade_itr(self.ticker, str(self.Pos_count))
                        save_trade_in_csv(self.ticker, self.quantity, "SELL", self.exit_price)

                elif (self.trade == "BUY") and (cur_price < stoploss):
                    lg.info("*************** Exiting Trade ********************")
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
                        save_ticker = self.ticker + "_" + str(self.Pos_count)
                        remove_positions(save_ticker)
                        self.Pos_count = self.Pos_count - 1
                        save_trade_itr(self.ticker, str(self.Pos_count))
                        save_trade_in_csv(self.ticker, self.quantity, "SELL", self.exit_price)

                else:
                    if (current_time - start_time) >= tel_time:
                        lg.info("Doing nothing")

                time.sleep(self.interval)
                if (current_time - start_time) >= tel_time:
                    start_time = current_time

        except KeyboardInterrupt:
            lg.error("Bot stop request by user")
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))
            send_to_telegram(message)

    def strategy(self):
        buy_p = 0.995

        cur_price = self.__get_cur_price()
        lg.info("current price: {} < prev high: {} \n".format(cur_price, (buy_p * self.prev_high)))
        if (current_time - start_time) >= tel_time:
            send_to_telegram("current price: {} < prev high: {}".format(cur_price, (buy_p * self.prev_high)))
        if cur_price < (buy_p * self.prev_high):
            self.prev_high = cur_price
            return "BUY"
        else:
            return "NA"
