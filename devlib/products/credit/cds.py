# -*- coding: utf-8 -*-
"""
Created on Wed Nov  6 15:44:39 2024

@author: Guanzhifan
"""

from typing import Union
import numpy as np
import pandas as pd
from itertools import repeat

import QuantLib as ql

from utils.ql_date_utils import get_year_fraction, ql_date_str
from utils.cds_utils import get_settle_date


#%%
class Cds:
    def __init__(
            self,
            direction: str, #{'long','short'}
            notional: float,
            effective_date: ql.Date,
            maturity_date: ql.Date,
            upfront_amount: float,
            upfront_payment_date: ql.Date,
            coupon_pay_front: bool,
            spread: float,
            daycount: ql.DayCounter,
            coupon_start_dates: Union[None, np.ndarray] = None,
            coupon_end_dates: Union[None, np.ndarray] = None, #[start, end]含首尾
            coupon_payment_dates: Union[None, np.ndarray] = None,
            accrual_coupon_type: str = 'ToDefaultDate', #{'Zero','ToDefaultDate','ToPeriodEndDate'}
            accrual_coupon_payment_date_type: str = 'DefaultDate', #{'DefaultDate', 'PaymentDate'}
            protection_start_dates: Union[None, np.ndarray] = None,
            protection_end_dates: Union[None, np.ndarray] = None, #[start, end]含首尾
            protection_payment_date_type: str = 'DefaultDate', #{'DefaultDate', 'PeriodEndDate'}
            recovery_rate: Union[None, float] = None
            ):
                
        if spread == 0.0:
            coupon_pay_front = True
            coupon_start_dates = np.array([effective_date])
            coupon_end_dates = np.array([maturity_date])
            coupon_payment_dates = np.array([upfront_payment_date])
        elif coupon_pay_front & (accrual_coupon_payment_date_type == 'PaymentDate'):
            raise Exception('If coupon pay front, only support pay at default date!')
            
        if type(coupon_start_dates) == type(None):
            coupon_start_dates = np.array([effective_date])
        if type(coupon_end_dates) == type(None):
            coupon_end_dates = np.array([maturity_date])
        
        if type(protection_start_dates) == type(None):
            protection_start_dates = np.array([effective_date])
        if type(protection_end_dates) == type(None):
            protection_end_dates = np.array([maturity_date])
        
        if not (len(coupon_start_dates) == len(coupon_end_dates) == len(coupon_payment_dates)):
            raise Exception('Unmatched coupon dates!')
        
        if not (len(protection_start_dates) == len(protection_end_dates)):
            raise Exception('Unmatched protection dates!')

        if not (min(coupon_start_dates) <= min(protection_start_dates) <= effective_date):
            raise Exception('Check first protection start date, first coupon start date, effective date!')            
        
        if not (max(coupon_end_dates) == max(protection_end_dates) == maturity_date):
            raise Exception('Check last protection end date, last coupon end date, maturity date!')    
        
        self.direction = direction
        self.notional = notional
        self.effective_date = effective_date
        self.maturity_date = maturity_date
        self.upfront_amount = upfront_amount
        self.upfront_payment_date = upfront_payment_date
        self.coupon_pay_front = coupon_pay_front
        self.spread = spread
        self.daycount = daycount
        self.recovery_rate = recovery_rate

        sorted_indices = np.argsort(coupon_start_dates)
        self.coupon_start_dates = coupon_start_dates[sorted_indices]
        self.coupon_end_dates = coupon_end_dates[sorted_indices]
        self.coupon_payment_dates = coupon_payment_dates[sorted_indices]
        
        if self.spread != 0.0:        
            if self.coupon_pay_front:
                if sum(self.coupon_payment_dates != self.coupon_start_dates) != 0:
                    raise Exception('Coupon payment dates and coupon start dates should be the same!')     
                self.coupon_determination_dates = self.coupon_start_dates
            else:
                if sum(self.coupon_payment_dates < self.coupon_end_dates) != 0:
                    raise Exception('Coupon payment dates should not be smaller than coupon end dates!')     
                self.coupon_determination_dates = self.coupon_end_dates
            
            self.coupon_rate = spread * 1e-4
            self.year_fractions = np.array(
                [get_year_fraction(self.daycount, start_date, end_date, day_stub='IncludeFirstIncludeEnd')
                  for start_date, end_date in zip(self.coupon_start_dates, self.coupon_end_dates)])
            self.cashflows = self.notional * self.coupon_rate * self.year_fractions

        self.accrual_coupon_type = accrual_coupon_type
        self.accrual_coupon_payment_date_type = accrual_coupon_payment_date_type
        
        sorted_indices = np.argsort(protection_start_dates)
        self.protection_start_dates = protection_start_dates[sorted_indices]
        self.protection_end_dates = protection_end_dates[sorted_indices]
        self.protection_payment_date_type = protection_payment_date_type
                
        
    def npv(self, today, discount_curve, credit_curve, valuation_mode='FI'):
        if valuation_mode not in ['FI', 'BBG']:
            raise Exception(f'Unsupported valuation mode: {valuation_mode}!')  
        
        if self.recovery_rate == None:
            recovery_rate = credit_curve.recovery_rate
        else:
            recovery_rate = self.recovery_rate
        
        npv_upfront = 0 if self.upfront_payment_date <= today \
            else self.upfront_amount * discount_curve.curve.discount(self.upfront_payment_date) \
                / discount_curve.curve.discount(today)
        
        if self.spread == 0:
            npv_coupon_survive, npv_coupon_default = 0.0, 0.0
        else:            
            cal_ratios_survive, cal_ratios_default = self._get_coupon_cal_ratios(today, valuation_mode)
            npv_coupon_survive = self._get_npv_coupon_survive(today, discount_curve, credit_curve, cal_ratios_survive)
            npv_coupon_default = self._get_npv_coupon_default(today, discount_curve, credit_curve, cal_ratios_default)
            
        npv_protection = self._get_npv_protection(today, discount_curve, credit_curve, recovery_rate)
        
        npv = npv_protection - npv_coupon_survive - npv_coupon_default - npv_upfront
        npv *= 1 if self.direction == 'long' else -1
        
        return npv
    
    
    def _get_coupon_cal_ratios(self, today, valuation_mode):
        if valuation_mode == 'FI':
            cal_ratios_survive = self.coupon_payment_dates > today
            cal_ratios_default = self.coupon_end_dates > today
        else:
            if not ((not self.coupon_pay_front) \
                    & (self.accrual_coupon_type == 'ToDefaultDate') \
                        & (self.accrual_coupon_payment_date_type == 'DefaultDate')):
                raise Exception('Not support BBG valuation mode!')    
            else:
                cal_ratios_survive = np.ones(len(self.cashflows))
                cal_ratios_survive[today >= self.coupon_end_dates] = 0
                fraction_flag = (today+1 == self.coupon_end_dates) & (self.coupon_end_dates == self.coupon_payment_dates)
                cal_ratios_survive[fraction_flag] = 1 / self.year_fractions[fraction_flag] \
                    * get_year_fraction(self.daycount, today, today+1, day_stub='IncludeFirstIncludeEnd')
                cal_ratios_default = cal_ratios_survive[:]
        return cal_ratios_survive, cal_ratios_default
        
    
    def _get_npv_coupon_survive(self, today, discount_curve, credit_curve, cal_ratios_survive):
        cal_flag = cal_ratios_survive != 0                
        if sum(cal_flag) == 0:
            return 0.0
        else:
            return self._get_sum_npv_func(today, discount_curve, credit_curve,
                                          self.coupon_determination_dates[cal_flag], None,
                                          cal_ratios_survive[cal_flag],
                                          self.cashflows[cal_flag],
                                          None, self.coupon_payment_dates[cal_flag])
            
        
    def _get_npv_coupon_default(self, today, discount_curve, credit_curve, cal_ratios_default):        
        if (self.coupon_pay_front) & (self.accrual_coupon_type == 'ToPeriodEndDate'):
            return 0.0
        if (not self.coupon_pay_front) & (self.accrual_coupon_type == 'Zero'):
            return 0.0

        cal_flag = cal_ratios_default != 0
        if sum(cal_flag) == 0:
            return 0.0
        
        if (self.coupon_pay_front) & (self.accrual_coupon_type == 'ToDefaultDate'):
            payment_amount_fixed_parts = self.notional * self.coupon_rate
            accrual_pillar_dates = self.coupon_end_dates[cal_flag]
        elif (self.coupon_pay_front) & (self.accrual_coupon_type == 'Zero'):
            payment_amount_fixed_parts = - self.cashflows[cal_flag]
            accrual_pillar_dates = None
        elif (not self.coupon_pay_front) & (self.accrual_coupon_type == 'ToDefaultDate'):
            payment_amount_fixed_parts = self.notional * self.coupon_rate
            accrual_pillar_dates = self.coupon_start_dates[cal_flag]
        elif (not self.coupon_pay_front) & (self.accrual_coupon_type == 'ToPeriodEndDate'):
            payment_amount_fixed_parts = self.cashflows[cal_flag]
            accrual_pillar_dates = None
        
        if self.accrual_coupon_payment_date_type == 'DefaultDate':
            payment_dates = None
        elif self.accrual_coupon_payment_date_type == 'PaymentDate':
            payment_dates = self.coupon_payment_dates[cal_flag]

        period_start_dates = self.coupon_start_dates[cal_flag] - 1
        period_start_dates[0] = max(today, period_start_dates[0])
        period_end_dates = self.coupon_end_dates[cal_flag]
        return self._get_sum_npv_func(today, discount_curve, credit_curve,
                                      period_start_dates, period_end_dates,
                                      cal_ratios_default[cal_flag],
                                      payment_amount_fixed_parts, 
                                      accrual_pillar_dates, payment_dates)
    
    
    def _get_npv_protection(self, today, discount_curve, credit_curve, recovery_rate):
        cal_flag = self.protection_end_dates > today
        if sum(cal_flag) == 0:
            return 0.0
        
        if self.protection_payment_date_type == 'DefaultDate':
            period_start_dates = np.array([max(today, self.protection_start_dates[0]-1)])
            period_end_dates = np.array([self.protection_end_dates[-1]])
            payment_dates = None
        elif self.protection_payment_date_type == 'PeriodEndDate':
            period_start_dates = self.protection_start_dates[cal_flag] - 1
            period_end_dates = self.protection_end_dates[cal_flag]
            payment_dates = period_end_dates[:]

        return self._get_sum_npv_func(today, discount_curve, credit_curve,
                                      period_start_dates, period_end_dates, 
                                      np.array([1]), self.notional*(1 - recovery_rate),
                                      None, payment_dates)


    def _get_sum_npv_func(self, today, discount_curve, credit_curve,
                          period_start_dates, period_end_dates,
                          cal_ratios, payment_amount_fixed_parts,
                          accrual_pillar_dates, payment_dates):
        
        cal_ratios = cal_ratios.astype(float)
        
        if (type(payment_dates) != type(None)) & (type(accrual_pillar_dates) == type(None)):
            return self._get_sum_npv_base(today, discount_curve, credit_curve, 
                                          period_start_dates, period_end_dates, 
                                          cal_ratios, payment_amount_fixed_parts, payment_dates)
        else:
            def gen_repeat(param):
                return param if isinstance(param, np.ndarray) else repeat(param, len(cal_ratios))
            npv_parts = np.array([self._get_npv_day_by_day(today, discount_curve, credit_curve,
                                                           period_start_date, period_end_date,
                                                           payment_amount_fixed_part,
                                                           accrual_pillar_date, payment_date)
                                  for period_start_date, period_end_date,
                                  payment_amount_fixed_part, accrual_pillar_date, payment_date
                                  in zip(period_start_dates, period_end_dates,
                                         gen_repeat(payment_amount_fixed_parts),
                                         gen_repeat(accrual_pillar_dates),
                                         gen_repeat(payment_dates))])
            return sum(npv_parts * cal_ratios)
        
        
    def _get_sum_npv_base(self, today, discount_curve, credit_curve, 
                          period_start_dates, period_end_dates, 
                          cal_ratios, payment_amounts, payment_dates,
                          output_full_info=False):
        
        cal_ratios = cal_ratios.astype(float)

        # 计算折现因子
        discount_func = discount_curve.curve.discount
        discount_factors = np.vectorize(discount_func)(payment_dates) / discount_func(today)
        
        # 计算信用事件概率
        survival_func = credit_curve.curve.survival_probability
        if type(period_start_dates) == type(None):
            survival_probabilities_left = survival_func(today)
        else:
            survival_probabilities_left = np.vectorize(survival_func)(period_start_dates)
        if type(period_end_dates) == type(None):
            survival_probabilities_right = 0
        else:
            survival_probabilities_right = np.vectorize(survival_func)(period_end_dates)
        event_probabilities = (survival_probabilities_left - survival_probabilities_right) / survival_func(today)
        
        npv_parts = payment_amounts * discount_factors * event_probabilities
        npv_parts_cal = npv_parts * cal_ratios
        npv = sum(npv_parts_cal)

        if not output_full_info:
            return npv
        
        return npv, payment_dates, payment_amounts, discount_factors, event_probabilities, npv_parts, cal_ratios, npv_parts_cal


    def _get_npv_day_by_day(self, today, discount_curve, credit_curve,
                            period_start_date, period_end_date,
                            payment_amount_fixed_part,
                            accrual_pillar_date, payment_date):
        
        all_dates = ql.NullCalendar().businessDayList(period_start_date, period_end_date)
        all_start_dates = all_dates[:-1]
        all_end_dates = all_dates[1:]
        
        if type(accrual_pillar_date) == type(None):
            payment_amounts = payment_amount_fixed_part
        else:
            if not self.coupon_pay_front:
                payment_amounts = payment_amount_fixed_part * np.array([
                    get_year_fraction(self.daycount, accrual_pillar_date, date)
                    for date in all_end_dates])
            else:
                payment_amounts = - payment_amount_fixed_part * np.array([
                    get_year_fraction(self.daycount, date, accrual_pillar_date,
                                      day_stub='IncludeFirstIncludeEnd')
                    for date in all_end_dates])
        
        if type(payment_date) == type(None):
            payment_dates = all_end_dates
        else:
            payment_dates = payment_date
        
        return self._get_sum_npv_base(today, discount_curve, credit_curve,
                                      all_start_dates, all_end_dates,
                                      np.array([1]), payment_amounts, payment_dates)
    
    
    def dv01_spread(self, today, discount_curve, credit_curve, valuation_mode='FI', tweak=1):
        credit_curve_up = credit_curve.tweak_parallel(tweak)
        pv_up = self.npv(today, discount_curve, credit_curve_up)
        credit_curve_down = credit_curve.tweak_parallel(-tweak)
        pv_down = self.npv(today, discount_curve, credit_curve_down)
        return (pv_up - pv_down) / (2 * tweak)
    
    
    def dv01_ir(self, today, discount_curve, credit_curve, valuation_mode='FI', tweak=1e-4, credit_curve_change=True):
        if credit_curve_change:
            discount_curve_up = discount_curve.tweak_parallel(tweak)
            credit_curve_up = credit_curve.tweak_discount(tweak)
            pv_up = self.npv(today, discount_curve_up, credit_curve_up)
            discount_curve_down = discount_curve.tweak_parallel(-tweak)
            credit_curve_down = credit_curve.tweak_discount(-tweak)
            pv_down = self.npv(today, discount_curve_down, credit_curve_down)
        else:
            discount_curve_up = discount_curve.tweak_parallel(tweak)
            pv_up = self.npv(today, discount_curve_up, credit_curve)
            discount_curve_down = discount_curve.tweak_parallel(-tweak)
            pv_down = self.npv(today, discount_curve_down, credit_curve)
        return (pv_up - pv_down) / (2 * tweak) * 1e-4


    def cashflow_schedule(self, today, discount_curve, credit_curve, valuation_mode='FI'):
        show_flag = self.coupon_payment_dates > today
        if sum(show_flag) == 0:
            return pd.DataFrame()

        cal_ratios_survive, _ = self._get_coupon_cal_ratios(today, valuation_mode)
        npv, payment_dates, payment_amounts, discount_factors, event_probabilities, npv_parts, cal_ratios, npv_parts_cal \
            = self._get_sum_npv_base(today, discount_curve, credit_curve, 
                                     self.coupon_determination_dates[show_flag], None,
                                     cal_ratios_survive[show_flag],
                                     self.cashflows[show_flag],
                                     self.coupon_payment_dates[show_flag], True)        
        
        df = pd.DataFrame({'Date': [ql_date_str(date) for date in payment_dates],
                           'Act Cashflow': payment_amounts,
                           'Disc Factor': discount_factors,
                           'Survival Prob': event_probabilities,
                           'Disc Cashflow (Full)': npv_parts,
                           'Cal Ratio': cal_ratios,
                           'Disc Cashflow (Cal)': npv_parts_cal})
        add_sum_row = pd.DataFrame({'Date': ['Total'],
                                    'Act Cashflow': [sum(df['Act Cashflow'])],
                                    'Disc Factor': [''],
                                    'Survival Prob': [''],
                                    'Disc Cashflow (Full)': [sum(df['Disc Cashflow (Full)'])],
                                    'Cal Ratio': [''],
                                    'Disc Cashflow (Cal)': [npv]})
        df = pd.concat([df, add_sum_row], ignore_index=True)
        return df


    def price_calculation(self, today, discount_curve, credit_curve, valuation_mode='FI', 
                          settle_date=None, settle_calendar_type=None):
        
        inst = Cds(self.direction, self.notional, self.effective_date, self.maturity_date,
                   0, today, self.coupon_pay_front, self.spread, self.daycount,
                   self.coupon_start_dates, self.coupon_end_dates, self.coupon_payment_dates,
                   self.accrual_coupon_type, self.accrual_coupon_payment_date_type,
                   self.protection_start_dates, self.protection_end_dates,
                   self.protection_payment_date_type, self.recovery_rate)
        npv = inst.npv(today, discount_curve, credit_curve, valuation_mode)
        
        if type(settle_date) == type(None):
            settle_date = get_settle_date(today, settle_calendar_type)
        cash_amount = npv / discount_curve.curve.discount(settle_date)
        if self.coupon_pay_front:
            return {'Settle Date:': ql_date_str(settle_date),
                    'Cash Amount:': cash_amount}
        
        if valuation_mode == 'FI':
            remain_flag = self.coupon_payment_dates > today
            if sum(remain_flag) == 0:
                accrued_coupon = 0
                txt = 'Accrued (0 days):'
            else:
                first_coupon_start_date = self.coupon_start_dates[remain_flag][0]
                first_coupon_end_date = self.coupon_end_dates[remain_flag][0]
                if sum(remain_flag) == 1:
                    accrued_to_date = min(today, first_coupon_end_date)
                    accrued_coupon = self.notional * self.coupon_rate * get_year_fraction(
                        self.daycount, first_coupon_start_date, accrued_to_date, day_stub='IncludeFirstIncludeEnd')
                    txt = f'Accrued ({accrued_to_date - first_coupon_start_date + 1} days):'
                else:
                    accrued_coupon = self.notional * self.coupon_rate * get_year_fraction(
                        self.daycount, first_coupon_start_date, today, day_stub='IncludeFirstIncludeEnd')
                    if today <= first_coupon_end_date:
                        txt = f'Accrued ({today - first_coupon_start_date + 1} days):'
                    else:
                        txt = f'Accrued ({first_coupon_end_date - first_coupon_start_date + 1} + {today - first_coupon_end_date} days):'

        elif valuation_mode == 'BBG':
            remain_flag = self.coupon_end_dates > today
            if sum(remain_flag) == 0:
                accrued_coupon = 0
                txt = 'Accrued (0 days):'
            else:
                first_coupon_start_date = self.coupon_start_dates[remain_flag][0]
                first_coupon_end_date = self.coupon_end_dates[remain_flag][0]
                if (sum(remain_flag) == 1) & (today + 1 == first_coupon_end_date):
                    accrued_coupon = 0
                    txt = 'Accrued (0 days):'
                else:
                    accrued_coupon = self.notional * self.coupon_rate * get_year_fraction(
                        self.daycount, first_coupon_start_date, today, day_stub='IncludeFirstIncludeEnd')
                    txt = f'Accrued ({today - first_coupon_start_date + 1} days):'
            
        accrued_coupon *= -1 if self.direction == 'long' else 1
        principal = cash_amount - accrued_coupon
        price = 100 * (1 - principal / self.notional) if self.direction == 'long' \
            else 100 * (1 + principal / self.notional)

        return {'Settle Date:': ql_date_str(settle_date),
                'Price:': price,
                'Principal:': principal,
                txt: accrued_coupon,
                'Cash Amount:': cash_amount}
