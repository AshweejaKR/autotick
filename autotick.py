# -*- coding: utf-8 -*-
"""
Created on Sat Nov 30 18:21:09 2024

@author: ashwe
"""

import time
import pandas as pd

from broker import *
from utils import *

## temp import
import json
import os

global no_of_order_placed
no_of_order_placed = 0

def KillSwitch():
    global no_of_order_placed
    if no_of_order_placed > 5:
        lg.error("Kill Switch Activated!!")
        lg.error("Stopping the Trading Bot")
        sys.exit(-1)

class autotick:
    def __init__(self, datestamp, strategy_id, broker_obj, mode, ticker, run_strategy = None, init_strategy = None, strategy_config = None):
        self.datestamp = datestamp
        self.strategy_id = strategy_id
        self.ticker = ticker
        self.strategy_config = strategy_config
        self.__init_strategy = init_strategy
        self.__run_strategy = run_strategy

        ###########################
        self.read_config_data()
        ###########################
        self.Mode = mode
        self.broker_obj = broker_obj

        mode_name = self.Mode
        self.Mode = 1 if (mode_name == "LIVE") else (2) if (mode_name == "PAPER") else (3) if (mode_name == "BACKTEST") else (4)
        lg.info(f"Trading mode value: {mode}")
        lg.info(f"Trading bot mode: {mode_name}")

        if self.Mode == 3:
            self.Interval = 0.0001
            self.broker_obj.init_test(self.ticker, self.Exchange, self.datestamp)

        pos_path = './data/'
        if self.Mode > 1:
            self.state_file = pos_path + f"{strategy_id}_{self.ticker}_trade_state_{mode_name.lower()}.json"
            self.trade_report_file = f"{strategy_id}_trade_report_{mode_name.lower()}"
        else:
            self.state_file = pos_path + f"{strategy_id}_{self.ticker}_trade_state.json"
            self.trade_report_file = f"{strategy_id}_trade_report"

        # state
        self.open_trades = []      # list of dicts for each open position
        self.reentry_counts = { 'BUY': 0, 'SELL': 0 }
        self.max_open_positions = 0


        # print(dir(self))
        # print("--------------------------------------------------------------------------\n")
        # print(f"Inside the class -- Strategy ID: {self.strategy_id}, {type(self.strategy_id)}")
        # print(f"Inside the class -- Broker Obj: {self.broker_obj}, {type(self.broker_obj)}")
        # print(f"Inside the class -- Ticker: {self.ticker}, {type(self.ticker)}")
        # print(f"Inside the class -- Exchange: {self.Exchange}, {type(self.Exchange)}")
        # print(f"Inside the class -- Mode: {self.Mode}, {type(self.Mode)}")
        # print(f"Inside the class -- Interval: {self.Interval}, {type(self.Interval)}")
        # print(f"Inside the class -- stop_loss_pct: {self.stop_loss_pct}, {type(self.stop_loss_pct)}")
        # print(f"Inside the class -- target_pct: {self.target_pct}, {type(self.target_pct)}")
        # print(f"Inside the class -- trailing_pct: {self.trailing_pct}, {type(self.trailing_pct)}")
        # print(f"Inside the class -- trailing_trigger_pct: {self.trailing_trigger_pct}, {type(self.trailing_trigger_pct)}")
        # print(f"Inside the class -- max_reentries: {self.max_reentries}, {type(self.max_reentries)}")
        # print(f"Inside the class -- capital_per_trade: {self.capital_per_trade}, {type(self.capital_per_trade)}")
        # print("--------------------------------------------------------------------------\n")
        self._load_state()

        lg.info(f"Initialized autotick Trading Bot for Stock {self.ticker} in {self.Exchange} exchange, running on {self.datestamp}")

    def _enter_trade(self, signal):
        global no_of_order_placed
        # place order via your broker API
        order_status = False
        available_cash = self.broker_obj.get_available_margin()
        cash_for_trade = min(available_cash, self.capital_per_trade)
        cur_price = self.broker_obj.get_current_price(self.ticker, self.Exchange)
        quantity = int(cash_for_trade / cur_price)
        if quantity > 0:
            if signal == "BUY":
                order_status = self.broker_obj.place_buy_order(self.ticker, quantity, self.Exchange)
            else:
                order_status = self.broker_obj.place_sell_order(self.ticker, quantity, self.Exchange)

            if order_status:
                order_status = self.broker_obj.verify_position(self.ticker, quantity, signal)

            if order_status:
                trade_count = self.reentry_counts[signal] + 1

                entry_price = self.broker_obj.get_entry_exit_price(self.ticker, signal)
                # calculate initial SL & TP
                if signal == "BUY":
                    sl = entry_price * (1 - self.stop_loss_pct)
                    tp = entry_price * (1 + self.target_pct)
                    no_of_order_placed = no_of_order_placed + 1
                else:  # SELL
                    sl = entry_price * (1 + self.stop_loss_pct)
                    tp = entry_price * (1 - self.target_pct)

                # save trade
                trade = {
                    "signal":      signal,
                    "entry_price": entry_price,
                    "sl":          sl,
                    "tp":          tp,
                    "quantity":    quantity,
                    "trade_count": trade_count
                }
                self.open_trades.append(trade)
                self.reentry_counts[signal] += 1
                self.max_open_positions = max(self.max_open_positions, len(self.open_trades))
                lg.info(f"Entered {signal} for {self.ticker} @ {entry_price:.2f}  SL={sl:.2f} TP={tp:.2f}")
                self._save_state()
                cmnt = "Entered long position" if signal == "BUY" else "Entered short position"
                if self.Mode != 3:
                    trade_time = dt.datetime.now().strftime('%Y-%m-%d %H-%M-%S')
                else:
                    trade_time = self.datestamp
                save_trade_in_csv(self.trade_report_file, trade_time, self.ticker, quantity, signal, entry_price, cmnt)
            else:
                lg.error(f"Failed to Entered {signal} for {self.ticker}, Reason: {self.broker_obj.error_msg}")
        else:
            lg.error(f"Failed to Entered {signal} for {self.ticker}, Reason: Insufficient funds")

    def _manage_current_trade(self):
        trade = self.open_trades[-1]
        price = self.broker_obj.get_current_price(self.ticker, self.Exchange)
        sig   = trade["signal"]
        myPrint('%d: SL %.2f <-- %.2f --> %.2f TP' % (trade["trade_count"], trade["sl"], price, trade["tp"]))

        # 3) trailing stop logic
        profit_pct = (price - trade["entry_price"]) / trade["entry_price"]
        if sig == "SELL":
            profit_pct = -profit_pct

        if profit_pct >= self.trailing_trigger_pct:
            # update SL to lock in profit
            old_sl = trade["sl"]
            if sig == "BUY":
                new_sl = price * (1 - self.trailing_pct)
                trade["sl"] = max(trade["sl"], new_sl)
            else:
                new_sl = price * (1 + self.trailing_pct)
                trade["sl"] = min(trade["sl"], new_sl)
            myPrint(f"Trailing SL updated from {old_sl:.2f} to {trade['sl']:.2f}")
            self._save_state()

        # 4) check SL or TP hit
        hit_sl = (price <= trade["sl"]) if sig=="BUY" else (price >= trade["sl"])
        hit_tp = (price >= trade["tp"]) if sig=="BUY" else (price <= trade["tp"])
        if hit_sl or hit_tp:
            cmnt = "Target hit" if hit_tp else "Stoploss hit"            
            self._exit_trade(trade, cmnt)

    def _exit_trade(self, trade, cmnt):
        # close via your broker API
        order_status = False
        quantity = trade["quantity"]
        signal = trade["signal"]
        order_type = "NA"

        if signal == "BUY":
            order_status = self.broker_obj.place_sell_order(self.ticker, quantity, self.Exchange)
            order_type = "SELL"
        else:
            order_status = self.broker_obj.place_buy_order(self.ticker, quantity, self.Exchange)
            order_type = "BUY"

        if order_status:
            order_status = self.broker_obj.verify_position(self.ticker, quantity, signal, True)

        if order_status:
            exit_price = self.broker_obj.get_entry_exit_price(self.ticker, signal, True)
            # update state
            self.open_trades.pop()
            self.reentry_counts[trade["signal"]] -= 1

            pnl = (exit_price - trade["entry_price"]) * (1 if trade["signal"]=="BUY" else -1) * trade["quantity"]
            lg.info(f"Closed {trade['signal']} for {self.ticker} @ {exit_price:.2f}  P&L={pnl:.2f}")

            self._save_state()
            if self.Mode != 3:
                trade_time = dt.datetime.now().strftime('%Y-%m-%d %H-%M-%S')
            else:
                trade_time = self.datestamp
            save_trade_in_csv(self.trade_report_file, trade_time, self.ticker, quantity, order_type, exit_price, cmnt)

    def _save_state(self):
        state = {
            "open_trades":        self.open_trades,
            "reentry_counts":     self.reentry_counts,
            "max_open_positions": self.max_reentries
        }
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)

    def _load_state(self):
        if os.path.isfile(self.state_file):
            with open(self.state_file, "r") as f:
                state = json.load(f)
            self.open_trades        = state.get("open_trades", [])
            self.reentry_counts     = state.get("reentry_counts", {"BUY":0,"SELL":0})
            self.max_open_positions = state.get("max_open_positions", 0)
        else:
            # first run
            self.open_trades        = []
            self.reentry_counts     = {"BUY": 0, "SELL": 0}
            self.max_open_positions = 0

    def __del__(self):
        pass

    # TODO
    def read_config_data(self):
        config_path = './config/'
        currentlog_path = config_path + self.strategy_config
        try:
            lg.warning("Reading strategy config CSV data")
            df = pd.read_csv(currentlog_path)
            # Create a dictionary with proper types
            typed_mapping = {
                row['NAME']: cast_value(row['VALUE'], row['TYPE'])
                for _, row in df.iterrows()
            }

            for i in typed_mapping:
                if (type(i) == type('str')):
                    n = i.replace(" ", "_")
                    setattr(self, n, typed_mapping[i])

            # make sl, tgt, tsl to %
            self.stop_loss_pct = self.stop_loss_pct / 100.00
            self.target_pct = self.target_pct / 100.00
            self.trailing_pct = self.trailing_pct / 100.00
            self.trailing_trigger_pct = self.trailing_trigger_pct / 100.00
        except Exception as err:
            template = "An exception of type {0} occurred. error message:{1!r}"
            message = template.format(type(err).__name__, err.args)
            lg.error("{}".format(message))

    def start_trade(self, index=0):
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
        # If market was closed while running, reload at start
        self._load_state()

        c = 0
        while is_market_open(self.Mode):
        # while c < 1:
            c = c + 1
            start_time = time.time()
            signal = "NA"
            # print(f"open_trades : {self.open_trades} ... \n")
            try:
                if self.__run_strategy is not None:
                    try:
                        signal = self.__run_strategy(self)
                        print(f"returned signal : {signal}")
                    except Exception as err:
                        template = "An exception of type {0} occurred while running __run_strategy. error message:{1!r}"
                        message = template.format(type(err).__name__, err.args)
                        lg.error("{}".format(message))

                KillSwitch()
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
