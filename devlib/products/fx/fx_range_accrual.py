import numpy as np
import pandas as pd
import QuantLib as ql

from ...products.fx.fx_digital import FxBinary
from ...products.fx.fx_base_option import FxBaseOption

from ...utils.utils import average_sigma


class FxRangeDigital(FxBaseOption):
    def __init__(self, d_ccy, f_ccy, calendar, expiry, payment_date, range_down, down_in, 
                 range_up, up_in, range_coupon, cash_ccy, trade_direction, cash_settle=True):  
        if range_down >= range_up:
            raise Exception('Error: range up should be bigger than range down!')
        if expiry > payment_date:
            raise Exception('Error: obs date should not be later than payment date!')
        if not cash_ccy in [d_ccy, f_ccy]:
            raise Exception('Error: cash ccy should be d_ccy or f_ccy!')
        
        super().__init__(d_ccy, f_ccy, calendar)
        self.expiry = expiry
        self.payment_date = payment_date
        self.range_down = range_down
        self.down_in = down_in
        self.range_up = range_up
        self.up_in = up_in
        self.range_coupon = range_coupon
        self.cash_ccy = cash_ccy
        self.trade_direction = trade_direction.lower()
        # 当前默认是cash settle模式，与bbg保持一致
        self.cash_settle = cash_settle

        # digs已考虑交易方向
        if self.range_down == float('-inf'):
            dig_put = FxBinary(d_ccy, f_ccy, calendar, expiry, payment_date, 'put', range_up, up_in, 
                               self.range_coupon, cash_ccy, trade_direction, cash_settle)
            self.digs = [dig_put]
        elif self.range_up == float('inf'):
            dig_call = FxBinary(d_ccy, f_ccy, calendar, expiry, payment_date, 'call', range_down, down_in, 
                                self.range_coupon, cash_ccy, trade_direction, cash_settle)
            self.digs = [dig_call]
        else:
            dig_call_1 = FxBinary(d_ccy, f_ccy, calendar, expiry, payment_date, 'call', range_down, 
                                  down_in, self.range_coupon, cash_ccy, trade_direction, cash_settle)
            trade_direction_2 = 'short' if trade_direction == 'long' else 'long'
            dig_call_2 = FxBinary(d_ccy, f_ccy, calendar, expiry, payment_date, 'call', range_up, 
                                  (not up_in), self.range_coupon, cash_ccy, trade_direction_2, cash_settle)
            self.digs = [dig_call_1, dig_call_2]
        
    
    def npv(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount=ql.Actual365Fixed()):
        npv = 0
        for dig in self.digs:
            npv_dig = dig.npv(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount)
            npv += npv_dig
        
        return npv
    

    # Report pricing parameters at initial
    def pricing_param(self, today, fwd_crv_f_d, discount_crv, 
                      vol_surf_f_d, daycount=ql.Actual365Fixed()):
        if today > self.expiry:
            raise Exception('Today is later than expiry!')
        
        dig_sigmas = []
        for dig in self.digs:
            dig_sigma = vol_surf_f_d.interp_vol(dig.expiry, dig.strike)
            dig_sigmas.append(dig_sigma)
        sigma_f_d = np.mean(np.array(dig_sigmas))

        r = discount_crv.curve.zeroRate(self.expiry, daycount, ql.Continuous).rate()
        
        return {'PricingVol': sigma_f_d, 'RiskFreeRate': r}
    

    def _specific_valuation_param(self, today, fwd_crv_f_d, discount_crv, 
                                  vol_surf_f_d, daycount=ql.Actual365Fixed()):
        if self.range_down == float('-inf'):
            sigma_f_d_1 = None
            sigma_f_d_2 = vol_surf_f_d.interp_vol(self.expiry, self.range_up)
        elif self.range_up == float('inf'):
            sigma_f_d_1 = vol_surf_f_d.interp_vol(self.expiry, self.range_down)
            sigma_f_d_2 = None
        else:
            sigma_f_d_1 = vol_surf_f_d.interp_vol(self.expiry, self.range_down)
            sigma_f_d_2 = vol_surf_f_d.interp_vol(self.expiry, self.range_up)

        return {'sigma_f_d_1': sigma_f_d_1,
                'sigma_f_d_2': sigma_f_d_2}
    


class FxRangeAccrual(FxBaseOption):
    def __init__(self, d_ccy, f_ccy, calendar, obs_schedule, payment_date, range_down, down_in, range_up, up_in, 
                 range_in_coupon, range_out_coupon, cash_ccy, trade_direction, fx_fixing, cash_settle=True):
        if range_down >= range_up:
            raise Exception('Error: range up should be bigger than range down!')
        if obs_schedule[-1] > payment_date:
            raise Exception('Error: obs date should not be later than payment date!')
        if not cash_ccy in [d_ccy, f_ccy]:
            raise Exception('Error: cash ccy should be d_ccy or f_ccy!')
        
        super().__init__(d_ccy, f_ccy, calendar)
        self.obs_schedule = obs_schedule
        self.payment_date = payment_date
        self.range_down = range_down
        self.down_in = down_in
        self.range_up = range_up
        self.up_in = up_in
        self.range_in_coupon = range_in_coupon
        self.range_out_coupon = range_out_coupon
        self.cash_ccy = cash_ccy
        self.trade_direction = trade_direction.lower()
        self.fx_fixing = fx_fixing
        # 当前默认是cash settle模式，与bbg保持一致
        self.cash_settle = cash_settle


    def _check_interval(self, price):
        """
        判断是否在高收益区间内
        """
        if self.range_down < price and price < self.range_up:
            flag = True
        elif self.range_down == price and self.down_in:
            flag = True
        elif self.range_up == price and self.up_in:
            flag = True
        else:
            # 其余都在低收益区域内
            flag = False
        
        return flag


    def npv(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount=ql.Actual365Fixed()):
        if today > self.obs_schedule[-1]:
            # 到期日后的估值默认为0
            return 0.0
        
        if today >= self.obs_schedule[0] and len(self.fx_fixing) == 0:
            fx_fixing = pd.Series(data=[fwd_crv_f_d.spot], index=[today])
        else:
            fx_fixing = self.fx_fixing
        
        range_dig_count = len(self.obs_schedule)
        dis_crv = discount_crv.curve
    
        if self.cash_settle:
            # 默认按最后一个观察日计算spot
            atm_pay_date = self.obs_schedule[-1]
        else:
            atm_pay_date = self.payment_date
        atm_pay = fwd_crv_f_d.get_forward(atm_pay_date)

        in_count = 0
        out_count = 0
        for obs_date in self.obs_schedule:
            if obs_date <= today:
                try:
                    price_observed = fx_fixing[fx_fixing.index <= obs_date].values[-1]
                except:
                    raise Exception(f'Missing fx fixing data for {str(obs_date)}!')
                if self._check_interval(price_observed):
                    in_count += 1
                else:
                    out_count += 1
            else:
                unit_range_dig = FxRangeDigital(
                    self.d_ccy, self.f_ccy, self.calendar, obs_date, atm_pay_date, 
                    self.range_down, self.down_in, self.range_up, self.up_in, 1, 
                    self.cash_ccy, 'long', cash_settle=False)
                unit_pv = unit_range_dig.npv(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount)
                unit_df = dis_crv.discount(atm_pay_date) / dis_crv.discount(today)
                if self.cash_ccy == self.f_ccy:
                    # asset or nothing
                    unit_prob = unit_pv / unit_df / atm_pay 
                else:
                    unit_prob = unit_pv / unit_df
                in_count += unit_prob
                out_count += (1 - unit_prob)
        
        df = dis_crv.discount(self.payment_date) / dis_crv.discount(today)
        npv = (self.range_in_coupon * in_count + self.range_out_coupon * out_count) / range_dig_count * df
        if self.cash_ccy == self.f_ccy:
            npv = npv * atm_pay
        
        return npv if self.trade_direction == 'long' else -npv
    

    # Report pricing parameters at initial
    def pricing_param(self, today, fwd_crv_f_d, discount_crv, 
                      vol_surf_f_d, daycount=ql.Actual365Fixed()):
        if today > self.obs_schedule[-1]:
            raise Exception('Today is later than expiry!')
        
        dig_strikes = []
        if not self.range_down == float('-inf'):
            dig_strikes.append(self.range_down)
        if not self.range_up == float('inf'):
            dig_strikes.append(self.range_up)

        dig_sigmas = []
        obs_dates = self.obs_schedule[self.obs_schedule > today]
        if len(obs_dates) == 0:
            sigma_f_d = None
        else:
            for strike in dig_strikes:
                dig_sigma = average_sigma(obs_dates, strike, vol_surf_f_d)
                dig_sigmas.append(dig_sigma)
            sigma_f_d = np.mean(np.array(dig_sigmas))

        r = discount_crv.curve.zeroRate(self.obs_schedule[-1], daycount, ql.Continuous).rate()
                
        return {'PricingVol': sigma_f_d, 'RiskFreeRate': r}
    

    def _set_target_date(self):

        return max(self.obs_schedule)
    

    def _specific_valuation_param(self, today, fwd_crv_f_d, discount_crv, 
                                  vol_surf_f_d, daycount=ql.Actual365Fixed()):
        obs_dates = self.obs_schedule[self.obs_schedule > today]
            
        if self.range_down == float('-inf'):
            sigma_f_d_1 = None
            sigma_f_d_2 = average_sigma(obs_dates, self.range_up, vol_surf_f_d)
        elif self.range_up == float('inf'):
            sigma_f_d_1 = average_sigma(obs_dates, self.range_down, vol_surf_f_d)
            sigma_f_d_2 = None
        else:
            sigma_f_d_1 = average_sigma(obs_dates, self.range_down, vol_surf_f_d)
            sigma_f_d_2 = average_sigma(obs_dates, self.range_up, vol_surf_f_d)

        # calc in and out count for RM
        if today >= self.obs_schedule[0] and len(self.fx_fixing) == 0:
            fx_fixing = pd.Series(data=[fwd_crv_f_d.spot], index=[today])
        else:
            fx_fixing = self.fx_fixing

        in_count = 0
        out_count = 0
        for obs_date in self.obs_schedule:
            if obs_date <= today:
                try:
                    price_observed = fx_fixing[fx_fixing.index <= obs_date].values[-1]
                except:
                    raise Exception(f'Missing fx fixing data for {str(obs_date)}!')
                if self._check_interval(price_observed):
                    in_count += 1
                else:
                    out_count += 1

        return {'sigma_f_d_1': sigma_f_d_1,
                'sigma_f_d_2': sigma_f_d_2, 
                'in_count': in_count, 
                'out_count': out_count}

