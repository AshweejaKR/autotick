# -*- coding: utf-8 -*-
"""
Created on Sat May 17 16:48:59 2025

@author: ashwe
"""
from logger import *

def init_strategy(obj):
    lg.info(f"Initializing Strategy for Stock {obj.tickers} in {obj.Exchange} exchange ... ")

def run_strategy(obj):
    lg.info(f"Running Strategy for Stock {obj.tickers} in {obj.Exchange} exchange ... ")
