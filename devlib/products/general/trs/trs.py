# -*- coding: utf-8 -*-
"""
Created on Tue Aug 22 12:09:58 2023

@author: xieyushan
"""

import QuantLib as ql
import numpy as np
import pandas as pd
 
from devlib.products.general.trs.funding_leg import (FixedFundingLeg, 
                                              FloatFundingLeg, 
                                              CrossBorderFixedFundingLeg, 
                                              CrossBorderFloatFundingLeg,
                                              )



class Trs:
    def __init__(
            self, 
            ):
        pass
        
        
    def npv(self, today: ql.Date, latest_price: float, fixings_dict: dict = {}, 
            is_only_realized: bool = False, is_only_unsettled: bool = False):
        npv_asset = self.npv_asset(today, latest_price, is_only_realized=is_only_realized, 
                                   is_only_unsettled=is_only_unsettled)
        npv_funding = self.npv_funding(today, fixings_dict, is_only_realized=is_only_realized, 
                                       is_only_unsettled=is_only_unsettled)
        
        return npv_asset + npv_funding
    
    
    def npv_asset(self, today: ql.Date, latest_price: float, 
                  is_only_realized: bool = False, is_only_unsettled: bool = False):
        
        return self.asset_leg.npv_mtm(today, latest_price, is_only_realized=is_only_realized, 
                                      is_only_unsettled=is_only_unsettled)
    
    
    def npv_funding(self, today: ql.Date, fixings_dict: dict = {}, 
                    is_only_realized: bool = False, is_only_unsettled: bool = False):
        npv = 0.0
        npv_legs = self.npv_funding_legs(today, fixings_dict, is_only_realized=is_only_realized, 
                                         is_only_unsettled=is_only_unsettled)
        for leg_name in self.funding_legs.keys():
            npv += npv_legs[leg_name]
            
        return npv      
        
    
    def npv_funding_legs(self, today: ql.Date, fixings_dict: dict = {}, 
                         is_only_realized: bool = False, is_only_unsettled: bool = False):
        npv = {}
        for leg_name in self.funding_legs.keys():
            leg = self.funding_legs[leg_name]
            if type(leg) == FloatFundingLeg:
                fixings = fixings_dict[leg_name]
                npv_leg = leg.npv_acr(today, fixings, is_only_realized=is_only_realized, 
                                      is_only_unsettled=is_only_unsettled)
            elif type(leg) == FixedFundingLeg:
                npv_leg = leg.npv_acr(today, is_only_realized=is_only_realized, 
                                      is_only_unsettled=is_only_unsettled)
            else:
                raise Exception(f'Unsupported funding leg type: {type(leg)}!')
            
            npv[leg_name] = npv_leg
        
        return npv
    
    
    def npv_distribution(self, today, is_only_realized: bool = False, is_only_unsettled: bool = False):
        try:
            return self.asset_leg.distribution_leg.npv_acr(today, is_only_realized=is_only_realized, 
                                                           is_only_unsettled=is_only_unsettled)
        except:
            return None



class CrossBorderTrs:
    def __init__(
            self, 
            ):
        pass
    
    
    def npv(self, today: ql.Date, latest_price: float, fx_spot: float, fixings_dict: dict = {}, 
            is_only_realized: bool = False, is_only_unsettled: bool = False):
        npv_asset = self.npv_asset(today, latest_price, fx_spot, is_only_realized=is_only_realized, 
                                   is_only_unsettled=is_only_unsettled)
        npv_funding = self.npv_funding(today, fx_spot, fixings_dict, is_only_realized=is_only_realized, 
                                       is_only_unsettled=is_only_unsettled)
        
        return npv_asset + npv_funding
    
    
    def npv_asset(self, today: ql.Date, latest_price: float, fx_spot: float, 
                  is_only_realized: bool = False, is_only_unsettled: bool = False):
        
        return self.asset_leg.npv_mtm(today, latest_price, fx_spot, is_only_realized=is_only_realized, 
                                      is_only_unsettled=is_only_unsettled)
    
    
    def npv_funding(self, today: ql.Date, fx_spot: float, fixings_dict: dict = {}, 
                    is_only_realized: bool = False, is_only_unsettled: bool = False):
        npv = 0.0
        npv_legs = self.npv_funding_legs(today, fx_spot, fixings_dict, is_only_realized=is_only_realized, 
                                         is_only_unsettled=is_only_unsettled)
        for leg_name in self.funding_legs.keys():
            npv += npv_legs[leg_name]
            
        return npv     
    
    
    def npv_funding_legs(self, today: ql.Date, fx_spot: float, fixings_dict: dict = {}, 
                         is_only_realized: bool = False, is_only_unsettled: bool = False):
        npv = {}
        for leg_name in self.funding_legs.keys():
            leg = self.funding_legs[leg_name]
            if type(leg) == CrossBorderFloatFundingLeg:
                fixings = fixings_dict[leg_name]
                npv_leg = leg.npv_acr(today, fixings, fx_spot, is_only_realized=is_only_realized, 
                                      is_only_unsettled=is_only_unsettled)
            elif type(leg) == CrossBorderFixedFundingLeg:
                npv_leg = leg.npv_acr(today, fx_spot, is_only_realized=is_only_realized, 
                                      is_only_unsettled=is_only_unsettled)
            elif type(leg) == FloatFundingLeg:
                fixings = fixings_dict[leg_name]
                npv_leg = leg.npv_acr(today, fixings, is_only_realized=is_only_realized, 
                                      is_only_unsettled=is_only_unsettled)
            elif type(leg) == FixedFundingLeg:
                npv_leg = leg.npv_acr(today, is_only_realized=is_only_realized, 
                                      is_only_unsettled=is_only_unsettled)                
            else:
                raise Exception(f'Unsupported funding leg type: {type(leg)}!')
            
            npv[leg_name] = npv_leg
        
        return npv
    
    
    def npv_distribution(self, today, fx_spot: float, is_only_realized: bool = False, 
                         is_only_unsettled: bool = False):
        try:
            return self.asset_leg.distribution_leg.npv_acr(
                today, fx_spot, is_only_realized=is_only_realized, 
                is_only_unsettled=is_only_unsettled)
        except:
            return None
    
    
    def npv_asset_ccy(self, today: ql.Date, latest_price: float, 
                      fixings_dict: dict = {}, is_only_realized: bool = False, 
                      is_only_unsettled: bool = False):
        npv_asset = self.npv_asset_asset_ccy(today, latest_price, is_only_realized=is_only_realized, 
                                             is_only_unsettled=is_only_unsettled)
        npv_funding = self.npv_funding_asset_ccy(today, fixings_dict, is_only_realized=is_only_realized, 
                                                 is_only_unsettled=is_only_unsettled)
        
        return npv_asset + npv_funding
    
    
    def npv_asset_asset_ccy(self, today: ql.Date, latest_price: float, 
                            is_only_realized: bool = False, is_only_unsettled: bool = False):
        
        return self.asset_leg.npv_mtm_asset_ccy(today, latest_price, is_only_realized=is_only_realized, 
                                                is_only_unsettled=is_only_unsettled)
    
    
    def npv_funding_asset_ccy(self, today: ql.Date, fixings_dict: dict = {}, 
                              is_only_realized: bool = False, is_only_unsettled: bool = False):
        npv = 0.0
        npv_legs = self.npv_funding_legs_asset_ccy(
            today, fixings_dict, is_only_realized=is_only_realized, 
            is_only_unsettled=is_only_unsettled)
        for leg_name in self.funding_legs.keys():
            npv += npv_legs[leg_name]
            
        return npv      
        
    
    def npv_funding_legs_asset_ccy(self, today: ql.Date, fixings_dict: dict = {}, 
                                   is_only_realized: bool = False, is_only_unsettled: bool = False):
        npv = {}
        for leg_name in self.funding_legs.keys():
            leg = self.funding_legs[leg_name]
            if not (type(leg) == CrossBorderFixedFundingLeg or 
                    type(leg) == CrossBorderFloatFundingLeg):
                raise Exception(f'Unsupported funding leg type: {type(leg)}!')
            else:
                if not leg.funding_ccy == self.asset_leg.asset_ccy:
                    raise Exception(f'Funding ccy does not match asset ccy!')
            
            if type(leg) == CrossBorderFloatFundingLeg:
                fixings = fixings_dict[leg_name]
                npv_leg = leg.npv_acr_funding_ccy(today, fixings, is_only_realized=is_only_realized, 
                                                  is_only_unsettled=is_only_unsettled)
            elif type(leg) == CrossBorderFixedFundingLeg:
                npv_leg = leg.npv_acr_funding_ccy(today, is_only_realized=is_only_realized, 
                                                  is_only_unsettled=is_only_unsettled)
        
            npv[leg_name] = npv_leg
        
        return npv
    
    
    def npv_distribution_asset_ccy(self, today, is_only_realized: bool = False, 
                                   is_only_unsettled: bool = False):
        try:
            return self.asset_leg.distribution_leg.npv_acr_asset_ccy(
                today, is_only_realized=is_only_realized, is_only_unsettled=is_only_unsettled)
        except:
            return None

    
    