# -*- coding: utf-8 -*-
"""
Created on Tue Dec  6 10:14:37 2022

@author: xieyushan
"""

import QuantLib as ql
import numpy as np
import pandas as pd

from ....utils.fx_utils import get_trs_fx_spot
from ....utils import ql_date_utils as qdu



class FixedFundingLeg:
    def __init__(
            self, 
            direction: str, 
            notionals: np.ndarray, 
            start_dates: np.ndarray, 
            end_dates: np.ndarray, 
            payment_dates: np.ndarray, 
            fixed_rate: float,
            daycount: ql.DayCounter, 
            ):
        direction = direction.lower()
        if not direction in ['pay', 'receive']:
            raise Exception(f'Unsupported direction type: {direction}!')
        
        if not (len(notionals) == len(start_dates) == 
                len(end_dates) == len(payment_dates)):
            raise Exception('Schedule info must match!')
        
        self.direction = direction
        self.notionals = notionals
        self.start_dates = start_dates
        self.end_dates = end_dates
        self.payment_dates = payment_dates
        self.fixed_rate = fixed_rate
        self.daycount = daycount
        

    def npv_acr(self, today: ql.Date, is_only_realized: bool = False, is_only_unsettled: bool = False):
        npv = 0
        for notional, start_date, end_date, payment_date in zip(
                self.notionals, self.start_dates, self.end_dates, 
                self.payment_dates):
            if start_date <= today and payment_date > today: 
                # if is_only_realized and end_date > today:
                if is_only_realized and end_date >= today:
                    continue

                # if only unsettled, include valuation only before end
                if is_only_unsettled and end_date < today:
                    continue
                
                acr_end_date = min(end_date, today)
                acr_period = qdu.get_year_fraction(
                    self.daycount, start_date, acr_end_date)
                npv += notional * self.fixed_rate * acr_period
        
        return npv if self.direction == 'receive' else -npv



class CrossBorderFixedFundingLeg(FixedFundingLeg):
    def __init__(
            self, 
            direction: str, 
            funding_ccy: str,
            settle_ccy: str, 
            ccy_pair: str, 
            notionals: np.ndarray, 
            start_dates: np.ndarray, 
            end_dates: np.ndarray, 
            payment_dates: np.ndarray, 
            fx_fixing_dates: np.ndarray, 
            fixed_rate: float,
            daycount: ql.DayCounter, 
            fx_fixings: pd.Series = pd.Series(dtype=np.float64), 
            ):
        super().__init__(direction, notionals, start_dates, end_dates, 
                         payment_dates, fixed_rate, daycount)
        self.funding_ccy = funding_ccy.upper()
        self.settle_ccy = settle_ccy.upper()
        self.ccy_pair = ccy_pair.upper()
        self.fx_fixing_dates = fx_fixing_dates
        self.fx_fixings = fx_fixings
        
        if not (len(notionals) == len(fx_fixing_dates)):
            raise Exception('Schedule info of fx rate fixing must match!')
            
    def npv_acr_funding_ccy(self, today: ql.Date, is_only_realized: bool = False, 
                            is_only_unsettled: bool = False):
        
        return super().npv_acr(today, is_only_realized=is_only_realized, 
                               is_only_unsettled=is_only_unsettled)
        
        
    def npv_acr(self, today: ql.Date, fx_spot: float, is_only_realized: bool = False, 
                is_only_unsettled: bool = False):
        npv = 0
        for notional, start_date, end_date, payment_date, fx_fixing_date in zip(
                self.notionals, self.start_dates, self.end_dates, 
                self.payment_dates, self.fx_fixing_dates):
            if start_date <= today and payment_date > today: 
                # if is_only_realized and end_date > today:
                if is_only_realized and end_date >= today:
                    continue

                # if only unsettled, include valuation only before end
                if is_only_unsettled and end_date < today:
                    continue
                
                acr_end_date = min(end_date, today)
                acr_period = qdu.get_year_fraction(
                    self.daycount, start_date, acr_end_date)
                fx_rate = get_trs_fx_spot(
                    self.funding_ccy, self.ccy_pair, today, fx_fixing_date, 
                    self.fx_fixings, fx_spot)
                
                npv += notional * self.fixed_rate * acr_period * fx_rate
        
        return npv if self.direction == 'receive' else -npv
    
    
    
class FloatFundingLeg:
    def __init__(
            self, 
            direction: str, 
            notionals: np.ndarray, 
            start_dates: np.ndarray, 
            end_dates: np.ndarray, 
            reset_dates_array: np.ndarray,
            fixing_dates_array: np.ndarray,
            payment_dates: np.ndarray, 
            index_name: str, 
            spread: float,
            daycount: ql.DayCounter,
            compounding_type: str = 'IncludeSprd',
            negative_interest_rate: str = 'Allow',
            ):
        
        direction = direction.lower()
        if not direction in ['receive', 'pay']:
            raise Exception(f'Unsupported direction type: {direction}!')
        
        if not (len(notionals) == len(start_dates) == len(end_dates) == 
                len(payment_dates) == len(reset_dates_array) == 
                len(fixing_dates_array)):
            raise Exception('Schedule info must match!')
        
        for start_date, reset_dates in zip(start_dates, reset_dates_array):
            if not start_date == reset_dates[0]:
                raise Exception('First reset date and start date must match!')
        
        if daycount == None:
            raise Exception('Float funding leg daycount should be annual!')
            
        if not negative_interest_rate in ['Allow', 'Zero', 'ZeroExcludingSprd']:
            raise Exception(f'Unsupported negative interest rate type: {negative_interest_rate}!')
        
        
        self.direction = direction
        self.notionals = notionals
        self.start_dates = start_dates
        self.end_dates = end_dates
        self.reset_dates_array = reset_dates_array
        self.fixing_dates_array = fixing_dates_array
        self.payment_dates = payment_dates
        self.index_name = index_name
        self.spread = spread
        self.daycount = daycount
        self.compounding_type = compounding_type
        self.negative_interest_rate = negative_interest_rate

    
    def npv_acr(self, today: ql.Date, fixings: pd.Series, 
                is_only_realized: bool = False, is_only_unsettled: bool = False):
        npv = 0
        for (notional, start_date, end_date, payment_date, reset_dates, 
             fixing_dates) in zip(
                 self.notionals, self.start_dates, self.end_dates, self.payment_dates, 
                 self.reset_dates_array, self.fixing_dates_array):
            if start_date < today and payment_date > today: 
                # if is_only_realized and end_date > today:
                if is_only_realized and end_date >= today:
                    continue

                # if only unsettled, include valuation only before end
                if is_only_unsettled and end_date < today:
                    continue

                acr_value = self.get_acr_value(
                    today, end_date, reset_dates, fixing_dates, fixings)
                npv += notional * acr_value
                
        return npv if self.direction == 'receive' else -npv
        
    
    def get_acr_value(
            self, today: ql.Date, end_date: ql.Date, reset_dates: np.ndarray, 
            fixing_dates: np.ndarray, fixings: pd.Series):
        rate_array = fixings[fixing_dates[reset_dates < today]]
        if self.negative_interest_rate == 'ZeroExcludingSprd':
            rate_array[rate_array<0] = 0 
            
        reset_dates = np.append(
            reset_dates[reset_dates < today], min(today, end_date))
        if len(rate_array) == 1:
            float_rate = rate_array[0] + self.spread / 10000.0
        else:        
            reset_period_dcf = np.array(
                [self.daycount.yearFraction(reset_dates[i], reset_dates[i+1]) 
                 for i in range(np.size(reset_dates) - 1)])
            
            if self.compounding_type == 'ExcludeSprd':
                float_rate = ((np.prod(rate_array * reset_period_dcf + 1) - 1) / 
                              np.sum(reset_period_dcf))
                float_rate += self.spread / 10000.0
            elif self.compounding_type == 'IncludeSprd':
                rate_array = rate_array + self.spread / 10000.0
                float_rate = ((np.prod(rate_array * reset_period_dcf + 1) - 1) / 
                              np.sum(reset_period_dcf))
            elif self.compounding_type == 'Simple':
                float_rate = (np.sum(rate_array * reset_period_dcf) / 
                              np.sum(reset_period_dcf))
                float_rate += self.spread / 10000.0
            elif self.compounding_type == 'Average':
                float_rate = np.mean(rate_array)
                float_rate += self.spread / 10000.0
            else:
                raise Exception(f'Unsupported compounding type: {self.compounding_type}')
        
        if (float_rate<0) & (self.negative_interest_rate == 'Zero'):
            return 0
        else:
            return float_rate * self.daycount.yearFraction(reset_dates[0], reset_dates[-1])

        
    
class CrossBorderFloatFundingLeg(FloatFundingLeg):
    def __init__(
            self,
            direction: str, 
            funding_ccy: str,
            settle_ccy: str, 
            ccy_pair: str, 
            notionals: np.ndarray, 
            start_dates: np.ndarray, 
            end_dates: np.ndarray, 
            reset_dates_array: np.ndarray,
            fixing_dates_array: np.ndarray,
            payment_dates: np.ndarray, 
            fx_fixing_dates: np.ndarray, 
            index_name: str, 
            spread: float,
            daycount: ql.DayCounter,
            compounding_type: str = 'IncludeSprd',
            negative_interest_rate: str = 'Allow',
            fx_fixings: pd.Series = pd.Series(dtype=np.float64), 
            ):
        super().__init__(
            direction, notionals, start_dates, end_dates, reset_dates_array, 
            fixing_dates_array, payment_dates, index_name, spread, daycount, 
            compounding_type, negative_interest_rate)
        self.funding_ccy = funding_ccy.upper()
        self.settle_ccy = settle_ccy.upper()
        self.ccy_pair = ccy_pair.upper()
        self.fx_fixing_dates = fx_fixing_dates
        self.fx_fixings = fx_fixings
        
        if not (len(notionals) == len(fx_fixing_dates)):
            raise Exception('Schedule info of fx rate fixing must match!')
    
    
    def npv_acr_funding_ccy(self, today: ql.Date, fixings: pd.Series, 
                            is_only_realized: bool = False, is_only_unsettled: bool = False):
        
        return super().npv_acr(today, fixings, is_only_realized=is_only_realized, 
                               is_only_unsettled=is_only_unsettled)
    
            
    def npv_acr(self, today: ql.Date, fixings: pd.Series, fx_spot: float, 
                is_only_realized: bool = False, is_only_unsettled: bool = False):
        npv = 0
        for (notional, start_date, end_date, payment_date, reset_dates, 
             fixing_dates, fx_fixing_date) in zip(
                self.notionals, self.start_dates, self.end_dates,
                self.payment_dates, self.reset_dates_array, 
                self.fixing_dates_array, self.fx_fixing_dates):
            if start_date < today and payment_date > today: 
                # if is_only_realized and end_date > today:
                if is_only_realized and end_date >= today:
                    continue

                # if only unsettled, include valuation only before end
                if is_only_unsettled and end_date < today:
                    continue

                acr_value = self.get_acr_value(
                    today, end_date, reset_dates, fixing_dates, fixings)
                fx_rate = get_trs_fx_spot(
                    self.funding_ccy, self.ccy_pair, today, fx_fixing_date, 
                    self.fx_fixings, fx_spot)
                npv += notional * acr_value * fx_rate
                
        return npv if self.direction == 'receive' else -npv
        

    
    