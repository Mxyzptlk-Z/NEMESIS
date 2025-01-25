# -*- coding: utf-8 -*-
"""
Created on Mon Jan 30 11:33:35 2023

@author: xieyushan
"""

import QuantLib as ql



class FlatRateCurve:
    def __init__(self, discount_rate, ccy, calendar=ql.NullCalendar(), daycount=ql.Actual365Fixed()):
        # default today is ql.Settings.instance().evaluationDate(with calendar adjust)
        self.name = 'FlatRateCurve'
        self.ccy = ccy.upper()
        self.discount_rate = discount_rate
        self.calendar = calendar
        self.daycount = daycount
        self.curve = ql.FlatForward(0, calendar, discount_rate, daycount)
        self.curve_date = self.curve.referenceDate()
        self.Fixing = None
        
    
    def tweak_parallel(self, tweak):
        discount_rate_tweak = self.discount_rate + tweak
        
        return FlatRateCurve(discount_rate_tweak, self.ccy, self.calendar, self.daycount)
    

    def tweak_discount_curve(self, tweak, tweak_daycount=None, tweak_type=None):
        # flat rate curve only support discount rate tweak
        return self.tweak_parallel(tweak)
