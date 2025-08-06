# -*- coding: utf-8 -*-
"""
Created on Mon Aug 21 10:30:19 2023

@author: xieyushan
"""

import QuantLib as ql
import numpy as np
import pandas as pd

from ....utils.ql_date_utils import ql_date_str
from ....utils.fx_utils import fx_ccy_trans, get_trs_fx_spot



class AssetLeg:
    def __init__(
            self, 
            direction: str, 
            qty: float, 
            init_price: float, 
            start_date: ql.Date, 
            expiry_date: ql.Date, 
            reset_dates: np.ndarray,
            payment_dates: np.ndarray, 
            is_fixed_qty: bool = True, 
            spread: float = 0.0,
            spread_daycount: ql.DayCounter = ql.Actual365Fixed(), 
            spread_notional_reset: bool = True,
            ref_prices: pd.Series = pd.Series(dtype=np.float64), 
            ):
        self.direction = direction.lower()
        self.qty = qty
        self.init_price = init_price
        self.start_date = start_date
        self.expiry_date = expiry_date
        self.reset_dates = reset_dates
        self.payment_dates = payment_dates
        self.is_fixed_qty = is_fixed_qty 
        self.spread = spread
        self.spread_daycount = spread_daycount
        self.spread_notional_reset = spread_notional_reset
        self.ref_prices = ref_prices
        
        if not reset_dates[-1] == expiry_date:
            raise Exception('Last reset date must be expiry date!')
        
        if not len(reset_dates) == len(payment_dates):
            raise Exception('Reset dates and payment dates must match!')
            
        if not self.direction in ['pay', 'receive']:
            raise Exception(f'Unsupported direction type: {direction}!')
    
    
    def npv_mtm(self, today: ql.Date, latest_price: float, 
                is_only_realized: bool = False, is_only_unsettled: bool = False):
        npv = 0.0
        for i in range(len(self.reset_dates)):
            payment_date = self.payment_dates[i]
            last_reset_date = self.start_date if i == 0 else self.reset_dates[i - 1]
            reset_date = self.reset_dates[i]
            if payment_date < reset_date:
                raise Exception('Payment date should be later than reset date!')
                
            if payment_date > today and last_reset_date <= today:
                # if is_only_realized and reset_date > today:
                if is_only_realized and reset_date >= today:
                    continue

                # if only unsettled, include valuation only before end
                if is_only_unsettled and reset_date < today:
                    continue
                
                last_ref_price, ref_price = self._get_ref_price(
                    i, last_reset_date, reset_date, today, self.init_price, 
                    latest_price, self.ref_prices)
                
                if self.is_fixed_qty:
                    qty_i = self.qty
                else:
                    qty_i = self.qty * self.init_price / last_ref_price
                
                if self.spread_notional_reset:
                    spread_notional = self.qty * last_ref_price
                else:
                    spread_notional = self.qty * self.init_price
                spread_peirod = self.spread_daycount.yearFraction(
                    last_reset_date, min(today, reset_date))
                
                npv += (qty_i * (ref_price - last_ref_price) + 
                        spread_notional * self.spread * spread_peirod)
        
        return npv if self.direction == 'receive' else -npv
    
    
    @staticmethod
    def _get_ref_price(i, last_reset_date, reset_date, today, 
                       init_price, latest_price, ref_prices):
        if i == 0:
            last_ref_price = init_price
        else:
            try:
                last_ref_price = ref_prices[last_reset_date]
            except:
                last_ref_price = latest_price
        if today >= reset_date:
            try:
                ref_price = ref_prices[reset_date]
            except:
                ref_price = latest_price
        else:
            ref_price = latest_price
        
        return last_ref_price, ref_price
    


class CrossBorderAssetLeg(AssetLeg):
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
            is_fixed_qty: bool = True, 
            spread: float = 0.0,
            spread_daycount: ql.DayCounter = ql.Actual365Fixed(), 
            spread_notional_reset: bool = True,
            ref_prices: pd.Series = pd.Series(dtype=np.float64), 
            fx_fixings: pd.Series = pd.Series(dtype=np.float64), 
            ):
        super().__init__(direction, qty, init_price, start_date, expiry_date, 
                         reset_dates, payment_dates, is_fixed_qty, spread, 
                         spread_daycount, spread_notional_reset, ref_prices)
        self.asset_ccy = asset_ccy.upper()
        self.settle_ccy = settle_ccy.upper()
        self.ccy_pair = ccy_pair.upper()
        self.fx_fixing_dates = fx_fixing_dates
        self.fx_fixings = fx_fixings
        
        if not (len(reset_dates) == len(fx_fixing_dates)):
            raise Exception('Reset dates and fx rate fixing dates must match!')
            
            
    def npv_mtm_asset_ccy(self, today: ql.Date, latest_price: float, 
                          is_only_realized: bool = False, is_only_unsettled: bool = False):
        
        return super().npv_mtm(today, latest_price, is_only_realized=is_only_realized, 
                               is_only_unsettled=is_only_unsettled)
            

    def npv_mtm(self, today: ql.Date, latest_price: float, fx_spot: float, 
                is_only_realized: bool = False, is_only_unsettled: bool = False):
        npv = 0.0
        for i in range(len(self.reset_dates)):
            payment_date = self.payment_dates[i]
            last_reset_date = self.start_date if i== 0 else self.reset_dates[i - 1]
            reset_date = self.reset_dates[i]
            fx_fixing_date = self.fx_fixing_dates[i]
            if payment_date < reset_date:
                raise Exception('Payment date should be later than reset date!')
            if payment_date < fx_fixing_date:
                raise Exception('Payment date should be later than fx rate fixing date!')
                
            if payment_date > today and last_reset_date <= today:
                # if is_only_realized and reset_date > today:
                if is_only_realized and reset_date >= today:
                    continue

                # if only unsettled, include valuation only before end
                if is_only_unsettled and reset_date < today:
                    continue
                
                last_ref_price, ref_price = self._get_ref_price(
                    i, last_reset_date, reset_date, today, self.init_price, 
                    latest_price, self.ref_prices)
                
                if self.is_fixed_qty:
                    qty_i = self.qty
                else:
                    qty_i = self.qty * self.init_price / last_ref_price

                if self.spread_notional_reset:
                    spread_notional = self.qty * last_ref_price
                else:
                    spread_notional = self.qty * self.init_price
                spread_peirod = self.spread_daycount.yearFraction(
                    last_reset_date, min(today, reset_date))
                
                fx_rate = self._get_fx_rate(today, fx_fixing_date, fx_spot)
                
                npv += (qty_i * (ref_price - last_ref_price) + 
                        spread_notional * self.spread * spread_peirod) * fx_rate
                
        return npv if self.direction == 'receive' else -npv
    
    
    def _get_fx_rate(self, today, fx_fixing_date, fx_spot):
        fx_rate = get_trs_fx_spot(
            self.asset_ccy, self.ccy_pair, today, fx_fixing_date, 
            self.fx_fixings, fx_spot)
        
        return fx_rate
            
            
            
class SwapAssetLeg(CrossBorderAssetLeg):
    def __init__(
            self, 
            direction: str, 
            asset_ccy: str, 
            settle_ccy: str, 
            ccy_pair: str, 
            qty: float, 
            init_price: float, 
            init_fx_rate: float, 
            start_date: ql.Date, 
            expiry_date: ql.Date, 
            reset_dates: np.ndarray,
            payment_dates: np.ndarray,
            is_fixed_qty: bool = True, 
            spread: float = 0.0,
            spread_daycount: ql.DayCounter = ql.Actual365Fixed(), 
            spread_notional_reset: bool = True,
            ref_prices: pd.Series = pd.Series(dtype=np.float64), 
            fx_fixings: pd.Series = pd.Series(dtype=np.float64), 
            ):
        self.direction = direction.lower()
        self.qty = qty
        self.init_price = init_price
        self.start_date = start_date
        self.expiry_date = expiry_date
        self.reset_dates = reset_dates
        self.payment_dates = payment_dates
        self.is_fixed_qty = is_fixed_qty 
        self.spread = spread
        self.spread_daycount = spread_daycount
        self.spread_notional_reset = spread_notional_reset
        self.ref_prices = ref_prices
        self.asset_ccy = asset_ccy.upper()
        self.settle_ccy = settle_ccy.upper()
        self.ccy_pair = ccy_pair.upper()
        self.init_fx_rate = init_fx_rate
        self.init_fx_rate_ = fx_ccy_trans(1, asset_ccy, init_fx_rate, ccy_pair)
        self.fx_fixings = fx_fixings
        
        
    def npv_mtm(self, today: ql.Date, latest_price: float, fx_spot: float, 
                is_only_realized: bool = False, is_only_unsettled: bool = False):
        npv = 0.0
        for i in range(len(self.reset_dates)):
            payment_date = self.payment_dates[i]
            last_reset_date = self.start_date if i== 0 else self.reset_dates[i - 1]
            reset_date = self.reset_dates[i]
            if payment_date < reset_date:
                raise Exception('Payment date should be later than reset date!')
                
            if payment_date > today and last_reset_date <= today:
                # if is_only_realized and reset_date > today:
                if is_only_realized and reset_date >= today:
                    continue

                # if only unsettled, include valuation only before end
                if is_only_unsettled and reset_date < today:
                    continue
                
                last_ref_price, ref_price = self._get_ref_price(
                    i, last_reset_date, reset_date, today, self.init_price, 
                    latest_price, self.ref_prices)
                
                if i == 0:
                    last_ref_price = last_ref_price * self.init_fx_rate_
                else:
                    last_fx_rate = self._get_fx_rate(today, last_reset_date, fx_spot)
                    last_ref_price = last_ref_price * last_fx_rate
                    
                fx_rate = self._get_fx_rate(today, reset_date, fx_spot)
                ref_price = ref_price * fx_rate

                if self.is_fixed_qty:
                    qty_i = self.qty
                else:
                    qty_i = self.qty * self.init_price * self.init_fx_rate_ / last_ref_price
                
                if self.spread_notional_reset:
                    spread_notional = self.qty * last_ref_price
                else:
                    spread_notional = self.qty * self.init_price * self.init_fx_rate_
                spread_peirod = self.spread_daycount.yearFraction(
                    last_reset_date, min(today, reset_date))
                
                npv += (qty_i * (ref_price - last_ref_price) + 
                        spread_notional * self.spread * spread_peirod)
                
        return npv if self.direction == 'receive' else -npv
    