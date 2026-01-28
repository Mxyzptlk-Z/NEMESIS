import numpy as np
import pandas as pd
import QuantLib as ql

from ...products.fx.fx_base_option import FxBaseOption
from ...models.bsm.black76 import cash_or_nothing_76, asset_or_nothing_76

from ...utils.utils import average_sigma
from ...utils.fx_utils import get_pair_tweak_param



class FxBinary(FxBaseOption):
    def __init__(self, d_ccy, f_ccy, calendar, expiry, payment_date, flavor, 
                 strike, pay_equal, cash, cash_ccy, trade_direction, cash_settle=True):  
        if expiry > payment_date:
            raise Exception('Error: obs date should not be later than payment date!')
        if not cash_ccy in [d_ccy, f_ccy]:
            raise Exception('Error: cash ccy should be d_ccy or f_ccy!')
        
        super().__init__(d_ccy, f_ccy, calendar)
        self.expiry = expiry
        self.payment_date = payment_date
        self.flavor = flavor.lower()
        self.strike = strike
        self.pay_equal = pay_equal
        self.cash = cash
        self.cash_ccy = cash_ccy
        self.trade_direction = trade_direction.lower()
        # 当前默认是cash settle模式，与bbg保持一致
        self.cash_settle = cash_settle
        

    def npv(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount=ql.Actual365Fixed()):
        if today > self.expiry:
            # 到期日后的估值默认为0
            return 0.0
        
        spot_f_d = fwd_crv_f_d.spot
        dis_crv = discount_crv.curve
        df = dis_crv.discount(self.payment_date) / dis_crv.discount(today)
        if today == self.expiry:
            # 到期日当天估值输出final payment
            if self.flavor == 'call':
                if spot_f_d > self.strike:
                    npv = self.cash * df
                elif spot_f_d == self.strike and self.pay_equal:
                    npv = self.cash * df
                else:
                    npv = 0.0
            else:
                if spot_f_d < self.strike:
                    npv = self.cash * df
                elif spot_f_d == self.strike and self.pay_equal:
                    npv = self.cash * df
                else:
                    npv = 0.0
            if self.cash_ccy == self.f_ccy:
                if self.cash_settle:
                    atm_pay = fwd_crv_f_d.get_forward_spot(self.expiry)
                else:
                    atm_pay = fwd_crv_f_d.get_forward(self.payment_date)
                npv = npv * atm_pay
            npv *= 1 if self.trade_direction == 'long' else -1
            
            return npv
        
        sigma_f_d = vol_surf_f_d.interp_vol(self.expiry, self.strike)
        atm = fwd_crv_f_d.get_forward_spot(self.expiry)
        dcf = daycount.yearFraction(today, self.expiry)

        if self.cash_ccy == self.f_ccy:
            if self.cash_settle:
                atm_pay = fwd_crv_f_d.get_forward_spot(self.expiry)
            else:
                atm_pay = fwd_crv_f_d.get_forward(self.payment_date)
            npv = self.cash * asset_or_nothing_76(self.flavor, atm, self.strike, dcf, sigma_f_d, atm_pay, df)
        else:
            npv = cash_or_nothing_76(self.flavor, atm, self.strike, self.cash, dcf, sigma_f_d, df)

        return npv if self.trade_direction == 'long' else -npv
    


class FxDigital(FxBaseOption):
    def __init__(self, d_ccy, f_ccy, calendar, expiry, payment_date, strike, left_in, coupon_left, 
                 coupon_right, cash_ccy, trade_direction, cash_settle=True): 
        if expiry > payment_date:
            raise Exception('Error: obs date should not be later than payment date!')
        if not cash_ccy in [d_ccy, f_ccy]:
            raise Exception('Error: cash ccy should be d_ccy or f_ccy!')
         
        super().__init__(d_ccy, f_ccy, calendar)
        self.expiry = expiry
        self.payment_date = payment_date
        self.strike = strike
        self.left_in = left_in
        self.coupon_left = coupon_left
        self.coupon_right = coupon_right
        self.cash_ccy = cash_ccy
        self.trade_direction = trade_direction.lower()
        # 当前默认是cash settle模式，与bbg保持一致
        self.cash_settle = cash_settle

        self.binary_left = FxBinary(d_ccy, f_ccy, calendar, expiry, payment_date, 'put', strike, 
                                    left_in, coupon_left, cash_ccy, trade_direction, cash_settle)
        self.binary_right = FxBinary(d_ccy, f_ccy, calendar, expiry, payment_date, 'call', strike, 
                                     (not left_in), coupon_right, cash_ccy, trade_direction, cash_settle)
        
    
    def npv(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount=ql.Actual365Fixed()):
        npv = (self.binary_left.npv(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount) + 
               self.binary_right.npv(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount))

        return npv
    
