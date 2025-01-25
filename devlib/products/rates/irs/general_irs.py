# -*- coding: utf-8 -*-
"""
Created on Fri Jul 14 15:26:14 2023

@author: Liuli5
"""

import QuantLib as ql
import numpy as np

import devlib.products.rates.irs.rate_legs as rl



# only for fixed to float irs
class FloatFixedIrs:
    def __init__(
            self, 
            ccy: str,
            fixed_leg_start_dates: np.ndarray, 
            fixed_leg_end_dates: np.ndarray, 
            fixed_leg_payment_dates: np.ndarray, 
            fixed_leg_notionals: np.ndarray, 
            fixed_leg_fixed_rates: np.ndarray, 
            fixed_leg_daycount: ql.DayCounter, 
            fixed_leg_direction: str, 
            float_leg_start_dates: np.ndarray, 
            float_leg_end_dates: np.ndarray,
            float_leg_payment_dates: np.ndarray, 
            float_leg_notionals: np.ndarray, 
            float_leg_daycount: ql.DayCounter, 
            float_leg_index_name: str, 
            float_leg_reset_dates_array: np.ndarray, 
            float_leg_fixing_dates_array: np.ndarray, 
            float_leg_multiplier: float, 
            float_leg_spread: float, 
            float_leg_direction: str, 
            float_leg_is_ois_leg: bool = False, 
            float_leg_compounding_type: str = 'ExcludeSprd', 
            is_init_notional_ex: bool = False, 
            init_notional_ex: float = 0.0, 
            init_notional_ex_paydate: ql.Date = None, 
            is_final_notional_ex: bool = False, 
            final_notional_ex: float = 0.0, 
            final_notional_ex_paydate: ql.Date = None,
            ):
        self.ccy = ccy
        fixed_leg_direction = fixed_leg_direction.lower()
        float_leg_direction = float_leg_direction.lower()

        self.fixed_leg = rl.FixedLeg(
            ccy, fixed_leg_start_dates, fixed_leg_end_dates, fixed_leg_payment_dates, 
            fixed_leg_notionals, fixed_leg_fixed_rates, fixed_leg_daycount, fixed_leg_direction, 
            is_init_notional_ex, init_notional_ex, init_notional_ex_paydate, 
            is_final_notional_ex, final_notional_ex, final_notional_ex_paydate)
        
        self.float_leg = rl.FloatLeg(
            ccy, float_leg_index_name, float_leg_start_dates, float_leg_end_dates, 
            float_leg_reset_dates_array, float_leg_fixing_dates_array, float_leg_payment_dates, 
            float_leg_notionals, float_leg_multiplier, float_leg_spread, float_leg_daycount, 
            float_leg_direction, float_leg_is_ois_leg, float_leg_compounding_type, 
            is_init_notional_ex, init_notional_ex, init_notional_ex_paydate, 
            is_final_notional_ex, final_notional_ex, final_notional_ex_paydate)

    
    # only support single curve valuation
    def npv(self, today, index_curve, discount_curve):
        fixed_leg_npv = self.fixed_leg.npv(today, discount_curve)
        float_leg_npv = self.float_leg.npv(today, index_curve, discount_curve)

        return fixed_leg_npv + float_leg_npv


    def fair_rate(self, today, index_curve, discount_curve):        
        annuity = self.fixed_leg.annuity(today, discount_curve)
        fixed_notional_ex_npv = self.fixed_leg.notional_ex_npv(today, discount_curve)
        if annuity < 1e-8:
            return None
        float_leg_npv = self.float_leg.npv(today, index_curve, discount_curve)
        fixed_trade_direction = -1 if self.fixed_leg.trade_direction == 'pay' else 1
        
        fair_rate = (-float_leg_npv - fixed_notional_ex_npv) / (annuity * fixed_trade_direction)

        return fair_rate
    
    
    def dv01_keytenor(self, today, index_curve, discount_curve, tweak=1e-4):
        dv01s = {}
        if index_curve.name == discount_curve.name:
            index_curve_keytenor_up = index_curve.tweak_keytenor(tweak)
            index_curve_keytenor_down = index_curve.tweak_keytenor(-tweak)
            for tenor in index_curve_keytenor_up.keys():
                index_curve_up = index_curve_keytenor_up[tenor]
                index_curve_down = index_curve_keytenor_down[tenor]
                npv_up = self.npv(today, index_curve_up, index_curve_up)
                npv_down = self.npv(today, index_curve_down, index_curve_down)
                dv01 = (npv_up - npv_down) / (2 * tweak) * 1e-4
                dv01s['DV01_' + index_curve.name + "_" + tenor] = dv01
        else:
            index_curve_keytenor_up = index_curve.tweak_keytenor(tweak)
            index_curve_keytenor_down = index_curve.tweak_keytenor(-tweak)
            for tenor in index_curve_keytenor_up.keys():
                index_curve_up = index_curve_keytenor_up[tenor]
                index_curve_down = index_curve_keytenor_down[tenor]
                npv_up = self.npv(today, index_curve_up, discount_curve)
                npv_down = self.npv(today, index_curve_down, discount_curve)
                dv01 = (npv_up - npv_down) / (2 * tweak) * 1e-4
                dv01s['DV01_' + index_curve.name + "_" + tenor] = dv01
            
            discount_curve_keytenor_up = discount_curve.tweak_keytenor(tweak)
            discount_curve_keytenor_down = discount_curve.tweak_keytenor(-tweak)
            for tenor in discount_curve_keytenor_up.keys():
                discount_curve_up = discount_curve_keytenor_up[tenor]
                discount_curve_down = discount_curve_keytenor_down[tenor]
                npv_up = self.npv(today, index_curve, discount_curve_up)
                npv_down = self.npv(today, index_curve, discount_curve_down)
                dv01 = (npv_up - npv_down) / (2 * tweak) * 1e-4
                dv01s['DV01_' + discount_curve.name + "_" + tenor] = dv01
            
        return dv01s


    def dv01_parallel(self, today, index_curve, discount_curve, tweak=1e-4):
        index_curve_up = index_curve.tweak_parallel(tweak)
        index_curve_down = index_curve.tweak_parallel(-tweak)
        discount_curve_up = discount_curve.tweak_parallel(tweak)
        discount_curve_down = discount_curve.tweak_parallel(-tweak)
        npv_up = self.npv(today, index_curve_up, discount_curve_up)
        npv_down = self.npv(today, index_curve_down, discount_curve_down)
        dv01 = (npv_up - npv_down) / (2 * tweak) * 1e-4
        
        return dv01
    


class StandardFloatFixedIrs(FloatFixedIrs):
    def __init__(
            self, 
            ccy: str,
            index_name: str, 
            effective_date: ql.Date, 
            maturity_date: ql.Date, 
            fixed_leg_pay_freq: str, 
            float_leg_pay_freq: str, 
            reset_freq: str, 
            notional: float, 
            fixed_rate: float, 
            multiplier: float,
            spread: float,
            fixed_leg_daycount: ql.DayCounter, 
            float_leg_daycount: ql.DayCounter, 
            payment_delay: int, 
            fixing_days: int, 
            sch_calendar: ql.Calendar, 
            fixing_calendar: ql.Calendar, 
            payment_calendar: ql.Calendar,
            fixed_leg_direction: str, 
            float_leg_direction: str,
            date_generation_rule=ql.DateGeneration.Forward,
            sch_convention=ql.ModifiedFollowing,
            end_convention=ql.ModifiedFollowing,
            payment_convention=ql.ModifiedFollowing, 
            reset_convention=ql.ModifiedFollowing, 
            fixing_convention=ql.Preceding, 
            end_of_month: bool = False, 
            is_ois_leg: bool = False,
            compounding_type: str = 'ExcludeSprd',
            is_init_notional_ex: bool = False,
            is_final_notional_ex: bool = False, 
            final_notional_ex_payment_delay: int = 0, 
            ):
        self.ccy = ccy
        fixed_leg_direction = fixed_leg_direction.lower()
        float_leg_direction = float_leg_direction.lower()

        self.fixed_leg = rl.StandardFixedLeg(
               ccy, effective_date, maturity_date, fixed_leg_pay_freq, notional, 
               fixed_rate, fixed_leg_daycount, payment_delay, sch_calendar, 
               payment_calendar, fixed_leg_direction, date_generation_rule, 
               sch_convention, end_convention, payment_convention, end_of_month, 
               is_init_notional_ex, is_final_notional_ex, final_notional_ex_payment_delay)
        
        self.float_leg = rl.StandardFloatLeg(
               ccy, index_name, effective_date, maturity_date, float_leg_pay_freq, 
               reset_freq, notional, multiplier, spread, float_leg_daycount, payment_delay, 
               fixing_days, sch_calendar, fixing_calendar, payment_calendar, float_leg_direction, 
               date_generation_rule, sch_convention, end_convention, payment_convention, 
               reset_convention, fixing_convention, end_of_month, is_ois_leg, compounding_type, 
               is_init_notional_ex, is_final_notional_ex, final_notional_ex_payment_delay)
        
        
        
class FloatFloatIrs:
    def __init__(
            self, 
            ccy: str, 
            float_leg_start_dates_1: np.ndarray, 
            float_leg_end_dates_1: np.ndarray,
            float_leg_payment_dates_1: np.ndarray, 
            float_leg_notionals_1: np.ndarray, 
            float_leg_daycount_1: ql.DayCounter, 
            float_leg_index_name_1: str, 
            float_leg_reset_dates_array_1: np.ndarray, 
            float_leg_fixing_dates_array_1: np.ndarray, 
            float_leg_multiplier_1: float, 
            float_leg_spread_1: float, 
            float_leg_direction_1: str, 
            float_leg_start_dates_2: np.ndarray, 
            float_leg_end_dates_2: np.ndarray,
            float_leg_payment_dates_2: np.ndarray, 
            float_leg_notionals_2: np.ndarray, 
            float_leg_daycount_2: ql.DayCounter, 
            float_leg_index_name_2: str, 
            float_leg_reset_dates_array_2: np.ndarray, 
            float_leg_fixing_dates_array_2: np.ndarray, 
            float_leg_multiplier_2: float, 
            float_leg_spread_2: float, 
            float_leg_direction_2: str, 
            float_leg_is_ois_leg_1: bool = False, 
            float_leg_compounding_type_1: str = 'ExcludeSprd', 
            float_leg_is_ois_leg_2: bool = False, 
            float_leg_compounding_type_2: str = 'ExcludeSprd', 
            is_init_notional_ex: bool = False, 
            init_notional_ex: float = 0.0, 
            init_notional_ex_paydate: ql.Date = None, 
            is_final_notional_ex: bool = False, 
            final_notional_ex: float = 0.0, 
            final_notional_ex_paydate: ql.Date = None, 
            ):
        self.ccy = ccy
        float_leg_direction_1 = float_leg_direction_1.lower()
        float_leg_direction_2 = float_leg_direction_2.lower()

        self.float_leg_1 = rl.FloatLeg(
            ccy, float_leg_index_name_1, float_leg_start_dates_1, float_leg_end_dates_1, 
            float_leg_reset_dates_array_1, float_leg_fixing_dates_array_1, float_leg_payment_dates_1, 
            float_leg_notionals_1, float_leg_multiplier_1, float_leg_spread_1, float_leg_daycount_1, 
            float_leg_direction_1, float_leg_is_ois_leg_1, float_leg_compounding_type_1, 
            is_init_notional_ex, init_notional_ex, init_notional_ex_paydate, 
            is_final_notional_ex, final_notional_ex, final_notional_ex_paydate)
        
        self.float_leg_2 = rl.FloatLeg(
            ccy, float_leg_index_name_2, float_leg_start_dates_2, float_leg_end_dates_2, 
            float_leg_reset_dates_array_2, float_leg_fixing_dates_array_2, float_leg_payment_dates_2, 
            float_leg_notionals_2, float_leg_multiplier_2, float_leg_spread_2, float_leg_daycount_2, 
            float_leg_direction_2, float_leg_is_ois_leg_2, float_leg_compounding_type_2, 
            is_init_notional_ex, init_notional_ex, init_notional_ex_paydate, 
            is_final_notional_ex, final_notional_ex, final_notional_ex_paydate)
    
    
    
    def npv(self, today, index_curve_1, discount_curve_1, index_curve_2, discount_curve_2):
        float_leg_1_npv = self.float_leg_1.npv(today, index_curve_1, discount_curve_1)
        float_leg_2_npv = self.float_leg_2.npv(today, index_curve_2, discount_curve_2)
        
        return float_leg_1_npv + float_leg_2_npv
    
    
    
    def dv01_parallel(self, today, index_curve_1, discount_curve_1, index_curve_2, discount_curve_2, tweak=1e-4):
        index_curve_1_up = index_curve_1.tweak_parallel(tweak)
        index_curve_1_down = index_curve_1.tweak_parallel(-tweak)
        discount_curve_1_up = discount_curve_1.tweak_parallel(tweak)
        discount_curve_1_down = discount_curve_1.tweak_parallel(-tweak)
        index_curve_2_up = index_curve_2.tweak_parallel(tweak)
        index_curve_2_down = index_curve_2.tweak_parallel(-tweak)
        discount_curve_2_up = discount_curve_2.tweak_parallel(tweak)
        discount_curve_2_down = discount_curve_2.tweak_parallel(-tweak)    

        npv_up = self.npv(today, index_curve_1_up, discount_curve_1_up, index_curve_2_up, discount_curve_2_up)
        npv_down = self.npv(today, index_curve_1_down, discount_curve_1_down, index_curve_2_down, discount_curve_2_down)
        dv01 = (npv_up - npv_down) / (2 * tweak) * 1e-4
        
        return dv01



class StandardFloatFloatIrs(FloatFloatIrs):
    def __init__(
            self, 
            ccy: str, 
            index_name_1: str, 
            index_name_2: str, 
            effective_date: ql.Date, 
            maturity_date: ql.Date, 
            float_leg_pay_freq_1: str, 
            float_leg_pay_freq_2: str, 
            reset_freq_1: str, 
            reset_freq_2: str, 
            notional: float, 
            multiplier_1: float, 
            multiplier_2: float, 
            spread_1: float, 
            spread_2: float, 
            float_leg_daycount_1: ql.DayCounter, 
            float_leg_daycount_2: ql.DayCounter, 
            payment_delay: int, 
            fixing_days_1: int, 
            fixing_days_2: int, 
            sch_calendar: ql.Calendar, 
            fixing_calendar_1: ql.Calendar, 
            fixing_calendar_2: ql.Calendar, 
            payment_calendar: ql.Calendar,
            float_leg_direction_1: str, 
            float_leg_direction_2: str,
            date_generation_rule=ql.DateGeneration.Forward,
            sch_convention=ql.ModifiedFollowing,
            end_convention=ql.ModifiedFollowing,
            payment_convention=ql.ModifiedFollowing, 
            reset_convention_1=ql.ModifiedFollowing, 
            reset_convention_2=ql.ModifiedFollowing, 
            fixing_convention_1=ql.Preceding, 
            fixing_convention_2=ql.Preceding, 
            end_of_month: bool = False, 
            is_ois_leg_1: bool = False, 
            is_ois_leg_2: bool = False, 
            compounding_type_1: str = 'ExcludeSprd', 
            compounding_type_2: str = 'ExcludeSprd',
            is_init_notional_ex: bool = False,
            is_final_notional_ex: bool = False, 
            final_notional_ex_payment_delay: int = 0, 
            ):
        self.ccy = ccy
        float_leg_direction_1 = float_leg_direction_1.lower()
        float_leg_direction_2 = float_leg_direction_2.lower()
        
        self.float_leg_1 = rl.StandardFloatLeg(
               ccy, index_name_1, effective_date, maturity_date, float_leg_pay_freq_1, 
               reset_freq_1, notional, multiplier_1, spread_1, float_leg_daycount_1, payment_delay, 
               fixing_days_1, sch_calendar, fixing_calendar_1, payment_calendar, float_leg_direction_1, 
               date_generation_rule, sch_convention, end_convention, payment_convention, 
               reset_convention_1, fixing_convention_1, end_of_month, is_ois_leg_1, compounding_type_1, 
               is_init_notional_ex, is_final_notional_ex, final_notional_ex_payment_delay)
        
        self.float_leg_2 = rl.StandardFloatLeg(
               ccy, index_name_2, effective_date, maturity_date, float_leg_pay_freq_2, 
               reset_freq_2, notional, multiplier_2, spread_2, float_leg_daycount_2, payment_delay, 
               fixing_days_2, sch_calendar, fixing_calendar_2, payment_calendar, float_leg_direction_2, 
               date_generation_rule, sch_convention, end_convention, payment_convention, 
               reset_convention_2, fixing_convention_2, end_of_month, is_ois_leg_2, compounding_type_2, 
               is_init_notional_ex, is_final_notional_ex, final_notional_ex_payment_delay)
 