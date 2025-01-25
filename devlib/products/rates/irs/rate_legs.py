# -*- coding: utf-8 -*-
"""
Created on Sun Oct  8 16:11:51 2023

@author: xieyushan
"""

import QuantLib as ql
import numpy as np

from ....utils.curve_utils import get_ois_float_rate, get_comp_float_rate
   

class FixedLeg:
    def __init__(
            self, 
            ccy: str,
            start_dates: np.ndarray, 
            end_dates: np.ndarray, 
            payment_dates: np.ndarray, 
            notionals: np.ndarray, 
            fixed_rates: np.ndarray, 
            daycount: ql.DayCounter,
            trade_direction: str,
            is_init_notional_ex: bool = False,
            init_notional_ex: float = 0.0,
            init_notional_ex_paydate: ql.Date = None,
            is_final_notional_ex: bool = False,
            final_notional_ex: float = 0.0,
            final_notional_ex_paydate: ql.Date = None, 
            ):
        self.ccy = ccy
        self.start_dates = start_dates
        self.end_dates = end_dates
        self.payment_dates = payment_dates      
        self.notionals = notionals
        self.fixed_rates = fixed_rates
        self.daycount = daycount
        self.trade_direction = trade_direction.lower()
        self.is_init_notional_ex = is_init_notional_ex
        self.init_notional_ex = init_notional_ex
        self.init_notional_ex_paydate = init_notional_ex_paydate
        self.is_final_notional_ex = is_final_notional_ex
        self.final_notional_ex = final_notional_ex
        self.final_notional_ex_paydate = final_notional_ex_paydate
        
        
    def npv(self, today, discount_curve):
        disc_curve = discount_curve.curve
        
        if today >= max(self.payment_dates):
            npv = 0.0
        else:
            # 计算区间长度
            periods = np.array(
                [self.daycount.yearFraction(start_date, end_date) 
                 for start_date, end_date in zip(self.start_dates, self.end_dates)])
            # 计算区间收益
            cashflow = self.notionals * periods * self.fixed_rates
            # 计算折现因子
            dfs = [disc_curve.discount(paydate) / disc_curve.discount(today) 
                   for paydate in self.payment_dates if paydate > today]
            npv = np.dot(cashflow[self.payment_dates > today], dfs)
        
        npv *= 1 if self.trade_direction == 'receive' else -1
        npv += self.notional_ex_npv(today, discount_curve)

        return npv
    
    
    def annuity(self, today, discount_curve):
        disc_curve = discount_curve.curve
        
        if today >= max(self.payment_dates):
            annuity = 0.0
        else:
            # 计算区间长度
            periods = np.array(
                [self.daycount.yearFraction(start_date, end_date) 
                 for start_date, end_date in zip(self.start_dates, self.end_dates)])
            # 计算区间收益
            annuity_flow = self.notionals * periods
            # 计算折现因子
            dfs = [disc_curve.discount(paydate) / disc_curve.discount(today) 
                   for paydate in self.payment_dates if paydate > today]
            annuity = np.dot(annuity_flow[self.payment_dates > today], dfs)
        
        return annuity
    
    
    def notional_ex_npv(self, today, discount_curve):
        disc_curve = discount_curve.curve
        npv = 0.0
        # 考虑本金交换(对receive方向，默认期初支付本金，期末回收本金)
        if self.is_init_notional_ex and self.init_notional_ex_paydate > today:
            init_ex_df = (disc_curve.discount(self.init_notional_ex_paydate) / 
                          disc_curve.discount(today))
            npv -= self.init_notional_ex * init_ex_df
            
        if self.is_final_notional_ex and self.final_notional_ex_paydate > today:
            final_ex_df = (disc_curve.discount(self.final_notional_ex_paydate) / 
                           disc_curve.discount(today))
            npv += self.final_notional_ex * final_ex_df
            
        npv *= 1 if self.trade_direction == 'receive' else -1
            
        return npv



class StandardFixedLeg(FixedLeg):
    def __init__(
            self, 
            ccy: str,
            effective_date: ql.Date, 
            maturity_date: ql.Date, 
            pay_freq: str,
            notional: float, 
            fixed_rate: float, 
            daycount: ql.DayCounter,
            payment_delay: int,
            sch_calendar: ql.Calendar,
            payment_calendar: ql.Calendar,
            trade_direction: str,
            date_generation_rule=ql.DateGeneration.Forward,
            sch_convention=ql.ModifiedFollowing,
            end_convention=ql.ModifiedFollowing,
            payment_convention=ql.ModifiedFollowing,
            end_of_month: bool = False,
            is_init_notional_ex: bool = False, 
            is_final_notional_ex: bool = False, 
            final_notional_ex_payment_delay: int = 0, 
            ):
        self.effective_date = effective_date
        self.maturity_date = maturity_date
        self.pay_freq = pay_freq
        self.notional = notional
        self.fixed_rate = fixed_rate
        self.payment_delay = payment_delay
        self.sch_calendar = sch_calendar
        self.payment_calendar = payment_calendar
        self.date_generation_rule = date_generation_rule
        self.sch_convention = sch_convention
        self.end_convention = end_convention
        self.payment_convention = payment_convention
        self.end_of_month = end_of_month

        start_dates, end_dates, payment_dates \
            = StandardFixedLeg.get_standard_schedule(
                effective_date, maturity_date, pay_freq, payment_delay, 
                sch_calendar, payment_calendar, date_generation_rule, 
                sch_convention, end_convention, payment_convention, end_of_month)
        
        notionals = np.array([self.notional] * len(start_dates))
        fixed_rates = np.array([self.fixed_rate] * len(start_dates))
        init_notional_ex_paydate = effective_date
        final_notional_ex_paydate = payment_calendar.advance(
            end_dates[-1], ql.Period(final_notional_ex_payment_delay, ql.Days), payment_convention)
        
        FixedLeg.__init__(
            self, ccy, start_dates, end_dates, payment_dates, notionals, fixed_rates, 
            daycount, trade_direction, is_init_notional_ex, notional, init_notional_ex_paydate, 
            is_final_notional_ex, notional, final_notional_ex_paydate)
        

    @staticmethod
    def get_standard_schedule(
            start, end, pay_freq, payment_delay, sch_calendar, payment_calendar, 
            date_generation_rule=ql.DateGeneration.Forward, 
            sch_convention=ql.ModifiedFollowing, end_convention=ql.ModifiedFollowing, 
            payment_convention=ql.ModifiedFollowing, end_of_month=False):
        schedule_dates = np.array(ql.Schedule(
            start, end, ql.Period(pay_freq), sch_calendar, sch_convention, 
            end_convention, date_generation_rule, end_of_month))
        start_dates = schedule_dates[:-1]
        end_dates = schedule_dates[1:]
        payment_dates = np.array(
            [payment_calendar.advance(end_date, ql.Period(payment_delay, ql.Days), 
                                      payment_convention) for end_date in end_dates])
        
        return start_dates, end_dates, payment_dates



class FloatLeg:
    def __init__(
            self, 
            ccy: str,
            index_name: str, 
            start_dates: np.ndarray, 
            end_dates: np.ndarray, 
            reset_dates_array: np.ndarray,
            fixing_dates_array: np.ndarray,
            payment_dates: np.ndarray, 
            notionals: np.ndarray,
            multiplier: float,
            spread: float,
            daycount: ql.DayCounter,
            trade_direction: str,
            is_ois_leg: bool = False,
            compounding_type: str = 'ExcludeSprd',
            is_init_notional_ex: bool = False,
            init_notional_ex: float = 0.0,
            init_notional_ex_paydate: ql.Date = None,
            is_final_notional_ex: bool = False,
            final_notional_ex: float = 0.0,
            final_notional_ex_paydate: ql.Date = None, 
            ):
        self.ccy = ccy
        self.index_name = index_name
        self.start_dates = start_dates
        self.end_dates = end_dates
        self.reset_dates_array = reset_dates_array
        self.fixing_dates_array = fixing_dates_array
        self.payment_dates = payment_dates
        self.notionals = notionals
        self.multiplier = multiplier
        self.spread = spread
        self.compounding_type = compounding_type
        self.daycount = daycount
        self.trade_direction = trade_direction.lower()
        self.is_ois_leg = is_ois_leg
        self.is_init_notional_ex = is_init_notional_ex
        self.init_notional_ex = init_notional_ex
        self.init_notional_ex_paydate = init_notional_ex_paydate
        self.is_final_notional_ex = is_final_notional_ex
        self.final_notional_ex = final_notional_ex
        self.final_notional_ex_paydate = final_notional_ex_paydate
    
    
    def get_float_rates(self, today, index_curve, only_future_float_rates=True):
        if only_future_float_rates:
            start_dates = self.start_dates[self.payment_dates > today]
            end_dates = self.end_dates[self.payment_dates > today]
        else:
            start_dates = self.start_dates
            end_dates = self.end_dates
        
        float_rates = []
        if self.is_ois_leg:
            for start_date, end_date in zip(start_dates, end_dates):
                float_rate = get_ois_float_rate(
                    index_curve, today, start_date, end_date, self.daycount, self.spread)
                float_rates.append(float_rate)
        else:
            if only_future_float_rates:
                fixing_dates_array = self.fixing_dates_array[self.payment_dates > today]
                reset_dates_array = self.reset_dates_array[self.payment_dates > today]
            else:
                fixing_dates_array = self.fixing_dates_array
                reset_dates_array = self.reset_dates_array
            
            for fixing_dates, reset_dates, end_date in zip(
                    fixing_dates_array, reset_dates_array, end_dates):
                float_rate = get_comp_float_rate(
                    index_curve, today, fixing_dates, reset_dates, end_date, 
                    self.multiplier, self.spread, self.daycount, self.compounding_type)
                float_rates.append(float_rate)
        
        return np.array(float_rates)

    
    def npv(self, today, index_curve, discount_curve):
        disc_curve = discount_curve.curve
        
        if today >= max(self.payment_dates):
            npv = 0.0
        
        else:
            #计算区间长度
            periods = np.array(
                [self.daycount.yearFraction(start_date, end_date) 
                 for start_date, end_date in zip(self.start_dates, self.end_dates)])
            periods = periods[self.payment_dates > today]
            #计算区间收益
            future_notionals = self.notionals[self.payment_dates > today]
            cashflow = future_notionals * periods * self.get_float_rates(today, index_curve)
            #计算折现因子
            dfs = [disc_curve.discount(payment_date) / disc_curve.discount(today) 
                   for payment_date in self.payment_dates if payment_date > today]
            npv = np.dot(cashflow, dfs)
 
        npv *= 1 if self.trade_direction == 'receive' else -1
        npv += self.notional_ex_npv(today, discount_curve)
        
        return npv
    
    
    def notional_ex_npv(self, today, discount_curve):
        disc_curve = discount_curve.curve
        npv = 0.0
        # 考虑本金交换(对receive方向，默认期初支付本金，期末回收本金)
        if self.is_init_notional_ex and self.init_notional_ex_paydate > today:
            init_ex_df = (disc_curve.discount(self.init_notional_ex_paydate) / 
                          disc_curve.discount(today))
            npv -= self.init_notional_ex * init_ex_df
            
        if self.is_final_notional_ex and self.final_notional_ex_paydate > today:
            final_ex_df = (disc_curve.discount(self.final_notional_ex_paydate) / 
                           disc_curve.discount(today))
            npv += self.final_notional_ex * final_ex_df
            
        npv *= 1 if self.trade_direction == 'receive' else -1
            
        return npv
    


class StandardFloatLeg(FloatLeg):
    def __init__(
            self, 
            ccy: str,
            index_name: str,
            effective_date: ql.Date, 
            maturity_date: ql.Date, 
            pay_freq: str,
            reset_freq: str,
            notional: float, 
            multiplier: float,
            spread: float,
            daycount: ql.DayCounter, 
            payment_delay: int,
            fixing_days: int,
            sch_calendar: ql.Calendar, 
            fixing_calendar: ql.Calendar, 
            payment_calendar: ql.Calendar,
            trade_direction: str,
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
        self.effective_date = effective_date
        self.maturity_date = maturity_date
        self.pay_freq = pay_freq
        self.reset_freq = reset_freq
        self.notional = notional
        self.payment_delay = payment_delay
        self.fixing_days = fixing_days
        self.sch_calendar = sch_calendar
        self.fixing_calendar = fixing_calendar
        self.payment_calendar = payment_calendar 
        self.date_generation_rule = date_generation_rule
        self.sch_convention = sch_convention
        self.end_convention = end_convention
        self.payment_convention = payment_convention
        self.reset_convention = reset_convention 
        self.fixing_convention = fixing_convention
        self.end_of_month = end_of_month

        if is_ois_leg:
            start_dates, end_dates, payment_dates \
                = StandardFixedLeg.get_standard_schedule(
                    effective_date, maturity_date, pay_freq, payment_delay, 
                    sch_calendar, payment_calendar, date_generation_rule, 
                    sch_convention, end_convention, payment_convention, end_of_month)
            reset_dates_array = None
            fixing_dates_array = None
        
        else:
            (start_dates, end_dates, payment_dates, reset_dates_array, 
             fixing_dates_array) = StandardFloatLeg.get_standard_float_schedule(
                effective_date, maturity_date, pay_freq, reset_freq, payment_delay, 
                fixing_days, sch_calendar, fixing_calendar, payment_calendar, 
                date_generation_rule, sch_convention, end_convention, payment_convention, 
                self.reset_convention, fixing_convention, end_of_month)
        
        notionals = np.array([self.notional] * len(start_dates))
        init_notional_ex_paydate = effective_date
        final_notional_ex_paydate = payment_calendar.advance(
            end_dates[-1], ql.Period(final_notional_ex_payment_delay, ql.Days), payment_convention)

        FloatLeg.__init__(
            self, ccy, index_name, start_dates, end_dates, reset_dates_array, 
            fixing_dates_array, payment_dates, notionals, multiplier, spread, 
            daycount, trade_direction, is_ois_leg,  compounding_type,
            is_init_notional_ex, notional, init_notional_ex_paydate, 
            is_final_notional_ex, notional, final_notional_ex_paydate)

        
    @staticmethod
    def get_standard_float_schedule(
        start, end, pay_freq, reset_freq, payment_delay, fixing_days, 
        sch_calendar, fixing_calendar, payment_calendar, 
        date_generation_rule=ql.DateGeneration.Forward, 
        sch_convention=ql.ModifiedFollowing, end_convention=ql.ModifiedFollowing, 
        payment_convention=ql.ModifiedFollowing, reset_convention=ql.ModifiedFollowing, 
        fixing_convention=ql.Preceding, end_of_month=False):
        
        start_dates, end_dates, payment_dates \
            = StandardFixedLeg.get_standard_schedule(
                start, end, pay_freq, payment_delay, sch_calendar, payment_calendar, 
                date_generation_rule, sch_convention, end_convention, 
                payment_convention, end_of_month)
        
        reset_dates_list = []
        fixing_dates_list = []
        
        for start_date, end_date in zip(start_dates, end_dates):
            if reset_freq == 'None' or reset_freq == None:
                reset_dates = np.array([start_date])
            else:
                reset_dates = np.array(
                    ql.Schedule(start_date, end_date, ql.Period(reset_freq), 
                                sch_calendar, reset_convention, reset_convention, 
                                ql.DateGeneration.Forward, False))[:-1]
            reset_dates_list.append(reset_dates)
                
        for reset_dates in reset_dates_list:
            fixing_dates = np.array(
                [fixing_calendar.advance(
                    reset_date, ql.Period(-fixing_days, ql.Days), fixing_convention) 
                    for reset_date in reset_dates])
            fixing_dates_list.append(fixing_dates)
        
        reset_dates_array = np.array(reset_dates_list, dtype=object)
        fixing_dates_array = np.array(fixing_dates_list, dtype=object)
        
        return (start_dates, end_dates, payment_dates, 
                reset_dates_array, fixing_dates_array)
    


class FixedAmountLeg:
    def __init__(self, 
                 ccy: str, 
                 cashflow: np.ndarray, 
                 payment_dates: np.ndarray, 
                 trade_direction: str):
        self.ccy = ccy
        self.cashflow = cashflow
        self.payment_dates = payment_dates
        self.trade_direction = trade_direction.lower()


    def npv(self, today, discount_curve):
        disc_curve = discount_curve.curve
        
        if today >= max(self.payment_dates):
            npv = 0.0
        
        else:
            #计算折现因子
            dfs = [disc_curve.discount(payment_date) / disc_curve.discount(today) 
                   for payment_date in self.payment_dates if payment_date > today]
            npv = np.dot(self.cashflow[self.payment_dates > today], dfs)
            npv *= 1 if self.trade_direction == 'receive' else -1

        return npv
        
    
    