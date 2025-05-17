# -*- coding: utf-8 -*-
"""
Created on Sat Nov 30 18:11:42 2024

@author: ashwe
"""

import sys
from enum import Enum

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
    
    ###########################################################################
    obj = autotick(datestamp)
    obj.init_strategy = strategy.init_strategy
    obj.run_strategy = strategy.run_strategy
    obj.run_trade()
    del obj
    ###########################################################################
    end = time.time()
    diff = end - start
    lg.info("Total time taken : {} \n".format(time.strftime('%H:%M:%S', time.gmtime(diff))))

    lg.done("Trading Bot done ...")
    
if __name__ == "__main__":
    main()
