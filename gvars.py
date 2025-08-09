# -*- coding: utf-8 -*-
"""
Created on Sun Dec  1 18:55:40 2024

@author: ashwe
"""

import datetime as dt

waitTime = dt.time(8, 55)
startTime = dt.time(9, 15)
endTime = dt.time(15, 15)
sleepTime = 5

# Per-ticker tracking using dictionaries
ticker_index = {}  # Track current index for each ticker
ticker_max_len = {}  # Track max length for each ticker

debugOn = True

# bot config data variables
strategy_threads = []
# broker_threads = {}
brokers = []
# objs = []