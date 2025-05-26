import QuantLib as ql
import numpy as np

import devlib.products.rates.irs.rate_legs as rl
from ....utils.fx_utils import fx_ccy_trans



# only for fixed to float ccs
class FloatFixedCcs:
    def __init__(
            self, 
            fixed_leg_ccy: str, 
            float_leg_ccy: str, 
            settlement_ccy: str, 
            fx_pair: str, 
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
            init_fixed_notional_ex: float = 0.0, 
            init_float_notional_ex: float = 0.0, 
            init_notional_ex_paydate: ql.Date = None, 
            is_final_notional_ex: bool = False, 
            final_fixed_notional_ex: float = 0.0, 
            final_float_notional_ex: float = 0.0, 
            final_fixed_notional_ex_paydate: ql.Date = None, 
            final_float_notional_ex_paydate: ql.Date = None, 
            ):
        if settlement_ccy not in [fixed_leg_ccy, float_leg_ccy]:
            raise Exception(f'Settlement currency must be fixed or float leg currency!')
        else:
            self.settlement_ccy = settlement_ccy
        
        self.fx_pair = fx_pair
        
        fixed_leg_direction = fixed_leg_direction.lower()
        float_leg_direction = float_leg_direction.lower()

        self.fixed_leg = rl.FixedLeg(
            fixed_leg_ccy, fixed_leg_start_dates, fixed_leg_end_dates, fixed_leg_payment_dates, 
            fixed_leg_notionals, fixed_leg_fixed_rates, fixed_leg_daycount, fixed_leg_direction, 
            is_init_notional_ex, init_fixed_notional_ex, init_notional_ex_paydate, 
            is_final_notional_ex, final_fixed_notional_ex, final_fixed_notional_ex_paydate)
        
        self.float_leg = rl.FloatLeg(
            float_leg_ccy, float_leg_index_name, float_leg_start_dates, float_leg_end_dates, 
            float_leg_reset_dates_array, float_leg_fixing_dates_array, float_leg_payment_dates, 
            float_leg_notionals, float_leg_multiplier, float_leg_spread, float_leg_daycount, 
            float_leg_direction, float_leg_is_ois_leg, float_leg_compounding_type, 
            is_init_notional_ex, init_float_notional_ex, init_notional_ex_paydate, 
            is_final_notional_ex, final_float_notional_ex, final_float_notional_ex_paydate)

    
    def npv(self, today, index_curve, fixed_discount_curve, float_discount_curve, fx_spot):
        fixed_leg_npv = self.fixed_leg.npv(today, fixed_discount_curve)
        float_leg_npv = self.float_leg.npv(today, index_curve, float_discount_curve)
        if self.fixed_leg.ccy == self.settlement_ccy:
            fx_spot_adj = fx_ccy_trans(1, self.float_leg.ccy, fx_spot, self.fx_pair)
            return fixed_leg_npv + float_leg_npv * fx_spot_adj
        else:
            fx_spot_adj = fx_ccy_trans(1, self.fixed_leg.ccy, fx_spot, self.fx_pair)
            return fixed_leg_npv * fx_spot_adj + float_leg_npv


    def fair_rate(self, today, index_curve, fixed_discount_curve, float_discount_curve, fx_spot):        
        annuity = self.fixed_leg.annuity(today, fixed_discount_curve)
        fixed_notional_ex_npv = self.fixed_leg.notional_ex_npv(today, fixed_discount_curve)
        if annuity < 1e-8:
            return None
        float_leg_npv = self.float_leg.npv(today, index_curve, float_discount_curve)
        fixed_trade_direction = -1 if self.fixed_leg.trade_direction == 'pay' else 1

        if self.fixed_leg.ccy == self.settlement_ccy:
            fx_spot_adj = fx_ccy_trans(1, self.float_leg.ccy, fx_spot, self.fx_pair)
            float_leg_npv *= fx_spot_adj
        else:
            fx_spot_adj = fx_ccy_trans(1, self.fixed_leg.ccy, fx_spot, self.fx_pair)
            annuity *= fx_spot_adj
            fixed_notional_ex_npv *= fx_spot_adj
        
        fair_rate = (-float_leg_npv - fixed_notional_ex_npv) / (annuity * fixed_trade_direction)

        return fair_rate
    
    
    def dv01s_parallel_orig_ccy(
            self, today, index_curve, fixed_discount_curve, float_discount_curve, tweak=1e-4):
        index_curve_up = index_curve.tweak_parallel(tweak)
        index_curve_down = index_curve.tweak_parallel(-tweak)
        fixed_discount_curve_up = fixed_discount_curve.tweak_parallel(tweak)
        fixed_discount_curve_down = fixed_discount_curve.tweak_parallel(-tweak)
        float_discount_curve_up = float_discount_curve.tweak_parallel(tweak)
        float_discount_curve_down = float_discount_curve.tweak_parallel(-tweak)

        dv01_fixed_discount = (
            self.fixed_leg.npv(today, fixed_discount_curve_up) - 
            self.fixed_leg.npv(today, fixed_discount_curve_down)) / (2 * tweak) * 1e-4
        
        dv01_float_discount = (
            self.float_leg.npv(today, index_curve, float_discount_curve_up) - 
            self.float_leg.npv(today, index_curve, float_discount_curve_down)) / (2 * tweak) * 1e-4
        
        dv01_float_index = (
            self.float_leg.npv(today, index_curve_up, float_discount_curve) - 
            self.float_leg.npv(today, index_curve_down, float_discount_curve)) / (2 * tweak) * 1e-4
        
        dv01s = {}
        dv01s['DV01_FIXED_DISCOUNT'] = dv01_fixed_discount
        dv01s['DV01_FLOAT_DISCOUNT'] = dv01_float_discount
        dv01s['DV01_FLOAT_INDEX'] = dv01_float_index

        return dv01s
    

    def dv01s_parallel_settle_ccy(
            self, today, index_curve, fixed_discount_curve, float_discount_curve, fx_spot, tweak=1e-4):
        dv01s = self.dv01s_parallel_orig_ccy(
            today, index_curve, fixed_discount_curve, float_discount_curve, tweak)
        if self.fixed_leg.ccy == self.settlement_ccy:
            fx_spot_adj = fx_ccy_trans(1, self.float_leg.ccy, fx_spot, self.fx_pair)
            dv01s['DV01_FLOAT_DISCOUNT'] = dv01s['DV01_FLOAT_DISCOUNT'] * fx_spot_adj
            dv01s['DV01_FLOAT_INDEX'] = dv01s['DV01_FLOAT_INDEX'] * fx_spot_adj
        else:
            fx_spot_adj = fx_ccy_trans(1, self.fixed_leg.ccy, fx_spot, self.fx_pair)
            dv01s['DV01_FIXED_DISCOUNT'] = dv01s['DV01_FIXED_DISCOUNT'] * fx_spot_adj

        return dv01s
    


class StandardFloatFixedCcs(FloatFixedCcs):
    def __init__(
            self, 
            fixed_leg_ccy: str, 
            float_leg_ccy: str, 
            settlement_ccy: str, 
            fx_pair: str, 
            index_name: str, 
            effective_date: ql.Date, 
            maturity_date: ql.Date, 
            fixed_leg_pay_freq: str, 
            float_leg_pay_freq: str, 
            reset_freq: str, 
            fixed_notional: float, 
            float_notional: float, 
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
        if settlement_ccy not in [fixed_leg_ccy, float_leg_ccy]:
            raise Exception(f'Settlement currency must be fixed or float leg currency!')
        else:
            self.settlement_ccy = settlement_ccy
        
        self.fx_pair = fx_pair
        
        fixed_leg_direction = fixed_leg_direction.lower()
        float_leg_direction = float_leg_direction.lower()

        self.fixed_leg = rl.StandardFixedLeg(
               fixed_leg_ccy, effective_date, maturity_date, fixed_leg_pay_freq, fixed_notional, 
               fixed_rate, fixed_leg_daycount, payment_delay, sch_calendar, 
               payment_calendar, fixed_leg_direction, date_generation_rule, 
               sch_convention, end_convention, payment_convention, end_of_month, 
               is_init_notional_ex, is_final_notional_ex, final_notional_ex_payment_delay)
        
        self.float_leg = rl.StandardFloatLeg(
               float_leg_ccy, index_name, effective_date, maturity_date, float_leg_pay_freq, 
               reset_freq, float_notional, multiplier, spread, float_leg_daycount, payment_delay, 
               fixing_days, sch_calendar, fixing_calendar, payment_calendar, float_leg_direction, 
               date_generation_rule, sch_convention, end_convention, payment_convention, 
               reset_convention, fixing_convention, end_of_month, is_ois_leg, compounding_type, 
               is_init_notional_ex, is_final_notional_ex, final_notional_ex_payment_delay)
        
        

# only for fixed to fixed ccs       
class FixedFixedCcs:
    def __init__(
            self, 
            fixed_leg_ccy_1: str, 
            fixed_leg_ccy_2: str, 
            settlement_ccy: str, 
            fx_pair: str, 
            fixed_leg_start_dates_1: np.ndarray, 
            fixed_leg_end_dates_1: np.ndarray, 
            fixed_leg_payment_dates_1: np.ndarray, 
            fixed_leg_notionals_1: np.ndarray, 
            fixed_leg_fixed_rates_1: np.ndarray, 
            fixed_leg_daycount_1: ql.DayCounter, 
            fixed_leg_direction_1: str, 
            fixed_leg_start_dates_2: np.ndarray, 
            fixed_leg_end_dates_2: np.ndarray, 
            fixed_leg_payment_dates_2: np.ndarray, 
            fixed_leg_notionals_2: np.ndarray, 
            fixed_leg_fixed_rates_2: np.ndarray, 
            fixed_leg_daycount_2: ql.DayCounter, 
            fixed_leg_direction_2: str, 
            is_init_notional_ex: bool = False, 
            init_notional_ex_1: float = 0.0, 
            init_notional_ex_2: float = 0.0, 
            init_notional_ex_paydate: ql.Date = None, 
            is_final_notional_ex: bool = False, 
            final_notional_ex_1: float = 0.0, 
            final_notional_ex_2: float = 0.0, 
            final_notional_ex_paydate_1: ql.Date = None, 
            final_notional_ex_paydate_2: ql.Date = None, 
            ):
        if settlement_ccy not in [fixed_leg_ccy_1, fixed_leg_ccy_2]:
            raise Exception(f'Settlement currency must be fixed or float leg currency!')
        else:
            self.settlement_ccy = settlement_ccy
        
        self.fx_pair = fx_pair
        
        fixed_leg_direction_1 = fixed_leg_direction_1.lower()
        fixed_leg_direction_2 = fixed_leg_direction_2.lower()

        self.fixed_leg_1 = rl.FixedLeg(
            fixed_leg_ccy_1, fixed_leg_start_dates_1, fixed_leg_end_dates_1, fixed_leg_payment_dates_1, 
            fixed_leg_notionals_1, fixed_leg_fixed_rates_1, fixed_leg_daycount_1, fixed_leg_direction_1, 
            is_init_notional_ex, init_notional_ex_1, init_notional_ex_paydate, 
            is_final_notional_ex, final_notional_ex_1, final_notional_ex_paydate_1)
        
        self.fixed_leg_2 = rl.FixedLeg(
            fixed_leg_ccy_2, fixed_leg_start_dates_2, fixed_leg_end_dates_2, fixed_leg_payment_dates_2, 
            fixed_leg_notionals_2, fixed_leg_fixed_rates_2, fixed_leg_daycount_2, fixed_leg_direction_2, 
            is_init_notional_ex, init_notional_ex_2, init_notional_ex_paydate, 
            is_final_notional_ex, final_notional_ex_2, final_notional_ex_paydate_2)
        
    
    def npv(self, today, discount_curve_1, discount_curve_2, fx_spot):
        fixed_leg_1_npv = self.fixed_leg_1.npv(today, discount_curve_1)
        fixed_leg_2_npv = self.fixed_leg_2.npv(today, discount_curve_2)
        if self.fixed_leg_1.ccy == self.settlement_ccy:
            fx_spot_adj = fx_ccy_trans(1, self.fixed_leg_2.ccy, fx_spot, self.fx_pair)
            # print(fixed_leg_1_npv, fixed_leg_2_npv * fx_spot_adj)
            return fixed_leg_1_npv + fixed_leg_2_npv * fx_spot_adj
        else:
            fx_spot_adj = fx_ccy_trans(1, self.fixed_leg_1.ccy, fx_spot, self.fx_pair)
            # print(fixed_leg_1_npv * fx_spot_adj, fixed_leg_2_npv)
            return fixed_leg_1_npv * fx_spot_adj + fixed_leg_2_npv
    
    
    def dv01s_parallel_orig_ccy(self, today, discount_curve_1, discount_curve_2, tweak=1e-4):
        discount_curve_1_up = discount_curve_1.tweak_parallel(tweak)
        discount_curve_1_down = discount_curve_1.tweak_parallel(-tweak)
        discount_curve_2_up = discount_curve_2.tweak_parallel(tweak)
        discount_curve_2_down = discount_curve_2.tweak_parallel(-tweak)

        dv01_discount_1 = (
            self.fixed_leg_1.npv(today, discount_curve_1_up) - 
            self.fixed_leg_1.npv(today, discount_curve_1_down)) / (2 * tweak) * 1e-4
        
        dv01_discount_2 = (
            self.fixed_leg_2.npv(today, discount_curve_2_up) - 
            self.fixed_leg_2.npv(today, discount_curve_2_down)) / (2 * tweak) * 1e-4
        
        dv01s = {}
        dv01s['DV01_DISCOUNT_1'] = dv01_discount_1
        dv01s['DV01_DISCOUNT_2'] = dv01_discount_2

        return dv01s
    

    def dv01s_parallel_settle_ccy(self, today, discount_curve_1, discount_curve_2, fx_spot, tweak=1e-4):
        dv01s = self.dv01s_parallel_orig_ccy(today, discount_curve_1, discount_curve_2, tweak)
        if self.fixed_leg_1.ccy == self.settlement_ccy:
            fx_spot_adj = fx_ccy_trans(1, self.fixed_leg_2.ccy, fx_spot, self.fx_pair)
            dv01s['DV01_DISCOUNT_2'] = dv01s['DV01_DISCOUNT_2'] * fx_spot_adj
        else:
            fx_spot_adj = fx_ccy_trans(1, self.fixed_leg_1.ccy, fx_spot, self.fx_pair)
            dv01s['DV01_DISCOUNT_1'] = dv01s['DV01_DISCOUNT_1'] * fx_spot_adj

        return dv01s
    
    
    
class StandardFixedFixedCcs(FixedFixedCcs):
    def __init__(
            self, 
            fixed_leg_ccy_1: str, 
            fixed_leg_ccy_2: str, 
            settlement_ccy: str, 
            fx_pair: str, 
            effective_date: ql.Date, 
            maturity_date: ql.Date, 
            fixed_leg_pay_freq_1: str, 
            fixed_leg_pay_freq_2: str, 
            notional_1: float, 
            notional_2: float, 
            fixed_rate_1: float, 
            fixed_rate_2: float, 
            fixed_leg_daycount_1: ql.DayCounter, 
            fixed_leg_daycount_2: ql.DayCounter, 
            payment_delay: int, 
            sch_calendar: ql.Calendar, 
            payment_calendar: ql.Calendar,
            fixed_leg_direction_1: str, 
            fixed_leg_direction_2: str,
            date_generation_rule=ql.DateGeneration.Forward,
            sch_convention=ql.ModifiedFollowing,
            end_convention=ql.ModifiedFollowing,
            payment_convention=ql.ModifiedFollowing, 
            end_of_month: bool = False, 
            is_init_notional_ex: bool = False,
            is_final_notional_ex: bool = False, 
            final_notional_ex_payment_delay: int = 0, 
            ):
        if settlement_ccy not in [fixed_leg_ccy_1, fixed_leg_ccy_2]:
            raise Exception(f'Settlement currency must be fixed or float leg currency!')
        else:
            self.settlement_ccy = settlement_ccy
        
        self.fx_pair = fx_pair
        
        fixed_leg_direction_1 = fixed_leg_direction_1.lower()
        fixed_leg_direction_2 = fixed_leg_direction_2.lower()

        self.fixed_leg_1 = rl.StandardFixedLeg(
               fixed_leg_ccy_1, effective_date, maturity_date, fixed_leg_pay_freq_1, notional_1, 
               fixed_rate_1, fixed_leg_daycount_1, payment_delay, sch_calendar, 
               payment_calendar, fixed_leg_direction_1, date_generation_rule, 
               sch_convention, end_convention, payment_convention, end_of_month, 
               is_init_notional_ex, is_final_notional_ex, final_notional_ex_payment_delay)
        
        self.fixed_leg_2 = rl.StandardFixedLeg(
               fixed_leg_ccy_2, effective_date, maturity_date, fixed_leg_pay_freq_2, notional_2, 
               fixed_rate_2, fixed_leg_daycount_2, payment_delay, sch_calendar, 
               payment_calendar, fixed_leg_direction_2, date_generation_rule, 
               sch_convention, end_convention, payment_convention, end_of_month, 
               is_init_notional_ex, is_final_notional_ex, final_notional_ex_payment_delay)
        


# only for float to float ccs
class FloatFloatCcs:
    def __init__(
            self, 
            float_leg_ccy_1: str, 
            float_leg_ccy_2: str, 
            settlement_ccy: str, 
            fx_pair: str, 
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
            init_notional_ex_1: float = 0.0, 
            init_notional_ex_2: float = 0.0, 
            init_notional_ex_paydate: ql.Date = None, 
            is_final_notional_ex: bool = False, 
            final_notional_ex_1: float = 0.0, 
            final_notional_ex_2: float = 0.0, 
            final_notional_ex_paydate_1: ql.Date = None, 
            final_notional_ex_paydate_2: ql.Date = None,
            ):
        if settlement_ccy not in [float_leg_ccy_1, float_leg_ccy_2]:
            raise Exception(f'Settlement currency must be fixed or float leg currency!')
        else:
            self.settlement_ccy = settlement_ccy
        
        self.fx_pair = fx_pair
        
        float_leg_direction_1 = float_leg_direction_1.lower()
        float_leg_direction_2 = float_leg_direction_2.lower()

        self.float_leg_1 = rl.FloatLeg(
            float_leg_ccy_1, float_leg_index_name_1, float_leg_start_dates_1, float_leg_end_dates_1, 
            float_leg_reset_dates_array_1, float_leg_fixing_dates_array_1, float_leg_payment_dates_1, 
            float_leg_notionals_1, float_leg_multiplier_1, float_leg_spread_1, float_leg_daycount_1, 
            float_leg_direction_1, float_leg_is_ois_leg_1, float_leg_compounding_type_1, 
            is_init_notional_ex, init_notional_ex_1, init_notional_ex_paydate, 
            is_final_notional_ex, final_notional_ex_1, final_notional_ex_paydate_1)
        
        self.float_leg_2 = rl.FloatLeg(
            float_leg_ccy_2, float_leg_index_name_2, float_leg_start_dates_2, float_leg_end_dates_2, 
            float_leg_reset_dates_array_2, float_leg_fixing_dates_array_2, float_leg_payment_dates_2, 
            float_leg_notionals_2, float_leg_multiplier_2, float_leg_spread_2, float_leg_daycount_2, 
            float_leg_direction_2, float_leg_is_ois_leg_2, float_leg_compounding_type_2, 
            is_init_notional_ex, init_notional_ex_2, init_notional_ex_paydate, 
            is_final_notional_ex, final_notional_ex_2, final_notional_ex_paydate_2)

    
    def npv(self, today, index_curve_1, discount_curve_1, index_curve_2, discount_curve_2, fx_spot):
        float_leg_1_npv = self.float_leg_1.npv(today, index_curve_1, discount_curve_1)
        float_leg_2_npv = self.float_leg_2.npv(today, index_curve_2, discount_curve_2)
        if self.float_leg_1.ccy == self.settlement_ccy:
            fx_spot_adj = fx_ccy_trans(1, self.float_leg_2.ccy, fx_spot, self.fx_pair)
            return float_leg_1_npv + float_leg_2_npv * fx_spot_adj
        else:
            fx_spot_adj = fx_ccy_trans(1, self.float_leg_1.ccy, fx_spot, self.fx_pair)
            return float_leg_1_npv * fx_spot_adj + float_leg_2_npv
    
    
    def dv01s_parallel_orig_ccy(
            self, today, index_curve_1, discount_curve_1, index_curve_2, discount_curve_2, tweak=1e-4):
        index_curve_1_up = index_curve_1.tweak_parallel(tweak)
        index_curve_1_down = index_curve_1.tweak_parallel(-tweak)
        discount_curve_1_up = discount_curve_1.tweak_parallel(tweak)
        discount_curve_1_down = discount_curve_1.tweak_parallel(-tweak)
        index_curve_2_up = index_curve_2.tweak_parallel(tweak)
        index_curve_2_down = index_curve_2.tweak_parallel(-tweak)
        discount_curve_2_up = discount_curve_2.tweak_parallel(tweak)
        discount_curve_2_down = discount_curve_2.tweak_parallel(-tweak)

        dv01_discount_1 = (
            self.float_leg_1.npv(today, index_curve_1, discount_curve_1_up) - 
            self.float_leg_1.npv(today, index_curve_1, discount_curve_1_down)) / (2 * tweak) * 1e-4
        
        dv01_index_1 = (
            self.float_leg_1.npv(today, index_curve_1_up, discount_curve_1) - 
            self.float_leg_1.npv(today, index_curve_1_down, discount_curve_1)) / (2 * tweak) * 1e-4
        
        dv01_discount_2 = (
            self.float_leg_2.npv(today, index_curve_2, discount_curve_2_up) - 
            self.float_leg_2.npv(today, index_curve_2, discount_curve_2_down)) / (2 * tweak) * 1e-4
        
        dv01_index_2 = (
            self.float_leg_2.npv(today, index_curve_2_up, discount_curve_2) - 
            self.float_leg_2.npv(today, index_curve_2_down, discount_curve_2)) / (2 * tweak) * 1e-4
        
        dv01s = {}
        dv01s['DV01_DISCOUNT_1'] = dv01_discount_1
        dv01s['DV01_INDEX_1'] = dv01_index_1
        dv01s['DV01_DISCOUNT_2'] = dv01_discount_2
        dv01s['DV01_INDEX_2'] = dv01_index_2

        return dv01s
    

    def dv01s_parallel_settle_ccy(
            self, today, index_curve_1, discount_curve_1, index_curve_2, discount_curve_2, fx_spot, tweak=1e-4):
        dv01s = self.dv01s_parallel_orig_ccy(
            today, index_curve_1, discount_curve_1, index_curve_2, discount_curve_2, tweak)
        if self.float_leg_1.ccy == self.settlement_ccy:
            fx_spot_adj = fx_ccy_trans(1, self.float_leg_2.ccy, fx_spot, self.fx_pair)
            dv01s['DV01_DISCOUNT_2'] = dv01s['DV01_DISCOUNT_2'] * fx_spot_adj
            dv01s['DV01_INDEX_2'] = dv01s['DV01_INDEX_2'] * fx_spot_adj
        else:
            fx_spot_adj = fx_ccy_trans(1, self.float_leg_1.ccy, fx_spot, self.fx_pair)
            dv01s['DV01_DISCOUNT_1'] = dv01s['DV01_DISCOUNT_1'] * fx_spot_adj
            dv01s['DV01_INDEX_1'] = dv01s['DV01_INDEX_1'] * fx_spot_adj

        return dv01s
    


class StandardFloatFloatCcs(FloatFloatCcs):
    def __init__(
            self, 
            float_leg_ccy_1: str, 
            float_leg_ccy_2: str, 
            settlement_ccy: str, 
            fx_pair: str, 
            index_name_1: str, 
            index_name_2: str, 
            effective_date: ql.Date, 
            maturity_date: ql.Date, 
            float_leg_pay_freq_1: str, 
            float_leg_pay_freq_2: str, 
            reset_freq_1: str, 
            reset_freq_2: str, 
            notional_1: float, 
            notional_2: float, 
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
        if settlement_ccy not in [float_leg_ccy_1, float_leg_ccy_2]:
            raise Exception(f'Settlement currency must be fixed or float leg currency!')
        else:
            self.settlement_ccy = settlement_ccy
        
        self.fx_pair = fx_pair
        
        float_leg_direction_1 = float_leg_direction_1.lower()
        float_leg_direction_2 = float_leg_direction_2.lower()
        
        self.float_leg_1 = rl.StandardFloatLeg(
               float_leg_ccy_1, index_name_1, effective_date, maturity_date, float_leg_pay_freq_1, 
               reset_freq_1, notional_1, multiplier_1, spread_1, float_leg_daycount_1, payment_delay, 
               fixing_days_1, sch_calendar, fixing_calendar_1, payment_calendar, float_leg_direction_1, 
               date_generation_rule, sch_convention, end_convention, payment_convention, 
               reset_convention_1, fixing_convention_1, end_of_month, is_ois_leg_1, compounding_type_1, 
               is_init_notional_ex, is_final_notional_ex, final_notional_ex_payment_delay)
        
        self.float_leg_2 = rl.StandardFloatLeg(
               float_leg_ccy_2, index_name_2, effective_date, maturity_date, float_leg_pay_freq_2, 
               reset_freq_2, notional_2, multiplier_2, spread_2, float_leg_daycount_2, payment_delay, 
               fixing_days_2, sch_calendar, fixing_calendar_2, payment_calendar, float_leg_direction_2, 
               date_generation_rule, sch_convention, end_convention, payment_convention, 
               reset_convention_2, fixing_convention_2, end_of_month, is_ois_leg_2, compounding_type_2, 
               is_init_notional_ex, is_final_notional_ex, final_notional_ex_payment_delay)
        