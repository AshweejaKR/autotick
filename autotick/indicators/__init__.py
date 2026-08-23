# -*- coding: utf-8 -*-
"""
Created on Mon Aug 24 00:19:15 2026

@author: ashwe

Indicator package for AutoTick.
"""

from autotick.indicators.base import Indicator
from autotick.indicators.moving_average import SimpleMovingAverage

__all__ = ["Indicator", "SimpleMovingAverage"]
