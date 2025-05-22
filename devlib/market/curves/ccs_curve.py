# -*- coding: utf-8 -*-
"""
Created on Mon Aug 19 10:46:33 2024

@author: Guanzhifan
"""

import QuantLib as ql

import devlib.market.curves.ccs_curve_generator as ccg
import devlib.market.curves.curve_generator as cg


#%% 61
class CnyUsdCcsOfCurve(ccg.CcsCurve):
    def curve_config_set(self):
        self.curve_config = ccg.DiscountCurveConfig(
            curve_name = 'CNYUSDCCSOF', 
            currency = ql.CNYCurrency())
        
        self.fx_swap_config = ccg.FxSwapConfig(
            fx_pair = 'USDCNY',
            settlement_delay = 2,
            calendar = ql.JointCalendar(ql.China(ql.China.IB),
                                        ql.UnitedStates(ql.UnitedStates.FederalReserve),
                                        ql.JoinHolidays),
            convention = ql.Following, 
            end_of_month = False,
            is_collateral_ccy_base_ccy = True,
            tweak_daycount = ql.Actual365Fixed())
        
        self.ccs_config = ccg.FixedToOisCcsConfig(
            settlement_delay = 2,
            calendar = ql.JointCalendar(ql.China(ql.China.IB),
                                        ql.UnitedStates(ql.UnitedStates.FederalReserve),
                                        ql.JoinHolidays),
            payment_lag = 2,
            payment_convention = ql.ModifiedFollowing,
            payment_freq = ql.Semiannual, 
            fixed_daycount = ql.Actual365Fixed(), 
            forward_start = 0)


#%% 59
class KrwUsdCcsOfCurve(ccg.CcsCurve):
    def curve_config_set(self):
        self.curve_config = ccg.DiscountCurveConfig(
            curve_name = 'KRWUSDCCSOF', 
            currency = ql.KRWCurrency())
        
        self.fx_swap_config = ccg.FxSwapConfig(
            fx_pair = 'USDKRW',
            settlement_delay = 2,
            calendar = ql.JointCalendar(ql.SouthKorea(),
                                        ql.UnitedStates(ql.UnitedStates.FederalReserve),
                                        ql.JoinHolidays),
            convention = ql.Following, 
            end_of_month = False,
            is_collateral_ccy_base_ccy = True,
            tweak_daycount = ql.Actual365Fixed())
        
        self.ccs_config = ccg.FixedToOisCcsConfig(
            settlement_delay = 2,
            calendar = ql.JointCalendar(ql.SouthKorea(),
                                        ql.UnitedStates(ql.UnitedStates.FederalReserve),
                                        ql.JoinHolidays),
            payment_lag = 2,
            payment_convention = ql.ModifiedFollowing,
            payment_freq = ql.Quarterly, 
            fixed_daycount = ql.Actual365Fixed(), 
            forward_start = 0)

#%% 210
class ThbUsdCcsOfCurve(ccg.CcsCurve):
    def curve_config_set(self):
        self.curve_config = ccg.DiscountCurveConfig(
            curve_name = 'THBUSDCCSOF', 
            currency = ql.THBCurrency())
        
        self.fx_swap_config = ccg.FxSwapConfig(
            fx_pair = 'USDTHB',
            settlement_delay = 2,
            calendar = ql.JointCalendar(ql.Thailand(),
                                        ql.UnitedStates(ql.UnitedStates.FederalReserve),
                                        ql.JoinHolidays),
            convention = ql.Following, 
            end_of_month = False,
            is_collateral_ccy_base_ccy = True,
            tweak_daycount = ql.Actual365Fixed())
        
        self.ccs_config = ccg.FixedToOisCcsConfig(
            settlement_delay = 2,
            calendar = ql.JointCalendar(ql.Thailand(),
                                        ql.UnitedStates(ql.UnitedStates.FederalReserve),
                                        ql.JoinHolidays),
            payment_lag = 2,
            payment_convention = ql.ModifiedFollowing,
            payment_freq = ql.Quarterly,
            fixed_daycount = ql.Actual365Fixed(), 
            forward_start = 0)


#%% 69
class InrUsdCcsOfCurve(ccg.CcsCurve):
    def curve_config_set(self):
        self.curve_config = ccg.DiscountCurveConfig(
            curve_name = 'INRUSDCCSOF', 
            currency = ql.INRCurrency())
        
        self.fx_swap_config = ccg.FxSwapConfig(
            fx_pair = 'USDINR',
            settlement_delay = 2,
            calendar = ql.JointCalendar(ql.India(),
                                        ql.UnitedStates(ql.UnitedStates.FederalReserve),
                                        ql.JoinHolidays),
            convention = ql.Following, 
            end_of_month = False,
            is_collateral_ccy_base_ccy = True,
            tweak_daycount = ql.Actual365Fixed())
        
        self.ccs_config = ccg.FixedToOisCcsConfig(
            settlement_delay = 2,
            calendar = ql.JointCalendar(ql.India(),
                                        ql.UnitedStates(ql.UnitedStates.FederalReserve),
                                        ql.JoinHolidays),
            payment_lag = 2,
            payment_convention = ql.ModifiedFollowing,
            payment_freq = ql.Semiannual, 
            fixed_daycount = ql.Actual365Fixed(), 
            forward_start = 0)


#%% 535
class CnhUsdCcsCurve(ccg.CcsCurve):
    def curve_config_set(self):
        self.curve_config = ccg.DiscountCurveConfig(
            curve_name = 'CNHUSDCCS', 
            currency = ql.CNHCurrency())
        
        self.fx_swap_config = ccg.FxSwapConfig(
            fx_pair = 'USDCNH',
            settlement_delay = 2,
            calendar = ql.JointCalendar(ql.China(ql.China.IB),
                                        ql.HongKong(),
                                        ql.UnitedStates(ql.UnitedStates.FederalReserve),
                                        ql.JoinHolidays),
            convention = ql.Following, 
            end_of_month = False,
            is_collateral_ccy_base_ccy = True,
            tweak_daycount = ql.Actual365Fixed())
        
        self.ccs_config = ccg.FixedToOisCcsConfig(
            settlement_delay = 2,
            calendar = ql.JointCalendar(ql.China(ql.China.IB),
                                        ql.HongKong(),
                                        ql.UnitedStates(ql.UnitedStates.FederalReserve),
                                        ql.JoinHolidays),
            payment_lag = 2,
            payment_convention = ql.ModifiedFollowing,
            payment_freq = ql.Quarterly,
            fixed_daycount = ql.Actual360(), 
            forward_start = 0)


#%% 536
class CnyUsdCcsCurve(ccg.CcsCurve):
    def curve_config_set(self):
        self.curve_config = ccg.DiscountCurveConfig(
            curve_name = 'CNYUSDCCS', 
            currency = ql.CNYCurrency())
        
        self.fx_swap_config = ccg.FxSwapConfig(
            fx_pair = 'USDCNY',
            settlement_delay = 2,
            calendar = ql.JointCalendar(ql.China(ql.China.IB),
                                        ql.UnitedStates(ql.UnitedStates.FederalReserve),
                                        ql.JoinHolidays),
            convention = ql.Following, 
            end_of_month = False,
            is_collateral_ccy_base_ccy = True,
            tweak_daycount = ql.Actual365Fixed())
        
        self.ccs_config = ccg.FixedToOisCcsConfig(
            settlement_delay = 2,
            calendar = ql.JointCalendar(ql.China(ql.China.IB),
                                        ql.UnitedStates(ql.UnitedStates.FederalReserve),
                                        ql.JoinHolidays),
            payment_lag = 2,
            payment_convention = ql.ModifiedFollowing,
            payment_freq = ql.Quarterly, 
            fixed_daycount = ql.Actual365Fixed(), 
            forward_start = 0)


#%% 97
class JpyUsdBasisCurve(ccg.CcsCurve):
    def curve_config_set(self):
        self.curve_config = ccg.DiscountCurveConfig(
            curve_name = 'JPYUSDBASIS', 
            currency = ql.JPYCurrency())
        
        self.fx_swap_config = ccg.FxSwapConfig(
            fx_pair = 'USDJPY',
            settlement_delay = 2,
            calendar = ql.JointCalendar(ql.Japan(),
                                        ql.UnitedStates(ql.UnitedStates.FederalReserve),
                                        ql.JoinHolidays),
            convention = ql.Following, 
            end_of_month = False,
            is_collateral_ccy_base_ccy = True,
            tweak_daycount = ql.Actual365Fixed())
        
        self.ccs_config = ccg.FloatToFloatCcsConfig(
            settlement_delay = 2,
            calendar = ql.JointCalendar(ql.Japan(),
                                        ql.UnitedStates(ql.UnitedStates.FederalReserve),
                                        ql.JoinHolidays),
            convention = ql.ModifiedFollowing,
            end_of_month = True,
            target_index_config = cg.IborIndexConfig(
                curve_name = 'TONA_CCS',
                tenor = '3M',
                settlement_delay = 0,
                currency = ql.JPYCurrency(),
                calendar = ql.Japan(),
                convention = ql.ModifiedFollowing,
                end_of_month = True,
                daycount = ql.Actual365Fixed()),
            collateral_index_config = cg.IborIndexConfig(
                curve_name = 'SOFR_CCS',
                tenor = '3M',
                settlement_delay = 0,
                currency = ql.USDCurrency(),
                calendar = ql.Sofr().fixingCalendar(),
                convention = ql.ModifiedFollowing,
                end_of_month = True,
                daycount = ql.Actual360()),
            is_basis_on_target_leg = True,
            is_target_leg_resettable = False)

        
#%% 96
class HkdUsdBasisCurve(ccg.CcsCurve):
    def curve_config_set(self):
        self.curve_config = ccg.DiscountCurveConfig(
            curve_name = 'HKDUSDBASIS', 
            currency = ql.HKDCurrency())
        
        self.fx_swap_config = ccg.FxSwapConfig(
            fx_pair = 'USDHKD',
            settlement_delay = 2,
            calendar = ql.JointCalendar(ql.HongKong(),
                                        ql.UnitedStates(ql.UnitedStates.FederalReserve),
                                        ql.JoinHolidays),
            convention = ql.Following, 
            end_of_month = False,
            is_collateral_ccy_base_ccy = True,
            tweak_daycount = ql.Actual365Fixed())
        
        self.ccs_config = ccg.FloatToFloatCcsConfig(
            settlement_delay = 2,
            calendar = ql.JointCalendar(ql.HongKong(),
                                        ql.UnitedStates(ql.UnitedStates.FederalReserve),
                                        ql.JoinHolidays),
            convention = ql.ModifiedFollowing,
            end_of_month = True,
            target_index_config = cg.IborIndexConfig(
                curve_name='HIBOR3M_CCS', 
                tenor='3M', 
                settlement_delay=0, 
                currency=ql.HKDCurrency(),
                calendar=ql.HongKong(), 
                convention=ql.ModifiedFollowing, 
                end_of_month=True, 
                daycount=ql.Actual365Fixed()),
            collateral_index_config = cg.IborIndexConfig(
                curve_name = 'SOFR_CCS',
                tenor = '3M',
                settlement_delay = 0,
                currency = ql.USDCurrency(),
                calendar = ql.Sofr().fixingCalendar(),
                convention = ql.ModifiedFollowing,
                end_of_month = True,
                daycount = ql.Actual360()),
            is_basis_on_target_leg = True)


