# -*- coding: utf-8 -*-
"""
Created on Mon Sep 25 10:44:40 2023

@author: xieyushan
"""

from math import sqrt
from scipy.stats import norm



# Bachelier model (normal distribution)
def vanilla(flavor, forward, strike, variance, df):
    d = (forward - strike) / sqrt(variance)
    
    if flavor == 'call':
        return df * ((forward - strike) * norm.cdf(d) + sqrt(variance) * norm.pdf(d))
    elif flavor == 'put':
        return df * ((strike - forward) * norm.cdf(-d) + sqrt(variance) * norm.pdf(-d))
    else:
        raise Exception('Vanilla option type error!')
          