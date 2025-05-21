# -*- coding: utf-8 -*-
"""
Created on Sat Nov 30 18:21:09 2024

@author: ashwe
"""

import time
import pandas as pd

from broker import *
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
    def __init__(self, datestamp, tickers = None, run_strategy = None, init_strategy = None, strategy_config = None):
        global no_of_order_placed
        self.datestamp = datestamp
        self.tickers = tickers
        self.strategy_config = strategy_config
        self.__init_strategy = init_strategy
        self.__run_strategy = run_strategy

        ###########################
        # self.Exchange = "NSE"
        # _broker = "ANGELONE"
        # self.Interval = 1
        ###########################
        self.read_config_data()
        ###########################
        self.broker_obj = Broker(0, self.Broker)
        self.quantity = 1
        self.stop_loss_pct = 0.1
        self.target_pct = 0.2
        self.trailing_pct = 0.05
        self.trailing_trigger_pct = 0.01
        self.max_reentries = 3
        self.Interval = 5.1

        # state
        self.open_trades = []      # list of dicts for each open position
        self.reentry_counts = { 'BUY': 0, 'SELL': 0 }
        self.max_open_positions = 0

    def _enter_trade(self, signal):
        price = self.broker_obj.get_current_price(self.tickers[0], self.Exchange)
        # calculate initial SL & TP
        if signal == "BUY":
            sl = price * (1 - self.stop_loss_pct)
            tp = price * (1 + self.target_pct)
        else:  # SELL
            sl = price * (1 + self.stop_loss_pct)
            tp = price * (1 - self.target_pct)

        # place order via your broker API
        # order = self.place_order_api(signal, self.quantity)
        order_id = "DUMMY_ID"
        
        # save trade
        trade = {
            "signal":      signal,
            "entry_price": price,
            "sl":          sl,
            "tp":          tp,
            "order_id":    order_id
        }
        self.open_trades.append(trade)
        self.reentry_counts[signal] += 1
        self.max_open_positions = max(self.max_open_positions, len(self.open_trades))
        print(f"Entered {signal} @ {price:.2f}  SL={sl:.2f} TP={tp:.2f}")

    def _manage_current_trade(self):
        trade = self.open_trades[-1]
        price = self.broker_obj.get_current_price(self.tickers[0], self.Exchange)
        sig   = trade["signal"]
        
        # 3) trailing stop logic
        profit_pct = (price - trade["entry_price"]) / trade["entry_price"]
        if sig == "SELL":
            profit_pct = -profit_pct
        
        if profit_pct >= self.trailing_trigger_pct:
            # update SL to lock in profit
            if sig == "BUY":
                new_sl = price * (1 - self.trailing_pct)
                trade["sl"] = max(trade["sl"], new_sl)
            else:
                new_sl = price * (1 + self.trailing_pct)
                trade["sl"] = min(trade["sl"], new_sl)
            print(f"Trailing SL updated to {trade['sl']:.2f}")
        
        # 4) check SL or TP hit
        if sig == "BUY":
            if price <= trade["sl"] or price >= trade["tp"]:
                self._exit_trade(trade, price)
        else:  # SELL
            if price >= trade["sl"] or price <= trade["tp"]:
                self._exit_trade(trade, price)

    def _exit_trade(self, trade, exit_price):
        # close via your broker API
        # self.close_order_api(trade["order_id"])
        
        # update state
        self.open_trades.pop()
        self.reentry_counts[trade["signal"]] -= 1
        
        pnl = (exit_price - trade["entry_price"]) * (1 if trade["signal"]=="BUY" else -1) * self.quantity
        print(f"Closed {trade['signal']} @ {exit_price:.2f}  P&L={pnl:.2f}")

    def __del__(self):
        pass

    # TODO
    def read_config_data(self):
        try:
            lg.warning("Reading strategy config CSV data")
            df = pd.read_csv(self.strategy_config)
            # Create a dictionary with proper types
            typed_mapping = {
                row['NAME']: cast_value(row['VALUE'], row['TYPE'])
                for _, row in df.iterrows()
            }

            for i in typed_mapping:
                n = i.replace(" ", "_")
                setattr(self, n, typed_mapping[i])

        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))

    def start_trade(self, index=0):
        global no_of_order_placed
        if self.__init_strategy is not None:
                try:
                    self.__init_strategy(self)
                except Exception as err:
                    template = "An exception of type {0} occurred while running __init_strategy. error message:{1!r}"
                    message = template.format(type(err).__name__, err.args)
                    lg.error("{}".format(message))

        wait_till_market_open(self.Mode)
        self.__run_trade()

    def __run_trade(self, index=0):

        while is_market_open(self.Mode):
            start_time = time.time()
            signal = "NA"
            try:
                if self.__run_strategy is not None:
                    try:
                        signal = self.__run_strategy(self)
                    except Exception as err:
                        template = "An exception of type {0} occurred while running __run_strategy. error message:{1!r}"
                        message = template.format(type(err).__name__, err.args)
                        lg.error("{}".format(message))

                #########################################################################
                # 1) handle new signals / re-entry
                if signal in ("BUY", "SELL"):
                    if self.reentry_counts[signal] < self.max_reentries:
                        self._enter_trade(signal)

                # 2) manage the last placed trade (SL, TP, trailing)
                if self.open_trades:
                    self._manage_current_trade()
                #########################################################################

                end_time = time.time()
                taken_time = end_time - start_time
                if self.Interval - taken_time > 0:
                    taken_time = self.Interval - taken_time
                else:
                    taken_time = self.Interval
                time.sleep(taken_time)

            except KeyboardInterrupt:
                lg.error("Bot stop request by user")
                break

            except Exception as err:
                template = "An exception of type {0} occurred. error message:{1!r}"
                message = template.format(type(err).__name__, err.args)
                lg.error("{}".format(message))
                break
