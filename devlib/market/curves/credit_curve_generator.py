# -*- coding: utf-8 -*-
"""
Created on Mon Aug 19 10:46:33 2024

@author: Guanzhifan
"""

import sys
import os
parant_folder_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
sys.path.append(parant_folder_path)


import QuantLib as ql
import pandas as pd
import numpy as np
import copy
from scipy import optimize
from typing import Union

from utils.cds_utils import cds_maturity_date, adjusted_oldcds_schedule
from utils.ql_date_utils import ql_date
from products.credit.cds import Cds

#%%
class CdsConfig:
    def __init__(
            self,
            recovery_rate: float,
            daycount: ql.DayCounter,
            calendar: ql.Calendar):
        self.recovery_rate = recovery_rate
        self.daycount = daycount
        self.calendar = calendar

        
    def generate_curve_cds_info(
            self,
            step_in_date: ql.Date,
            maturity_date: ql.Date, 
            spread: float):
        
        coupon_schedule = adjusted_oldcds_schedule(step_in_date, maturity_date, self.calendar)
        coupon_start_dates = np.array(coupon_schedule[:-1])
        coupon_end_dates = np.array(coupon_schedule[1:])
        coupon_end_dates[:-1] -= 1
        coupon_payment_dates = np.array(coupon_schedule[1:])
        coupon_payment_dates[-1] = self.calendar.adjust(coupon_payment_dates[-1])
        
        inst = Cds('long', 1e7, coupon_start_dates[0], coupon_end_dates[-1],
                   0, step_in_date, False, spread, self.daycount,
                   coupon_start_dates, coupon_end_dates, coupon_payment_dates,
                   'ToDefaultDate', 'DefaultDate', 
                   None, None, 'DefaultDate', self.recovery_rate)
        return inst

    

#%%
class BasicCreditCurve:
    def __init__(
            self,
            today: ql.Date,
            hazard_rate_series: pd.Series,
            daycount: ql.DayCounter
            ):
        self.today = today
        self.hazard_rate_series = copy.copy(hazard_rate_series.sort_index())
        self.daycount = daycount
        self.basic_interp_func = ql.BackwardFlatInterpolation
        
        self.interp_xs = [self.daycount.yearFraction(self.today, date)
                          for date in self.hazard_rate_series.index]
        self.update_curve(self.hazard_rate_series.values)
        
            
    # update interpolation infomation
    def update_curve(self, interp_ys):
        self.interp_ys = list(interp_ys)
        self.curve_interp_func = self.basic_interp_func(self.interp_xs, self.interp_ys)
        
        
    # curve function
    def hazard_rate(self, date):
        x = self.daycount.yearFraction(self.today, date)
        return self.curve_interp_func(x, allowExtrapolation=True)
    
    
    def survival_probability(self, date):
        x = self.daycount.yearFraction(self.today, date)
        if x <= 0:
            return 1.0
        index = np.searchsorted(self.interp_xs, x)
        if index == len(self.interp_xs):
            index -= 1
        integration_xs = np.array(self.interp_xs)[: index + 1]
        integration_xs[index] = x
        integration_xs = [integration_xs[0]] + list(np.diff(integration_xs))
        integration_ys = np.array(self.interp_ys)[: index + 1]
        integration = np.dot(integration_xs, integration_ys)
        return np.exp(-integration)



class ParameterCreditCurve:
    def __init__(
            self,
            today: ql.Date,
            entity: str,
            parameter: Union[pd.Series, float],
            daycount: ql.DayCounter, 
            recovery_rate: float = 0.4,
            parameter_type: str = 'constant_spread'
            ):
        
        self.today = today
        self.entity = entity
        if parameter_type == 'constant_spread':
            self.parameter_type = 'spread'
            self.parameter_series = pd.Series([parameter], index=[today+365], dtype=float)
        elif parameter_type == 'constant_hazard_rate':
            self.parameter_type = 'hazard_rate'
            self.parameter_series = pd.Series([parameter], index=[today+365], dtype=float)
        else:
            self.parameter_type = parameter_type
            self.parameter_series = copy.copy(parameter)
        self.daycount = daycount
        self.recovery_rate = recovery_rate
        
        self.curve = self.build_curve()


    def build_curve(self):
        if self.parameter_type == 'hazard_rate':
            return BasicCreditCurve(self.today, self.parameter_series, self.daycount)
        elif self.parameter_type == 'spread':
            hazard_rates = -np.log(1 - np.array(self.parameter_series.values) / (1- self.recovery_rate))
            hazard_rates_series = pd.Series(hazard_rates, self.parameter_series.index)
            return BasicCreditCurve(self.today, hazard_rates_series, self.daycount)
        elif self.parameter_type == 'survival_probability':
            parameter_series = copy.copy(self.parameter_series.sort_index())
            neg_ln_survival_probabilities = -np.log(parameter_series.values)
            interval_probabilities = [neg_ln_survival_probabilities[0]] + list(np.diff(neg_ln_survival_probabilities))
            interp_xs = [self.daycount.yearFraction(self.today, date)
                         for date in self.parameter_series.index]
            interval_xs = [interp_xs[0]] + list(np.diff(interp_xs))
            hazard_rates = np.array(interval_probabilities) / np.array(interval_xs)
            hazard_rates_series = pd.Series(hazard_rates, parameter_series.index)
            return BasicCreditCurve(self.today, hazard_rates_series, self.daycount)
        elif self.parameter_type == 'default_probability':
            return ParameterCreditCurve(self.today, self.entity, 1-self.parameter_series, self.daycount,
                                        self.recovery_rate, 'survival_probability').curve
        else:
            raise Exception(f'Unsupported interpolation method: {self.parameter_type}!')
            
            
    def tweak_parallel(self, tweak):
        hazard_rates_series = self.curve.hazard_rate_series
        coupon_rates = (1 - self.recovery_rate) * (1 - np.exp(-hazard_rates_series.values))
        hazard_rates_tweaked = -np.log(1 - (coupon_rates + tweak/1e4) / (1 - self.recovery_rate))
        hazard_rates_series_tweaked = pd.Series(hazard_rates_tweaked, hazard_rates_series.index)
        curve_tweak = self.__class__(self.today, self.entity, hazard_rates_series_tweaked, self.daycount,
                                     self.recovery_rate, 'hazard_rate')
        return curve_tweak



class MarketDataCreditCurve:
    def __init__(
            self,
            today: ql.Date,
            entity: str,
            cds_data: pd.DataFrame,
            discount_curve,
            cds_type: str,
            cds_config: CdsConfig,
            daycount: ql.DayCounter
            ):
        
        self.today = today
        self.entity = entity
        self.cds_data = copy.copy(cds_data)
        self.discount_curve = discount_curve
        self.cds_type = cds_type
        self.cds_config = cds_config
        self.daycount = daycount
        self.recovery_rate = self.cds_config.recovery_rate

        self.curve = self.build_curve()


    def build_curve(self):
        
        if self.cds_type == 'single_name':
            maturity_dates = [cds_maturity_date(self.today, tenor) for tenor in self.cds_data['Tenor']]
        elif self.cds_type == 'index':
            maturity_dates = [ql_date(maturity) for maturity in self.cds_data['Maturity']]
        insts = self._get_constuction_tools(maturity_dates)
        num = len(maturity_dates)
        init_hazard_rates = np.array([0.005] * num)
        hazard_rate_series = pd.Series(init_hazard_rates, index=maturity_dates, dtype=float)
        credit_curve = ParameterCreditCurve(self.today, self.entity, hazard_rate_series, self.daycount, self.recovery_rate, 'hazard_rate')
        
        final_hazard_rates = init_hazard_rates[:]
        for i in range(num):
            inst = insts[i]
            tmp_hazard_rates = np.array(list(final_hazard_rates[:i]) + list(init_hazard_rates[i:]))
            def bootstrapping_func(x):
                tmp_hazard_rates[i] = x
                return self._bootstrapping_target(tmp_hazard_rates, credit_curve, inst)
            root = self._bootstrapping_root(bootstrapping_func)
            final_hazard_rates[i] = root
        
        credit_curve.curve.update_curve(final_hazard_rates)
        credit_curve.curve.hazard_rate_series[:] = list(final_hazard_rates)
        return credit_curve.curve
        
        
    def _get_constuction_tools(self, maturity_dates):
        step_in_date = self.today + 1
        insts = np.array([self.cds_config.generate_curve_cds_info(step_in_date, maturity_date, spread)
                          for maturity_date, spread in zip(maturity_dates, self.cds_data['Spread'])]).T
        return insts
    
    def _bootstrapping_target(self, new_hazard_rates, credit_curve, inst):
        credit_curve.curve.update_curve(new_hazard_rates)
        return inst.npv(self.today, self.discount_curve, credit_curve)

    def _bootstrapping_root(self, func):
        root = optimize.newton(func, 0.005, maxiter=100000, tol=1e-9)
        return root
    
    
    def mkt_data_tweak(self, tweak: float, tenor: str):
        cds_data_tweaked = self.cds_data.copy()
        if tenor == 'ALL':
            cds_data_tweaked['Spread'] += tweak
        else:
            cds_data_tweaked.loc[
                cds_data_tweaked.loc[:, 'Tenor'] == tenor, 'Spread'] += tweak
        return cds_data_tweaked
    
    def tweak_parallel(self, tweak):
        cds_data_tweaked = self.mkt_data_tweak(tweak, 'ALL')
        curve_tweak = self.__class__(self.today, self.entity, cds_data_tweaked, self.discount_curve,
                                     self.cds_type, self.cds_config,  self.daycount)
        return curve_tweak
    
    def tweak_discount(self, tweak):
        discount_curve_tweaked = self.discount_curve.tweak_parallel(tweak)
        curve_tweak = self.__class__(self.today, self.entity, self.cds_data, discount_curve_tweaked,
                                     self.cds_type, self.cds_config, self.daycount)
        return curve_tweak


    



