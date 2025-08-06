# -*- coding: utf-8 -*-
"""
Created on Tue Aug 22 16:24:02 2023

@author: xieyushan
"""

import QuantLib as ql
import numpy as np
import pandas as pd

from devlib.products.general.trs.trs import Trs, CrossBorderTrs
from devlib.products.general.trs import asset_leg
from devlib.products.general.trs import funding_leg



class FutureTrs(Trs):
    def __init__(
            self, 
            direction: str, 
            qty: float, 
            init_price: float, 
            start_date: ql.Date, 
            expiry_date: ql.Date, 
            reset_dates: np.ndarray,
            payment_dates: np.ndarray,
            ref_prices: pd.Series = pd.Series(dtype=np.float64),
            funding_legs: dict = {},
            ):
        self.direction = direction
        self.qty = qty
        self.init_price= init_price
        self.start_date = start_date
        self.expiry_date = expiry_date
        self.reset_dates = reset_dates
        self.payment_dates = payment_dates
        self.ref_prices = ref_prices
        
        self.funding_legs = funding_legs    
        
        # future trs has no distribution and no spread
        self.asset_leg = asset_leg.AssetLeg(
            direction, qty, init_price, start_date, expiry_date, reset_dates,
            payment_dates, ref_prices=ref_prices)
        


class CrossBorderFutureTrs(CrossBorderTrs):
    def __init__(
            self, 
            direction: str, 
            asset_ccy: str, 
            settle_ccy: str, 
            ccy_pair: str, 
            qty: float, 
            init_price: float, 
            start_date: ql.Date, 
            expiry_date: ql.Date, 
            reset_dates: np.ndarray,
            payment_dates: np.ndarray,
            fx_fixing_dates: np.ndarray, 
            ref_prices: pd.Series = pd.Series(dtype=np.float64),
            fx_fixings: pd.Series = pd.Series(dtype=np.float64),
            funding_legs: dict = {},
            ):
        self.direction = direction
        self.asset_ccy = asset_ccy
        self.settle_ccy = settle_ccy
        self.ccy_pair = ccy_pair
        self.qty = qty
        self.init_price= init_price
        self.start_date = start_date
        self.expiry_date = expiry_date
        self.reset_dates = reset_dates
        self.payment_dates = payment_dates
        self.fx_fixing_dates = fx_fixing_dates
        self.ref_prices = ref_prices
        self.fx_fixings = fx_fixings
                
        self.funding_legs = funding_legs
        
        # future trs has no distribution and no spread
        self.asset_leg = asset_leg.CrossBorderAssetLeg(
            direction, asset_ccy, settle_ccy, ccy_pair, qty, init_price, 
            start_date, expiry_date, reset_dates, payment_dates, fx_fixing_dates, 
            ref_prices=ref_prices, fx_fixings=fx_fixings)
