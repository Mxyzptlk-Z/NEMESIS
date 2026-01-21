import math
import numpy as np
import pandas as pd
import QuantLib as ql
from scipy.stats import norm

from .fx_base_option import FxBaseOption
from ...models.bsm.black76 import vanilla_76

from ...utils.fx_utils import get_pair_tweak_param



class FxVanilla(FxBaseOption):
    def __init__(self, d_ccy, f_ccy, calendar, expiry, payment_date, 
                 flavor, strike, notional, notional_ccy, trade_direction,
                 get_fwd_method='forward'):  
        if expiry > payment_date:
            raise Exception('Error: obs date should not be later than payment date!')
        
        super().__init__(d_ccy, f_ccy, calendar)
        self.expiry = expiry
        self.payment_date = payment_date
        self.flavor = flavor.lower()
        self.strike = strike
        self.notional = notional
        self.notional_ccy = notional_ccy
        self.trade_direction = trade_direction.lower()
        self.get_fwd_method = get_fwd_method.lower()

        if notional_ccy == d_ccy:
            self.qty = notional / strike
        elif notional_ccy == f_ccy:
            self.qty = notional
        else:
            raise Exception(f'Unsupported notional ccy: {notional_ccy} for pair {f_ccy}{d_ccy}!')
            
        if not self.get_fwd_method in {'spot', 'forward'}:
            raise Exception(f'Unsupported get forward method: {get_fwd_method}!')
        

    def npv(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount=ql.Actual365Fixed()):
        if today > self.expiry:
            # 到期日后的估值默认为0
            return 0.0
        
        disc_crv = discount_crv.curve
        df = disc_crv.discount(self.payment_date) / disc_crv.discount(today)
        if self.get_fwd_method == 'forward':
            atm = fwd_crv_f_d.get_forward(self.payment_date)
        else:
            atm = fwd_crv_f_d.get_forward_spot(self.expiry)

        if today == self.expiry:
            if self.flavor == 'call':
                npv = self.qty * max(atm - self.strike, 0) * df
            elif self.flavor == 'put':
                npv = self.qty * max(self.strike - atm, 0) * df
            else:
                Exception('Vanilla option type error!')
            npv *= 1 if self.trade_direction == 'long' else -1
            
            return npv
        
        sigma_f_d = vol_surf_f_d.interp_vol(self.expiry, self.strike)
        dcf = daycount.yearFraction(today, self.expiry)
        npv = vanilla_76(self.flavor, atm, self.strike, dcf, sigma_f_d, df) * self.qty

        return npv if self.trade_direction == 'long' else -npv
    

    def _set_target_date(self):
        # vanilla option as physical settle
        return self.payment_date
    


class FxRiskReversal(FxBaseOption):
    def __init__(self, d_ccy, f_ccy, calendar, expiry, payment_date, flavor, strike_left, 
                 strike_right, notional, notional_ccy, trade_direction):  
        if expiry > payment_date:
            raise Exception('Error: obs date should not be later than payment date!')
        
        super().__init__(d_ccy, f_ccy, calendar)
        self.expiry = expiry
        self.payment_date = payment_date
        self.flavor = flavor.lower()
        self.strike_left = strike_left
        self.strike_right = strike_right
        self.notional = notional
        self.notional_ccy = notional_ccy
        self.trade_direction = trade_direction.lower()
        
        self.call = FxVanilla(d_ccy, f_ccy, calendar, expiry, payment_date, 'call', 
                              strike_right, notional, notional_ccy, trade_direction)
        self.put = FxVanilla(d_ccy, f_ccy, calendar, expiry, payment_date, 'put', 
                             strike_left, notional, notional_ccy, trade_direction)
        

    def npv(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount=ql.Actual365Fixed()):
        if self.flavor == 'call':
            npv = (self.call.npv(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount) - 
                   self.put.npv(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount))
        elif self.flavor == 'put':
            npv = (self.put.npv(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount) - 
                   self.call.npv(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount))
        else:
            Exception('Vanilla option type error!')
        
        return npv
    

    # Report pricing parameters at initial
    def pricing_param(self, today, fwd_crv_f_d, discount_crv, 
                      vol_surf_f_d, daycount=ql.Actual365Fixed()):
        if today > self.expiry:
            raise Exception('Today is later than expiry!')
        
        sigma_f_d_left = vol_surf_f_d.interp_vol(self.expiry, self.strike_left)
        sigma_f_d_right = vol_surf_f_d.interp_vol(self.expiry, self.strike_right)
        sigma_f_d = (sigma_f_d_left + sigma_f_d_right) / 2
        r = discount_crv.curve.zeroRate(self.expiry, daycount, ql.Continuous).rate()
        
        return {'PricingVol': sigma_f_d, 'RiskFreeRate': r}
    

    def _set_target_date(self):
        # vanilla option as physical settle
        return self.payment_date
    

    def _specific_valuation_param(self, today, fwd_crv_f_d, discount_crv, 
                                  vol_surf_f_d, daycount=ql.Actual365Fixed()):
        sigma_f_d_1 = vol_surf_f_d.interp_vol(self.expiry, self.strike_left)
        sigma_f_d_2 = vol_surf_f_d.interp_vol(self.expiry, self.strike_right)

        return {'sigma_f_d_1': sigma_f_d_1,
                'sigma_f_d_2': sigma_f_d_2}

