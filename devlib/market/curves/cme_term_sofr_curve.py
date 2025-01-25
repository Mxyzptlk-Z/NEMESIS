# -*- coding: utf-8 -*-
"""
Created on Mon Aug 12 17:00:20 2024

@author: Guanzhifan
"""

from abc import abstractmethod
from typing import Union
import copy
import pandas as pd
import numpy as np

import QuantLib as ql
import devlib.market.curves.curve_generator as cg
from devlib.market.curves.overnight_index_curves import Sofr
import devlib.utils.curve_utils as cu


class CmeTermSofrCurve:
    def __init__(
            self, 
            today: ql.Date, 
            deposit_mkt_data: pd.DataFrame, 
            base_curve_swap_mkt_data: pd.DataFrame,
            fixing_data: pd.DataFrame = pd.DataFrame(), 
            interpolation_method: str = 'PiecewiseLinearZero', 
            ):
        self.curve_config_set()
        self.name = self.index_config.curve_name
        self.ccy = self.index_config.currency.code()
        
        self.today = today
        self.deposit_mkt_data = copy.copy(deposit_mkt_data)
        self.base_curve_swap_mkt_data = copy.copy(base_curve_swap_mkt_data)
        self.fixing_data = copy.copy(fixing_data)
        self.interpolation_method = interpolation_method
        
        self.curve, self.index = self.build_curve()
    
        
    @abstractmethod    
    def curve_config_set(self):
        self.index_config = cg.IndexConfig()
        self.deposit_config = cg.DepositHelperConfig(
            settlement_delay=2, 
            calendar=ql.UnitedStates(ql.UnitedStates.FederalReserve), 
            convention=ql.ModifiedFollowing, 
            end_of_month=True, 
            daycount=ql.Actual360())
        
    
    def build_all_helpers(self):
        base_curve = Sofr(self.today, swap_mkt_data=self.base_curve_swap_mkt_data,
                          interpolation_method=self.interpolation_method)
        base_curve_curve = base_curve.curve

        deposit_tenors = [ql.Period(tenor) for tenor in self.deposit_mkt_data['Tenor']]
        swap_tenors = np.array([ql.Period(tenor) for tenor in self.base_curve_swap_mkt_data['Tenor']])
        max_deposit_tenor = max(deposit_tenors)
        min_deposit_tenor = min(deposit_tenors)
        self.base_curve_swap_mkt_data_greater = self.base_curve_swap_mkt_data.loc[
            swap_tenors > max_deposit_tenor, :].copy()
        self.base_curve_swap_mkt_data_less = self.base_curve_swap_mkt_data.loc[
            swap_tenors < min_deposit_tenor, :].copy()
        
        ## deposit_helpers
        deposit_helpers = [self.deposit_config.build_deposit_helper( 
            self.index_config.curve_name, self.index_config.currency, 
            self.deposit_mkt_data.loc[0, 'Tenor'], self.deposit_mkt_data.loc[0, 'Rate'])]
        
        ## add_deposit_helpers
        add_deposit_helpers = []
        if len(self.base_curve_swap_mkt_data_less) == 0:
            pass
        else:
            date_deposit_start = deposit_helpers[0].earliestDate()
            date_deposit_end = deposit_helpers[0].maturityDate()
            curve_init = ql.PiecewiseLinearZero(self.today, deposit_helpers, ql.Actual360())
            df_curve = curve_init.discount(date_deposit_end) / curve_init.discount(date_deposit_start)
            df_base_curve = base_curve_curve.discount(date_deposit_end) / base_curve_curve.discount(date_deposit_start)
            spread = - np.log(df_curve / df_base_curve) / ql.Actual365Fixed().yearFraction(date_deposit_start, date_deposit_end)

            pre_first_deposit_dates = base_curve_curve.dates()[1 : len(self.base_curve_swap_mkt_data_less) + 1]
            for date in pre_first_deposit_dates:
                zero_rate = base_curve_curve.zeroRate(date, ql.Actual365Fixed(), ql.Continuous).rate() + spread
                dcf = ql.Actual365Fixed().yearFraction(self.today, date)
                simple_rate = (np.exp(zero_rate * dcf) - 1) / dcf
                tenor_days = date - self.today
                add_deposit_helpers.append(ql.DepositRateHelper(
                    simple_rate, ql.Period(tenor_days, ql.Days), 0, ql.NullCalendar(), 
                    ql.Unadjusted, False, ql.Actual365Fixed()))
        
        ## add_swap_helpers
        add_swap_helpers = [base_curve.swap_config.build_swap_helper(
            self.base_curve_swap_mkt_data_greater.loc[idx, 'Tenor'], 
            self.base_curve_swap_mkt_data_greater.loc[idx, 'Rate'], 
            base_curve.index_config.build_index()) for idx in self.base_curve_swap_mkt_data_greater.index]  
        
        helpers = deposit_helpers + add_deposit_helpers + add_swap_helpers

        return helpers

        
    def build_curve(self):
        helpers = self.build_all_helpers()

        if self.interpolation_method == 'PiecewiseLinearZero':
            curve = ql.PiecewiseLinearZero(self.today, helpers, ql.Actual360())
        else:
            raise Exception(
                f'unsupported curve interpolation method: {self.interpolation_method}')

        curve.enableExtrapolation()
        
        curve_ts = ql.YieldTermStructureHandle(curve)
        index = self.index_config.build_index_with_curve_ts(curve_ts)
        # add fixing
        index = cu.add_fixing(index, self.index_config.calendar, self.fixing_data, self.today)

        return curve, index


    def mkt_data_tweak(self, data_type: str, tweak: float, tenor: Union[list, str]):
        if data_type == 'deposit':
            deposit_mkt_data_tweaked = self.deposit_mkt_data.copy()
            if tenor == 'ALL':
                deposit_mkt_data_tweaked['Rate'] += tweak
            else:
                deposit_mkt_data_tweaked.loc[
                    deposit_mkt_data_tweaked.loc[:, 'Tenor'] == tenor, 'Rate'] += tweak
            return deposit_mkt_data_tweaked
        
        elif data_type == 'base_curve_swap':
            swap_mkt_data_tweaked = self.base_curve_swap_mkt_data.copy()
            if tenor == 'ALL':
                swap_mkt_data_tweaked['Rate'] += tweak
            else:
                swap_mkt_data_tweaked.loc[swap_mkt_data_tweaked['Tenor'].isin(tenor), 'Rate'] += tweak
            return swap_mkt_data_tweaked
            
        else:
            raise Exception(f'unsupported data type: {data_type}')

    
    
    def tweak_parallel(self, tweak):
        deposit_mkt_data_tweaked = self.mkt_data_tweak('deposit', tweak, 'ALL')
        base_curve_swap_tweak_tenor = list(self.base_curve_swap_mkt_data_greater['Tenor'])
        # base_curve_swap_tweak_tenor = 'ALL'
        base_curve_swap_mkt_data_tweaked = self.mkt_data_tweak('base_curve_swap', tweak, base_curve_swap_tweak_tenor)
        
        curve_tweak = self.__class__(
            self.today, deposit_mkt_data_tweaked, base_curve_swap_mkt_data_tweaked,
            self.fixing_data, self.interpolation_method)
        
        return curve_tweak
    
    
    def tweak_keytenor(self, tweak, tenor='ALL'):
        deposit_tenor = list(self.deposit_mkt_data['Tenor'])
        base_curve_swap_tenors = list(self.base_curve_swap_mkt_data_greater['Tenor'])
        
        if tenor == 'ALL':
            all_tweaked_curves = dict()
            for tenor in deposit_tenor:
                deposit_mkt_data_tweaked = self.mkt_data_tweak('deposit', tweak, tenor)
                curve_tweak = self.__class__(
                    self.today, deposit_mkt_data_tweaked, self.base_curve_swap_mkt_data,
                    self.fixing_data, self.interpolation_method)
                all_tweaked_curves[tenor] = curve_tweak

            for tenor in base_curve_swap_tenors:
                base_curve_swap_mkt_data_tweak = self.mkt_data_tweak('base_curve_swap', tweak, [tenor])
                curve_tweak = self.__class__(
                    self.today, self.deposit_mkt_data, base_curve_swap_mkt_data_tweak,
                    self.fixing_data, self.interpolation_method)
                all_tweaked_curves[tenor] = curve_tweak

            return all_tweaked_curves

        elif tenor in deposit_tenor:
            deposit_mkt_data_tweaked = self.mkt_data_tweak('deposit', tweak, tenor)
            curve_tweak = self.__class__(
                self.today, deposit_mkt_data_tweaked, self.base_curve_swap_mkt_data,
                self.fixing_data, self.interpolation_method)
            return curve_tweak

        elif tenor in base_curve_swap_tenors:
            base_curve_swap_mkt_data_tweak = self.mkt_data_tweak('base_curve_swap', tweak, [tenor])
            curve_tweak = self.__class__(
                self.today, self.deposit_mkt_data, base_curve_swap_mkt_data_tweak,
                self.fixing_data, self.interpolation_method)
            return curve_tweak

        else:
            raise Exception(f'Invalid tenor: {tenor}!')



#%%
class CmeTermSofr3M(CmeTermSofrCurve):    
    def curve_config_set(self):
        super().curve_config_set()
        self.index_config = cg.IborIndexConfig(
            curve_name='TERMSOFR3M', 
            tenor='3M', 
            settlement_delay=2, 
            currency=ql.USDCurrency(),
            calendar=ql.Sofr().fixingCalendar(), 
            convention=ql.ModifiedFollowing, 
            end_of_month=True, 
            daycount=ql.Actual360())


class CmeTermSofr1M(CmeTermSofrCurve):
    def curve_config_set(self):
        super().curve_config_set()
        self.index_config = cg.IborIndexConfig(
            curve_name='TERMSOFR1M', 
            tenor='1M', 
            settlement_delay=2, 
            currency=ql.USDCurrency(),
            calendar=ql.Sofr().fixingCalendar(), 
            convention=ql.ModifiedFollowing, 
            end_of_month=True, 
            daycount=ql.Actual360())


class CmeTermSofr6M(CmeTermSofrCurve):
    def curve_config_set(self):
        super().curve_config_set()
        self.index_config = cg.IborIndexConfig(
            curve_name='TERMSOFR6M', 
            tenor='6M', 
            settlement_delay=2, 
            currency=ql.USDCurrency(),
            calendar=ql.Sofr().fixingCalendar(), 
            convention=ql.ModifiedFollowing, 
            end_of_month=True, 
            daycount=ql.Actual360())


class CmeTermSofr12M(CmeTermSofrCurve):
    def curve_config_set(self):
        super().curve_config_set()
        self.index_config = cg.IborIndexConfig(
            curve_name='TERMSOFR12M', 
            tenor='12M', 
            settlement_delay=2, 
            currency=ql.USDCurrency(),
            calendar=ql.Sofr().fixingCalendar(), 
            convention=ql.ModifiedFollowing, 
            end_of_month=True, 
            daycount=ql.Actual360())



