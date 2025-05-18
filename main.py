# -*- coding: utf-8 -*-
"""
Created on Sat Nov 30 18:11:42 2024

@author: ashwe
"""

import sys

import strategy

from logger import *
from autotick import *

def main():

    initialize_logger()
    lg.info("Trading Bot running ... ! \n")

    start = time.time()
    ###########################################################################
    datestamp = dt.date.today()
    ###########################
    strategy_config_file = "C:\\user\\ashwee\\autotick\\data\\test_strategy.csv"
    ###########################################################################
    obj = autotick(datestamp, ["NIFTYBEES-EQ"], strategy.run_strategy, strategy.init_strategy, strategy_config_file)
    print(dir(obj))
    print(f"obj.Broker : {obj.Broker}, {type(obj.Broker)}")
    print(f"obj.Exchange : {obj.Exchange}, {type(obj.Exchange)}")
    print(f"obj.Interval : {obj.Interval}, {type(obj.Interval)}")
    print(f"obj.Intraday : {obj.Intraday}, {type(obj.Intraday)}")
    print(f"obj.Stoploss : {obj.Stoploss}, {type(obj.Stoploss)}")
    print(f"obj.Target : {obj.Target}, {type(obj.Target)}")
    print(f"obj.Trade count : {obj.Trade_count}, {type(obj.Trade_count)}")
    print(f"obj.Trade once : {obj.Trade_once}, {type(obj.Trade_once)}")
    obj.start_trade()
    del obj
    ###########################################################################

    end = time.time()
    diff = end - start
    lg.info("Total time taken : {} \n".format(time.strftime('%H:%M:%S', time.gmtime(diff))))

    lg.done("Trading Bot done ...")

if __name__ == "__main__":
    main()
