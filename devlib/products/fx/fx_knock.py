# -*- coding: utf-8 -*-
"""
Created on Tue Jun  4 16:38:40 2024

@author: Guanzhifan
"""


import QuantLib as ql

from ...products.fx.fx_base_option import FxBaseOption
from ...products.fx.fx_vanilla import FxVanilla
from ...products.fx.fx_digital import FxBinary


class FxKnock(FxBaseOption):
    def __init__(self, d_ccy, f_ccy, calendar, expiry, payment_date, 
                 barrier_type, barrier, barrier_at_coupon, flavor, strike,
                 notional, notional_ccy, trade_direction, 
                 coupon=0, coupon_cash_settle=True): # option、coupon执行收益币种为本币
        
        if expiry > payment_date:
            raise Exception('Error: obs date should not be later than payment date!')
            
        super().__init__(d_ccy, f_ccy, calendar)
        self.expiry = expiry
        self.payment_date = payment_date
        self.barrier_type = barrier_type.lower()
        self.barrier = barrier
        self.barrier_at_coupon = barrier_at_coupon
        self.flavor = flavor.lower()
        self.strike = strike
        self.notional = notional
        self.notional_ccy = notional_ccy
        self.trade_direction = trade_direction.lower()
        self.coupon = coupon
        self.coupon_cash_settle = coupon_cash_settle

        if notional_ccy == d_ccy:
            notional = notional / strike
            notional_ccy = f_ccy
        elif notional_ccy != f_ccy:
            raise Exception('Notional_ccy type error!')
            
        
        if self.barrier_type in ['upout','downin']:
            barrier_type_equal = 'upout'
            if self.coupon!=0:
                self.digital_coupon = FxBinary(d_ccy, f_ccy, calendar, expiry, payment_date, 'call', 
                                               barrier, barrier_at_coupon, coupon, d_ccy,
                                               self.trade_direction, coupon_cash_settle)
        elif self.barrier_type in ['upin','downout']:
            barrier_type_equal = 'upin'
            if self.coupon!=0:
                self.digital_coupon = FxBinary(d_ccy, f_ccy, calendar, expiry, payment_date, 'put', 
                                               barrier, barrier_at_coupon, coupon, d_ccy,
                                               self.trade_direction, coupon_cash_settle)
        else:
            raise Exception('Barrier type error!')
        
        if self.flavor == 'call':
            diff = self.barrier - self.strike
            if diff < 0:
                raise Exception('Barrier should be larger than strike!')
        elif self.flavor == 'put':
            diff = self.strike - self.barrier
            if diff < 0:
                raise Exception('Strike should be larger than barrier!')
        else:
            raise Exception('Vanilla option type error!')
        
        if ((barrier_type_equal, self.flavor) == ('upout', 'call')) | ((barrier_type_equal, self.flavor) == ('upin', 'put')):
            self.option_type = 1
            self.digital_diff = FxBinary(d_ccy, f_ccy, calendar, expiry, payment_date, self.flavor, 
                                         barrier, barrier_at_coupon, diff*notional,
                                         d_ccy, self.trade_direction)
            self.vanilla_barrier = FxVanilla(d_ccy, f_ccy, calendar, expiry, payment_date, self.flavor, 
                                             barrier, notional, notional_ccy, self.trade_direction,
                                             get_fwd_method='spot')
            self.vanilla_strike = FxVanilla(d_ccy, f_ccy, calendar, expiry, payment_date, self.flavor, 
                                            strike, notional, notional_ccy, self.trade_direction,
                                            get_fwd_method='spot')

        else:
            self.option_type = 0
            self.digital_diff = FxBinary(d_ccy, f_ccy, calendar, expiry, payment_date, self.flavor, 
                                         barrier, not barrier_at_coupon, diff*notional,
                                         d_ccy, self.trade_direction)
            self.vanilla_barrier = FxVanilla(d_ccy, f_ccy, calendar, expiry, payment_date, self.flavor, 
                                             barrier, notional, notional_ccy, self.trade_direction,
                                             get_fwd_method='spot')
        

        

    def npv(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount=ql.Actual365Fixed()):
        if self.option_type == 1:
            npv = self.vanilla_strike.npv(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount) \
                - self.vanilla_barrier.npv(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount) \
                - self.digital_diff.npv(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount) \
                
        else:
            npv = self.vanilla_barrier.npv(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount) \
                + self.digital_diff.npv(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount) \
        
        if self.coupon!=0:
            npv += self.digital_coupon.npv(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount) 
        
        return npv
    

