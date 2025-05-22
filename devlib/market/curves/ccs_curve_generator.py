# -*- coding: utf-8 -*-
"""
Created on Mon Aug 19 10:46:33 2024

@author: Guanzhifan
"""

from abc import abstractmethod
from typing import Union

import QuantLib as ql
import pandas as pd
import numpy as np
import copy

import devlib.market.curves.curve_generator as cg
from devlib.utils.fx_utils import get_pair_tweak_param



class DiscountCurveConfig:
    def __init__(self,
                 curve_name: str, 
                 currency: ql.Currency):
        
        self.curve_name = curve_name
        self.currency = currency
    
    

class FxSwapConfig:
    def __init__(self,
                 fx_pair: str,
                 settlement_delay: int,
                 calendar: ql.Calendar,
                 convention: int, 
                 end_of_month: bool,
                 is_collateral_ccy_base_ccy: bool, #collateral_ccy==f_ccy
                 tweak_daycount: ql.DayCounter): 
        
        self.fx_pair = fx_pair
        self.settlement_delay = settlement_delay
        self.calendar = calendar
        self.convention = convention
        self.end_of_month = end_of_month
        self.is_collateral_ccy_base_ccy = is_collateral_ccy_base_ccy
        self.tweak_daycount = tweak_daycount
       
        
    @abstractmethod
    def build_fx_swap_helper(self, 
                             tenor: str,
                             spread: float,
                             spot: float,
                             collateral_discount_curve_yts: ql.YieldTermStructureHandle):
        
        hp = ql.FxSwapRateHelper(
            ql.QuoteHandle(ql.SimpleQuote(spread)), ql.QuoteHandle(ql.SimpleQuote(spot)),
            ql.Period(tenor), self.settlement_delay, self.calendar, self.convention,
            self.end_of_month, self.is_collateral_ccy_base_ccy, collateral_discount_curve_yts)
        
        return hp



class FixedToOisCcsConfig:
    def __init__(self, 
                 settlement_delay: int,
                 calendar: ql.Calendar,
                 payment_lag: int,
                 payment_convention: int,
                 payment_freq: int,
                 fixed_daycount: ql.DayCounter, 
                 forward_start: int):
        
        self.settlement_delay = settlement_delay
        self.calendar = calendar
        self.payment_lag = payment_lag
        self.payment_convention = payment_convention
        self.payment_freq = payment_freq
        self.fixed_daycount = fixed_daycount
        self.forward_start = forward_start        
        
    
    @abstractmethod
    def generate_ois_index(self, curve_name, currency):
        self.target_ois_index = ql.OvernightIndex(
            curve_name, 0, currency, self.calendar, self.fixed_daycount)
        
    @abstractmethod
    def build_ccs_helper(self, 
                         tenor: str, 
                         rate: float):
        
        if ql.Period(tenor) > ql.Period(self.payment_freq):
            pillar_date_type = ql.Pillar.LastRelevantDate
        else:
            pillar_date_type = ql.Pillar.MaturityDate
        hp = ql.OISRateHelper(
            self.settlement_delay, ql.Period(tenor), 
            ql.QuoteHandle(ql.SimpleQuote(rate)), self.target_ois_index,
            ql.YieldTermStructureHandle(), True, self.payment_lag,
            self.payment_convention, self.payment_freq, self.calendar,
            ql.Period(str(self.forward_start) + 'D'),
            0, pillar_date_type, ql.Date())
        
        return hp



class FloatToFloatCcsConfig:
    def __init__(self,
                 settlement_delay: int,
                 calendar: ql.Calendar,
                 convention: int, 
                 end_of_month: bool,
                 target_index_config: cg.IborIndexConfig,
                 collateral_index_config: cg.IborIndexConfig,
                 is_basis_on_target_leg: bool,
                 is_target_leg_resettable: Union[None, bool] = None):
        
        self.settlement_delay = settlement_delay
        self.calendar = calendar
        self.convention = convention
        self.end_of_month = end_of_month
        self.target_index_config = target_index_config
        self.collateral_index_config = collateral_index_config
        self.is_basis_on_target_leg = is_basis_on_target_leg

        if is_target_leg_resettable == None:
            self.build_ccs_helper_func = self.build_not_mtm_ccs_helper
        else:
            self.is_target_leg_resettable = is_target_leg_resettable
            self.build_ccs_helper_func = self.build_mtm_ccs_helper
    
    
    @abstractmethod
    def generate_ccs_index(self, target_index_curve, collateral_index_curve):
        self.target_index = self.generate_index(
            target_index_curve, self.target_index_config)
        self.collateral_index = self.generate_index(
            collateral_index_curve, self.collateral_index_config)
    
    
    def generate_index(self, index_curve, index_config):
        index = index_curve.index
        if index.tenor() == index_config.tenor:
            return index
        return index_config.build_index_with_curve_ts(ql.YieldTermStructureHandle(index_curve.curve))
        
    
    @abstractmethod
    def build_ccs_helper(self,
                         tenor: str,
                         basis: float,
                         collateral_discount_curve_yts: ql.YieldTermStructureHandle):
        
        return self.build_ccs_helper_func(tenor, basis, collateral_discount_curve_yts)
    
    
    def build_not_mtm_ccs_helper(self,
                                 tenor: str,
                                 basis: float,
                                 collateral_discount_curve_yts: ql.YieldTermStructureHandle):
        
        hp = ql.ConstNotionalCrossCurrencyBasisSwapRateHelper(
            ql.QuoteHandle(ql.SimpleQuote(basis)), ql.Period(tenor),
            self.settlement_delay, self.calendar, self.convention, self.end_of_month,
            self.target_index, self.collateral_index, collateral_discount_curve_yts,
            False, self.is_basis_on_target_leg)
            
        return hp
    

    def build_mtm_ccs_helper(self,
                             tenor: str,
                             basis: float,
                             collateral_discount_curve_yts: ql.YieldTermStructureHandle):
        
        hp = ql.MtMCrossCurrencyBasisSwapRateHelper(
            ql.QuoteHandle(ql.SimpleQuote(basis)), ql.Period(tenor),
            self.settlement_delay, self.calendar, self.convention, self.end_of_month,
            self.target_index, self.collateral_index, collateral_discount_curve_yts,
            False, self.is_basis_on_target_leg, self.is_target_leg_resettable)
            
        return hp



class CcsCurve:
    def __init__(self, 
                 today: ql.Date,
                 collateral_index_curve,
                 collateral_discount_curve,
                 ccs_mkt_data: pd.DataFrame, 
                 fx_swap_mkt_data: pd.DataFrame = pd.DataFrame(), 
                 target_index_curve = None,
                 interpolation_method: str = 'PiecewiseLinearZero'):
        
        self.curve_config_set()
        self.curve_name = self.curve_config.curve_name
        self.ccy = self.curve_config.currency.code()
        self.today = today
        self.collateral_index_curve = collateral_index_curve
        self.collateral_discount_curve = collateral_discount_curve
        self.ccs_mkt_data = copy.copy(ccs_mkt_data)
        self.fx_swap_mkt_data = copy.copy(fx_swap_mkt_data)
        self.target_index_curve = target_index_curve
        self.interpolation_method = interpolation_method
        
        self.curve = self.build_curve()
        
        
    @abstractmethod
    def curve_config_set(self):
        self.curve_config = None
        self.ccs_config = None
        self.fx_swap_config = None  
    
    
    @abstractmethod
    def build_all_helpers(self):   
        collateral_discount_curve_yts = ql.YieldTermStructureHandle(self.collateral_discount_curve.curve)
        
        if self.fx_swap_config == None:
            fx_swap_helpers = [] 
        else:   
            spot = self.fx_swap_mkt_data.loc[self.fx_swap_mkt_data['Tenor']=='SPOT', 'Spread'].values[0]
            pair_tweak_param = get_pair_tweak_param(self.fx_swap_config.fx_pair)
            fx_swap_helpers = [self.fx_swap_config.build_fx_swap_helper(
                self.fx_swap_mkt_data.loc[idx, 'Tenor'], self.fx_swap_mkt_data.loc[idx, 'Spread']/pair_tweak_param,
                spot, collateral_discount_curve_yts)
                for idx in self.fx_swap_mkt_data[self.fx_swap_mkt_data['Tenor']!='SPOT'].index]

        if type(self.ccs_config) == FixedToOisCcsConfig:
            self.ccs_config.generate_ois_index(self.curve_config.curve_name+'_OIS', self.curve_config.currency)
            ccs_helpers = [self.ccs_config.build_ccs_helper(
                self.ccs_mkt_data.loc[idx, 'Tenor'], self.ccs_mkt_data.loc[idx, 'Rate'])
                for idx in self.ccs_mkt_data.index]
        elif type(self.ccs_config) == FloatToFloatCcsConfig:
            self.ccs_config.generate_ccs_index(self.target_index_curve, self.collateral_index_curve)
            ccs_helpers = [self.ccs_config.build_ccs_helper(
                self.ccs_mkt_data.loc[idx, 'Tenor'], self.ccs_mkt_data.loc[idx, 'Basis']/10000,
                collateral_discount_curve_yts) for idx in self.ccs_mkt_data.index]
        else:
            raise Exception(f'Unsupported ccs config type: {type(self.ccs_config)}!')
                
        return fx_swap_helpers + ccs_helpers
        

    @abstractmethod
    def build_curve(self):
        helpers = self.build_all_helpers()        

        if self.interpolation_method == 'PiecewiseLinearZero':
            curve = ql.PiecewiseLinearZero(self.today, helpers, ql.Actual360())
        else:
            raise Exception(
                f'Unsupported curve interpolation method: {self.interpolation_method}')
            
        curve.enableExtrapolation()
        
        return curve
    
    
    def mkt_data_tweak(self, data_type: str, tweak: float, tenor: Union[list, str]):
        if data_type == 'fx':
            if tenor == 'ALL':
                tenor = list(self.fx_swap_mkt_data.loc[self.fx_swap_mkt_data['Tenor']!='SPOT','Tenor'])
            
            fx_swap_mkt_data_tweaked = self.fx_swap_mkt_data.copy()
            
            fx_spot = self.fx_swap_mkt_data.loc[self.fx_swap_mkt_data['Tenor']=='SPOT', 'Spread'].values[0]
            fx_pair_tweak_param = get_pair_tweak_param(self.fx_swap_config.fx_pair)
            fx_start_date = self.fx_swap_config.calendar.advance(self.today, self.fx_swap_config.settlement_delay, ql.Days)
            for idx in fx_swap_mkt_data_tweaked.index:
                fx_tenor = fx_swap_mkt_data_tweaked.loc[idx,'Tenor']
                if fx_tenor in tenor:
                    spread = fx_swap_mkt_data_tweaked.loc[idx,'Spread']
                    date = self.fx_swap_config.calendar.advance(
                        fx_start_date, ql.Period(fx_tenor),
                        self.fx_swap_config.convention, self.fx_swap_config.end_of_month)
                    year_fraction = self.fx_swap_config.tweak_daycount.yearFraction(fx_start_date, date)
                    forward = fx_spot + spread / fx_pair_tweak_param
                    forward_tweaked = forward * np.exp(tweak * year_fraction)
                    spread_tweaked = (forward_tweaked - fx_spot) * fx_pair_tweak_param
                    fx_swap_mkt_data_tweaked.loc[idx,'Spread'] = spread_tweaked
            return fx_swap_mkt_data_tweaked
        
        elif data_type == 'fixed_to_ois_ccs':
            ccs_mkt_data_tweaked = self.ccs_mkt_data.copy()
            if tenor == 'ALL':
                ccs_mkt_data_tweaked['Rate'] += tweak
            else:
                ccs_mkt_data_tweaked.loc[ccs_mkt_data_tweaked['Tenor'].isin(tenor), 'Rate'] += tweak
            return ccs_mkt_data_tweaked
            
        elif data_type == 'float_to_float_ccs':
            ccs_mkt_data_tweaked = self.ccs_mkt_data.copy()
            if tenor == 'ALL':
                ccs_mkt_data_tweaked['Basis'] += tweak*10000
            else:
                ccs_mkt_data_tweaked.loc[ccs_mkt_data_tweaked['Tenor'].isin(tenor), 'Basis'] += tweak*10000
            return ccs_mkt_data_tweaked

        else:
            raise Exception(f'unsupported data type: {data_type}')

    
    @abstractmethod
    def tweak_parallel(self, tweak):
        
        if self.fx_swap_config == None:
            fx_swap_mkt_data_tweaked = pd.DataFrame()
        else: 
            fx_tweak = tweak if self.fx_swap_config.is_collateral_ccy_base_ccy else -tweak
            fx_swap_mkt_data_tweaked = self.mkt_data_tweak('fx', fx_tweak, 'ALL')
        
        if type(self.ccs_config) == FixedToOisCcsConfig:
            ccs_data_type = 'fixed_to_ois_ccs'
            ccs_tweak = tweak
        elif type(self.ccs_config) == FloatToFloatCcsConfig:
            ccs_data_type = 'float_to_float_ccs'
            ccs_tweak = tweak if self.ccs_config.is_basis_on_target_leg else -tweak
        ccs_mkt_data_tweaked = self.mkt_data_tweak(ccs_data_type, ccs_tweak, 'ALL')
        
        curve_tweak = self.__class__(
            self.today, self.collateral_index_curve, self.collateral_discount_curve,
            ccs_mkt_data_tweaked, fx_swap_mkt_data_tweaked, 
            self.target_index_curve, self.interpolation_method)
        
        return curve_tweak


    @abstractmethod
    def tweak_keytenor(self, tweak, tenor='ALL'):
        
        if self.fx_swap_config == None:
            fx_tenors = []
        else: 
            fx_tenors = list(self.fx_swap_mkt_data.loc[self.fx_swap_mkt_data['Tenor']!='SPOT','Tenor'])
            fx_tweak = tweak if self.fx_swap_config.is_collateral_ccy_base_ccy else -tweak
        
        ccs_tenors = list(self.ccs_mkt_data['Tenor'])
        if type(self.ccs_config) == FixedToOisCcsConfig:
            ccs_data_type = 'fixed_to_ois_ccs'
            ccs_tweak = tweak
        elif type(self.ccs_config) == FloatToFloatCcsConfig:
            ccs_data_type = 'float_to_float_ccs'
            ccs_tweak = tweak if self.ccs_config.is_basis_on_target_leg else -tweak
        
        if tenor == 'ALL':
            all_tweaked_curves = dict()
            for tenor in fx_tenors:
                fx_swap_mkt_data_tweaked = self.mkt_data_tweak('fx', fx_tweak, [tenor])
                curve_tweak = self.__class__(
                    self.today, self.collateral_index_curve, self.collateral_discount_curve,
                    self.ccs_mkt_data, fx_swap_mkt_data_tweaked, 
                    self.target_index_curve, self.interpolation_method)
                all_tweaked_curves[tenor] = curve_tweak

            for tenor in ccs_tenors:
                ccs_mkt_data_tweaked = self.mkt_data_tweak(ccs_data_type, ccs_tweak, [tenor])
                curve_tweak = self.__class__(
                    self.today, self.collateral_index_curve, self.collateral_discount_curve,
                    ccs_mkt_data_tweaked, self.fx_swap_mkt_data, 
                    self.target_index_curve, self.interpolation_method)
                all_tweaked_curves[tenor] = curve_tweak

            return all_tweaked_curves

        elif tenor in fx_tenors:
            fx_swap_mkt_data_tweaked = self.mkt_data_tweak('fx', fx_tweak, [tenor])
            curve_tweak = self.__class__(
                self.today, self.collateral_index_curve, self.collateral_discount_curve,
                self.ccs_mkt_data, fx_swap_mkt_data_tweaked, 
                self.target_index_curve, self.interpolation_method)
            return curve_tweak

        elif tenor in ccs_tenors:
            ccs_mkt_data_tweaked = self.mkt_data_tweak(ccs_data_type, ccs_tweak, [tenor])
            curve_tweak = self.__class__(
                self.today, self.collateral_index_curve, self.collateral_discount_curve,
                ccs_mkt_data_tweaked, self.fx_swap_mkt_data, 
                self.target_index_curve, self.interpolation_method)
            return curve_tweak

        else:
            raise Exception(f'Invalid tenor: {tenor}!')
