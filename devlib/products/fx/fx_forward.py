import numpy as np
import QuantLib as ql

from utils.fx_utils import get_pair_tweak_param



class FxForward:
    def __init__(
            self, 
            d_ccy: str, 
            f_ccy: str, 
            calendar: ql.Calendar, 
            settle_date: ql.Date, 
            notional_dccy: float, 
            notional_fccy: float, 
            flavor_fccy: str, 
            settle_type: str = 'physical', 
            settle_ccy: str = None, 
            pricing_date: ql.Date = None, 
            pricing_fx_rate: float = None, 
    ):
        self.d_ccy = d_ccy
        self.f_ccy = f_ccy
        self.calendar = calendar 
        self.settle_date = settle_date
        self.notional_dccy = notional_dccy 
        self.notional_fccy = notional_fccy
        self.flavor_fccy = flavor_fccy
        self.settle_type = settle_type
        self.settle_ccy = settle_ccy
        self.pricing_date = pricing_date
        self.pricing_fx_rate = pricing_fx_rate

        if not self.flavor_fccy in ['buy', 'sell']:
            raise Exception(f'Unsupported flavor: {self.flavor_fccy}!')
        
        if not self.settle_type in ['physical', 'cash']:
            raise Exception(f'Unsupported flavor: {self.settle_type}!')
        
        if self.settle_type == 'cash' and (not self.settle_ccy in [d_ccy, f_ccy]):
            raise Exception(f'Unsupported settle ccy: {self.settle_ccy} for {self.f_ccy + self.d_ccy}!')


    def npv(self, today, fwd_crv_f_d, discount_crv, including_settle=True):
        if (not including_settle) and today >= self.settle_date:
            return 0.0
        elif self.settle_type == 'physical' or (self.settle_type == 'cash' and today < self.pricing_date):
            real_settle_date = max(fwd_crv_f_d.today, self.settle_date)
            fwd = fwd_crv_f_d.get_forward(real_settle_date)
            disc_crv = discount_crv.curve
            df = disc_crv.discount(real_settle_date) / disc_crv.discount(today)
            npv = df * (self.notional_fccy * fwd - self.notional_dccy)
        else:
            # settle_type = 'cash' and today >= pricing date
            pricing_fx_rate = self.__get_pricing_fx_rate(fwd_crv_f_d)
            if today >= self.settle_date:
                df = 1.0
            else:
                disc_crv = discount_crv.curve
                df = disc_crv.discount(self.settle_date) / disc_crv.discount(today)
            if self.settle_ccy == self.d_ccy:
                payment = self.notional_fccy * pricing_fx_rate - self.notional_dccy
            else:
                payment_fccy = self.notional_fccy - self.notional_dccy / pricing_fx_rate
                if today >= self.settle_date:
                    payment = payment_fccy * fwd_crv_f_d.spot
                else:
                    fx_rate = fwd_crv_f_d.get_forward(self.settle_date)
                    payment = payment_fccy * fx_rate
            npv = payment * df
        
        npv *= 1 if self.flavor_fccy == 'buy' else -1
        
        return npv
    

    def __get_pricing_fx_rate(self, fwd_crv_f_d):
        if self.pricing_fx_rate == None:
            return fwd_crv_f_d.get_forward(self.settle_date)
        else:
            return self.pricing_fx_rate
            
    
    def delta(self, today, fwd_crv_f_d, discount_crv, tweak=1, including_settle=True):
        tweak_param = get_pair_tweak_param(self.f_ccy + self.d_ccy)
        fwd_crv_f_d_up = fwd_crv_f_d.tweak_spot(tweak / tweak_param)
        fwd_crv_f_d_down = fwd_crv_f_d.tweak_spot(-tweak / tweak_param)
        npv_up = self.npv(today, fwd_crv_f_d_up, discount_crv, including_settle=including_settle)   
        npv_down = self.npv(today, fwd_crv_f_d_down, discount_crv, including_settle=including_settle)
        delta = (npv_up - npv_down) / (2 * tweak / tweak_param)
        
        return delta
    

    # for trader use
    def delta_ccy2(self, today, fwd_crv_f_d, discount_crv, tweak=1, including_settle=True):
        delta = self.delta(today, fwd_crv_f_d, discount_crv, tweak=1, including_settle=including_settle)

        return -delta * self.notional_dccy / self.notional_fccy
        

    def bbg_delta(self, today, fwd_crv_f_d, discount_crv, tweak=1, delta_type='spot'):
        tweak_param = get_pair_tweak_param(self.f_ccy + self.d_ccy)
        spot_date = fwd_crv_f_d.spot_date
        spot = FxForward(self.d_ccy, self.f_ccy, self.calendar, spot_date, 
                         fwd_crv_f_d.spot * self.notional_fccy, self.notional_fccy, 'buy')
        forward = FxForward(self.d_ccy, self.f_ccy, self.calendar, self.settle_date, 
                            fwd_crv_f_d.spot * self.notional_fccy, self.notional_fccy, 'buy')
        
        fwd_crv_f_d_up = fwd_crv_f_d.tweak_spot(tweak / tweak_param)
        fwd_crv_f_d_down = fwd_crv_f_d.tweak_spot(-tweak / tweak_param)
        npv_up = self.npv(today, fwd_crv_f_d_up, discount_crv)   
        npv_down = self.npv(today, fwd_crv_f_d_down, discount_crv)
        if delta_type == 'spot':
            spot_npv_up = spot.npv(today, fwd_crv_f_d_up, discount_crv)
            spot_npv_down = spot.npv(today, fwd_crv_f_d_down, discount_crv)
            delta = (npv_up - npv_down) / (spot_npv_up - spot_npv_down)
        elif delta_type == 'forward':
            forward_npv_up = forward.npv(today, fwd_crv_f_d_up, discount_crv)
            forward_npv_down = forward.npv(today, fwd_crv_f_d_down, discount_crv)
            delta = (npv_up - npv_down) / (forward_npv_up - forward_npv_down)
        else:
            raise Exception(f'Delta type error {delta_type}!')
        
        return delta * self.notional_fccy
        

    def gamma(self, today, fwd_crv_f_d, discount_crv):
        return 0.0
    

    # Theta wrt 1 day change 
    def theta(self, today, fwd_crv_f_d, discount_crv, tweak=1, including_settle=True):
        npv = self.npv(today, fwd_crv_f_d, discount_crv, including_settle=including_settle)    
        tmr = self.calendar.advance(today, ql.Period(str(tweak) + 'D'))
        if tmr == self.settle_date:
            including_settle = True
        npv_tmr = self.npv(tmr, fwd_crv_f_d, discount_crv, including_settle=including_settle) 
        
        return (npv_tmr - npv) / tweak


    # Rho(DV01) wrt 0.01% change in Domestic Currency interest rate (discount curve)
    def rho(self, today, fwd_crv_f_d, discount_crv, tweak=1, tweak_type='pillar_rate'):
        if today >= self.settle_date:
            return 0.0
        
        if tweak_type == 'pillar_rate':
            discount_crv_up = discount_crv.tweak_discount_curve(tweak/10000)
            discount_crv_down = discount_crv.tweak_discount_curve(-tweak/10000)
            fwd_crv_f_d_up = fwd_crv_f_d.tweak_parallel(tweak / 10000)
            fwd_crv_f_d_down = fwd_crv_f_d.tweak_parallel(-tweak / 10000)
        elif tweak_type == 'market':
            discount_crv_up = discount_crv.tweak_parallel(tweak/10000)
            discount_crv_down = discount_crv.tweak_parallel(-tweak/10000)
            fwd_crv_f_d_up = fwd_crv_f_d.tweak_dccy_curve(discount_crv, discount_crv_up)
            fwd_crv_f_d_down = fwd_crv_f_d.tweak_dccy_curve(discount_crv, discount_crv_down)
        else:
            raise Exception(f'Unsupported tweak type: {tweak_type}!')
        
        npv_up = self.npv(today, fwd_crv_f_d_up, discount_crv_up) 
        npv_down = self.npv(today, fwd_crv_f_d_down, discount_crv_down) 

        return (npv_up - npv_down) / (2 * tweak)


    # Phi(DV01) wrt 0.01% change in Foreign Currency interest rate
    def phi(self, today, fwd_crv_f_d, discount_crv, tweak=1, tweak_type='pillar_rate'):
        if today >= self.settle_date:
            return 0.0
        
        if tweak_type == 'pillar_rate':
            fwd_crv_f_d_up = fwd_crv_f_d.tweak_parallel(tweak / 10000)
            fwd_crv_f_d_down = fwd_crv_f_d.tweak_parallel(-tweak / 10000)
        elif tweak_type == 'market':
            discount_crv_up = discount_crv.tweak_parallel(tweak/10000)
            discount_crv_down = discount_crv.tweak_parallel(-tweak/10000)
            fwd_crv_f_d_up = fwd_crv_f_d.tweak_dccy_curve(discount_crv, discount_crv_up)
            fwd_crv_f_d_down = fwd_crv_f_d.tweak_dccy_curve(discount_crv, discount_crv_down)
        else:
            raise Exception(f'Unsupported tweak type: {tweak_type}!')
            
        npv_up = self.npv(today, fwd_crv_f_d_down, discount_crv) 
        npv_down = self.npv(today, fwd_crv_f_d_up, discount_crv)

        return (npv_up - npv_down) / (2 * tweak)
    

    def phi_ccy1(self, today, fwd_crv_f_d, discount_crv, tweak=1):
        phi = self.phi(today, fwd_crv_f_d, discount_crv, tweak=tweak)

        return phi / fwd_crv_f_d.spot_today
    

    # for trader use (forward delta)
    def dccy_cashflow(self, today, fwd_crv_f_d):
        flag_dccy = -1 if self.flavor_fccy == 'buy' else 1
        if self.settle_type == 'physical' or (
            self.settle_type == 'cash' and today < self.pricing_date):
            cashflow = self.notional_dccy * flag_dccy
        else:
            # cash settle and today >= pricing date
            if self.settle_ccy == self.d_ccy:
                pricing_fx_rate = self.__get_pricing_fx_rate(fwd_crv_f_d)
                cashflow = (self.notional_dccy - self.notional_fccy * pricing_fx_rate) * flag_dccy
            else:
                cashflow = 0.0
        
        return cashflow
    

    # for trader use (forward delta)
    def fccy_cashflow(self, today, fwd_crv_f_d):
        flag_fccy = 1 if self.flavor_fccy == 'buy' else -1
        if self.settle_type == 'physical' or (
            self.settle_type == 'cash' and today < self.pricing_date):
            cashflow = self.notional_fccy * flag_fccy
        else:
            # cash settle and today >= pricing date
            if self.settle_ccy == self.f_ccy:
                pricing_fx_rate = self.__get_pricing_fx_rate(fwd_crv_f_d)
                cashflow = (self.notional_fccy - self.notional_dccy / pricing_fx_rate) * flag_fccy
            else:
                cashflow = 0.0
        
        return cashflow
    

    def npv_dccy_cashflow(self, today, fwd_crv_f_d, discount_crv):
        cashflow = self.dccy_cashflow(today, fwd_crv_f_d)
        real_settle_date = max(today, self.settle_date)
        disc_crv = discount_crv.curve
        df = disc_crv.discount(real_settle_date) / disc_crv.discount(today) 

        return df * cashflow
            

    def npv_fccy_cashflow(self, today, fwd_crv_f_d, discount_crv):
        cashflow = self.fccy_cashflow(today, fwd_crv_f_d)
        real_settle_date = max(today, self.settle_date)
        disc_crv = discount_crv.curve
        df_dccy = disc_crv.discount(real_settle_date) / disc_crv.discount(today)
        fwd_crv = fwd_crv_f_d.curve
        df_fwd = fwd_crv.discount(real_settle_date) / fwd_crv.discount(today)
        df = df_dccy / df_fwd

        return df * cashflow


    # for trader use
    def dv01s(self, today, fwd_crv_f_d, discount_crv, tweak=1):
        discount_crv_up = discount_crv.tweak_discount_curve(tweak / 10000)
        discount_crv_down = discount_crv.tweak_discount_curve(-tweak / 10000)
        npv_d_up = self.npv_dccy_cashflow(today, fwd_crv_f_d, discount_crv_up) 
        npv_d_down = self.npv_dccy_cashflow(today, fwd_crv_f_d, discount_crv_down) 
        dv01_dccy = (npv_d_up - npv_d_down) / (2 * tweak)

        fwd_crv_f_d_up = fwd_crv_f_d.tweak_parallel(-tweak / 10000)
        fwd_crv_f_d_down = fwd_crv_f_d.tweak_parallel(tweak / 10000)
        npv_f_up = self.npv_fccy_cashflow(today, fwd_crv_f_d_up, discount_crv) 
        npv_f_down = self.npv_fccy_cashflow(today, fwd_crv_f_d_down, discount_crv) 
        dv01_fccy = (npv_f_up - npv_f_down) / (2 * tweak)

        return {'DV01_dccy': dv01_dccy, 
                'DV01_fccy': dv01_fccy}


    def valuation_param(self, today, fwd_crv_f_d, discount_crv, daycount=ql.Actual365Fixed()):
        target_date = max(today, self.settle_date)
        r_d = discount_crv.curve.zeroRate(target_date, daycount, ql.Continuous).rate()
        r_f_d = fwd_crv_f_d.curve.zeroRate(target_date, daycount, ql.Continuous).rate()
        r_f = r_d - r_f_d
        spot_f_d = fwd_crv_f_d.spot
        forward_f_d = fwd_crv_f_d.get_forward(target_date)
        tweak_param = get_pair_tweak_param(self.f_ccy + self.d_ccy)
        if today >= self.settle_date:
            forward_point_f_d = 0.0
        elif self.settle_date < fwd_crv_f_d.spot_date:
            forward_point_f_d = (spot_f_d - forward_f_d) * tweak_param
        else:
            forward_point_f_d = (forward_f_d - spot_f_d) * tweak_param

        return {'spot_f_d': spot_f_d,
                'forward_point_f_d': forward_point_f_d,
                'r_f': r_f, 
                'r_d': r_d}
    


class FxSwap(FxForward):
    def __init__(
            self, 
            d_ccy: str, 
            f_ccy: str, 
            calendar: ql.Calendar, 
            settle_date_1: ql.Date, 
            settle_date_2: ql.Date, 
            notional_dccy_1: float, 
            notional_fccy_1: float, 
            notional_dccy_2: float, 
            notional_fccy_2: float, 
            flavor_fccy_1: str, 
            flavor_fccy_2: str, 
            settle_type: str = 'physical', 
            settle_ccy: str = None, 
            pricing_date_1: ql.Date = None, 
            pricing_date_2: ql.Date = None, 
            pricing_fx_rate_1: float = None, 
            pricing_fx_rate_2: float = None, 
    ):
        self.d_ccy = d_ccy
        self.f_ccy = f_ccy
        self.calendar = calendar
        self.settle_date_1 = settle_date_1
        self.settle_date_2 = settle_date_2
        self.notional_dccy_1 = notional_dccy_1
        self.notional_fccy_1 = notional_fccy_1
        self.notional_dccy_2 = notional_dccy_2
        self.notional_fccy_2 = notional_fccy_2
        self.flavor_fccy_1 = flavor_fccy_1
        self.flavor_fccy_2 = flavor_fccy_2
        self.settle_type = settle_type
        self.settle_ccy = settle_ccy
        self.pricing_date_1 = pricing_date_1
        self.pricing_date_2 = pricing_date_2
        self.pricing_fx_rate_1 = pricing_fx_rate_1
        self.pricing_fx_rate_2 = pricing_fx_rate_2

        if not self.flavor_fccy_1 in ['buy', 'sell']:
            raise Exception(f'Unsupported flavor 1: {self.flavor_fccy_1}!')
        if not self.flavor_fccy_2 in ['buy', 'sell']:
            raise Exception(f'Unsupported flavor 2: {self.flavor_fccy_2}!')

        self.forward_1 = FxForward(
            self.d_ccy, self.f_ccy, self.calendar, self.settle_date_1, notional_dccy_1, 
            notional_fccy_1, flavor_fccy_1, settle_type=settle_type, settle_ccy=settle_ccy, 
            pricing_date=pricing_date_1, pricing_fx_rate=pricing_fx_rate_1)
        self.forward_2 = FxForward(
            self.d_ccy, self.f_ccy, self.calendar, self.settle_date_2, notional_dccy_2, 
            notional_fccy_2, flavor_fccy_2, settle_type=settle_type, settle_ccy=settle_ccy, 
            pricing_date=pricing_date_2, pricing_fx_rate=pricing_fx_rate_2)


    def npv(self, today, fwd_crv_f_d, discount_crv, including_settle=True):
        npv_1 = self.forward_1.npv(today, fwd_crv_f_d, discount_crv, including_settle=including_settle)
        npv_2 = self.forward_2.npv(today, fwd_crv_f_d, discount_crv, including_settle=including_settle)

        return npv_1 + npv_2
    

    def bbg_delta(self, today, fwd_crv_f_d, discount_crv, tweak=1, delta_type='spot'):
        tweak_param = get_pair_tweak_param(self.f_ccy + self.d_ccy)
        spot_date = fwd_crv_f_d.spot_date
        spot = FxForward(self.d_ccy, self.f_ccy, self.calendar, spot_date, 
                         fwd_crv_f_d.spot * self.notional_fccy_1, self.notional_fccy_1, 'buy')
        forward_near = FxForward(self.d_ccy, self.f_ccy, self.calendar, self.settle_date_1, 
                                 fwd_crv_f_d.spot * self.notional_fccy_1, self.notional_fccy_1, 'buy')
        forward_far = FxForward(self.d_ccy, self.f_ccy, self.calendar, self.settle_date_2, 
                                fwd_crv_f_d.spot * self.notional_fccy_1, self.notional_fccy_1, 'buy')
        
        fwd_crv_f_d_up = fwd_crv_f_d.tweak_spot(tweak / tweak_param)
        fwd_crv_f_d_down = fwd_crv_f_d.tweak_spot(-tweak / tweak_param)
        npv_up = self.npv(today, fwd_crv_f_d_up, discount_crv)   
        npv_down = self.npv(today, fwd_crv_f_d_down, discount_crv)
        if delta_type == 'spot':
            spot_npv_up = spot.npv(today, fwd_crv_f_d_up, discount_crv)
            spot_npv_down = spot.npv(today, fwd_crv_f_d_down, discount_crv)
            delta = (npv_up - npv_down) / (spot_npv_up - spot_npv_down) * self.notional_fccy_1
        elif delta_type == 'forward':
            forward_npv_up_1 = forward_near.npv(today, fwd_crv_f_d_up, discount_crv)
            forward_npv_down_1 = forward_near.npv(today, fwd_crv_f_d_down, discount_crv)
            delta_near = (npv_up - npv_down) / (forward_npv_up_1 - forward_npv_down_1)
            forward_npv_up_2 = forward_far.npv(today, fwd_crv_f_d_up, discount_crv)
            forward_npv_down_2 = forward_far.npv(today, fwd_crv_f_d_down, discount_crv)
            delta_far = (npv_up - npv_down) / (forward_npv_up_2 - forward_npv_down_2)
            delta = {'near': delta_near * self.notional_fccy_1, 
                     'far': delta_far * self.notional_fccy_1}
        else:
            raise Exception(f'Delta type error {delta_type}!')
        
        return delta
    

    # for trader use
    def delta_ccy2(self, today, fwd_crv_f_d, discount_crv, tweak=1, including_settle=True):
        delta_ccy2_1 = self.forward_1.delta_ccy2(
            today, fwd_crv_f_d, discount_crv, tweak=tweak, including_settle=including_settle)
        delta_ccy2_2 = self.forward_2.delta_ccy2(
            today, fwd_crv_f_d, discount_crv, tweak=tweak, including_settle=including_settle)

        return delta_ccy2_1 + delta_ccy2_2
    
    
    # Theta wrt 1 day change 
    def theta(self, today, fwd_crv_f_d, discount_crv, tweak=1, including_settle=True):
        theta_1 = self.forward_1.theta(today, fwd_crv_f_d, discount_crv, tweak, including_settle)
        theta_2 = self.forward_2.theta(today, fwd_crv_f_d, discount_crv, tweak, including_settle)
        
        return theta_1 + theta_2
    
    
    # Rho(DV01) wrt 0.01% change in Domestic Currency interest rate (discount curve)
    def rho(self, today, fwd_crv_f_d, discount_crv, tweak=1, tweak_type='pillar_rate'):
        rho_1 = self.forward_1.rho(today, fwd_crv_f_d, discount_crv, tweak, tweak_type)
        rho_2 = self.forward_2.rho(today, fwd_crv_f_d, discount_crv, tweak, tweak_type)
        
        return rho_1 + rho_2


    # Phi(DV01) wrt 0.01% change in Foreign Currency interest rate
    def phi(self, today, fwd_crv_f_d, discount_crv, tweak=1, tweak_type='pillar_rate'):
        phi_1 = self.forward_1.phi(today, fwd_crv_f_d, discount_crv, tweak, tweak_type)
        phi_2 = self.forward_2.phi(today, fwd_crv_f_d, discount_crv, tweak, tweak_type)
        
        return phi_1 + phi_2
    

    # for trader use (forward delta)
    def dccy_cashflow(self, today, fwd_crv_f_d):
        cashflow_1 = self.forward_1.dccy_cashflow(today, fwd_crv_f_d)
        cashflow_2 = self.forward_2.dccy_cashflow(today, fwd_crv_f_d)
        
        return cashflow_1 + cashflow_2
    

    # for trader use (forward delta)
    def fccy_cashflow(self, today, fwd_crv_f_d):
        cashflow_1 = self.forward_1.fccy_cashflow(today, fwd_crv_f_d)
        cashflow_2 = self.forward_2.fccy_cashflow(today, fwd_crv_f_d)
        
        return cashflow_1 + cashflow_2
    

    # for trader use
    def dv01s(self, today, fwd_crv_f_d, discount_crv, tweak=1):
        dv01s_1 = self.forward_1.dv01s(today, fwd_crv_f_d, discount_crv, tweak=tweak)
        dv01s_2 = self.forward_2.dv01s(today, fwd_crv_f_d, discount_crv, tweak=tweak)
        dv01_dccy = dv01s_1['DV01_dccy'] + dv01s_2['DV01_dccy']
        dv01_fccy = dv01s_1['DV01_fccy'] + dv01s_2['DV01_fccy']
        
        return {'DV01_dccy': dv01_dccy, 
                'DV01_fccy': dv01_fccy}
    

    def valuation_param(self, today, fwd_crv_f_d, discount_crv, daycount=ql.Actual365Fixed()):
        param_1 = self.forward_1.valuation_param(today, fwd_crv_f_d, discount_crv, daycount)
        param_2 = self.forward_2.valuation_param(today, fwd_crv_f_d, discount_crv, daycount)
        
        return {'spot_f_d': param_2['spot_f_d'],
                'forward_point_f_d_1': param_1['forward_point_f_d'],
                'forward_point_f_d_2': param_2['forward_point_f_d'],
                'r_f': param_2['r_f'], 
                'r_d': param_2['r_d']}
