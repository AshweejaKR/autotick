# -*- coding: utf-8 -*-
"""
Created on Sat Nov 30 18:21:09 2024

@author: ashwe
"""

import time

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
    def __init__(self, datestamp):
        global no_of_order_placed
        self.datestamp = datestamp
        self.ticker = "NIFTYBEES-EQ"
        self.exchange = "NSE"

        lg.info(f"Initialized autotick Trading Bot for Stock {self.ticker} in {self.exchange} exchange, running on {self.datestamp}")

    def run_trade(self):
        global no_of_order_placed
        lg.info(f"Running Trade for Stock {self.ticker} in {self.exchange} exchange ... ")
