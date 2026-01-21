from abc import abstractmethod
import numpy as np
import QuantLib as ql

from ...utils.fx_utils import get_ccy_pair, fx_ccy_trans, get_pair_tweak_param
from ...models.bsm.black76 import NegativeSigmaError



class FxBaseOption:
    def __init__(self, d_ccy, f_ccy, calendar):  
        self.d_ccy = d_ccy
        self.f_ccy = f_ccy
        self.calendar = calendar
        

    # NPV
    @abstractmethod
    def npv(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount=ql.Actual365Fixed()):
        
        pass
    
    
    # Delta wrt Foreign/Domestic FX spot 
    def delta(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
              daycount=ql.Actual365Fixed(), tweak=1):
        tweak_param = get_pair_tweak_param(self.f_ccy + self.d_ccy)
        fwd_crv_f_d_up = fwd_crv_f_d.tweak_spot(tweak / tweak_param)
        fwd_crv_f_d_down = fwd_crv_f_d.tweak_spot(-tweak / tweak_param)
        npv_up = self.npv(today, fwd_crv_f_d_up, discount_crv, vol_surf_f_d, daycount)   
        npv_down = self.npv(today, fwd_crv_f_d_down, discount_crv, vol_surf_f_d, daycount)
        delta = (npv_up - npv_down) / (2 * tweak / tweak_param)
        
        return delta
    

    # 将delta转化为货币2计价
    def delta_ccy2(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
                   daycount=ql.Actual365Fixed(), tweak=1):
        delta = self.delta(today, fwd_crv_f_d, discount_crv, 
                           vol_surf_f_d, daycount, tweak)
        
        return -delta * fwd_crv_f_d.spot
    

    # 具有相同delta的forward notional(货币2数量)
    def forward_delta(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
                      daycount=ql.Actual365Fixed(), tweak=1):
        spot_delta = self.delta(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount, tweak)
        fwd_date = self.payment_date
        spot_date = fwd_crv_f_d.spot_date
        if fwd_date < today:
            raise Exception('Payment date should be later than today!')
        rf_adj = ((fwd_crv_f_d.curve.discount(fwd_date) / fwd_crv_f_d.curve.discount(spot_date)) / 
                  (discount_crv.curve.discount(fwd_date) / discount_crv.curve.discount(spot_date)))

        return spot_delta * rf_adj
    

    def forward_delta_ccy2(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
                           daycount=ql.Actual365Fixed(), tweak=1):
        forward_delta = self.forward_delta(today, fwd_crv_f_d, discount_crv, 
                                           vol_surf_f_d, daycount, tweak)

        return -forward_delta * fwd_crv_f_d.spot
    

    # Gamma wrt Foreign/Domestic FX spot 
    def gamma(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
              daycount=ql.Actual365Fixed(), tweak=1):  
        tweak_param = get_pair_tweak_param(self.f_ccy + self.d_ccy)
        fwd_crv_f_d_up = fwd_crv_f_d.tweak_spot(tweak / tweak_param)
        fwd_crv_f_d_down = fwd_crv_f_d.tweak_spot(-tweak / tweak_param)
        npv = self.npv(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount)   
        npv_up = self.npv(today, fwd_crv_f_d_up, discount_crv, vol_surf_f_d, daycount)   
        npv_down = self.npv(today, fwd_crv_f_d_down, discount_crv, vol_surf_f_d, daycount)
        gamma = (npv_up + npv_down - 2 * npv) / ((tweak / tweak_param) ** 2)
        
        return gamma
    

    def gamma_1pip(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
                   daycount=ql.Actual365Fixed(), tweak=1):
        tweak_param = get_pair_tweak_param(self.f_ccy + self.d_ccy)
        return self.gamma(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
                          daycount, tweak) / tweak_param
    

    def gamma_1pct(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
                   daycount=ql.Actual365Fixed(), tweak=1):
        
        return self.gamma(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
                          daycount, tweak) * fwd_crv_f_d.spot * 0.01
    

    # 将gamma_1pip转化为货币2的数量
    def gamma_ccy2_1pip(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
                         daycount=ql.Actual365Fixed(), tweak=1):
        gamma_1pip = self.gamma_1pip(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
                                       daycount, tweak)
        
        return -gamma_1pip * fwd_crv_f_d.spot
        

    # 将gamma_1pct转化为货币2的数量
    def gamma_ccy2_1pct(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
                        daycount=ql.Actual365Fixed(), tweak=1):
        gamma_1pct = self.gamma_1pct(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
                                     daycount, tweak)
        
        return -gamma_1pct * fwd_crv_f_d.spot

    
    # Vega wrt Foreign/Domestic FX Vol (1%) 
    def vega(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
             daycount=ql.Actual365Fixed(), tweak=1):
        vol_surf_f_d_up = vol_surf_f_d.vol_tweak(tweak / 100)
        vol_surf_f_d_down = vol_surf_f_d.vol_tweak(-tweak / 100)
        npv_up = self.npv(today, fwd_crv_f_d, discount_crv, vol_surf_f_d_up, daycount)  
        try:
            npv_down = self.npv(today, fwd_crv_f_d, discount_crv, vol_surf_f_d_down, daycount)
            vega = (npv_up - npv_down) / (2 * tweak)
        except NegativeSigmaError as e:
            print("当前波动率较小，采用单边前向差分法计算vega")
            npv = self.npv(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount)
            vega = (npv_up - npv) / tweak            
        
        return vega
    

    def volga(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
              daycount=ql.Actual365Fixed(), tweak=1):
        try:
            vol_surf_f_d_down = vol_surf_f_d.vol_tweak(-tweak / 100)
            npv_down = self.npv(today, fwd_crv_f_d, discount_crv, vol_surf_f_d_down, daycount)
            vol_surf_f_d_up = vol_surf_f_d.vol_tweak(tweak / 100)
            npv_up = self.npv(today, fwd_crv_f_d, discount_crv, vol_surf_f_d_up, daycount)   
            npv = self.npv(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount)
            volga = (npv_up + npv_down - 2 * npv) / ((tweak) ** 2)
        except NegativeSigmaError as e:
            print("当前波动率较小，采用单边前向差分法计算volga")
            vol_surf_f_d_up = vol_surf_f_d.vol_tweak(tweak / 100)
            vol_surf_f_d_up_up = vol_surf_f_d.vol_tweak(2 * tweak / 100)            
            npv_up = self.npv(today, fwd_crv_f_d, discount_crv, vol_surf_f_d_up, daycount) 
            npv_up_up = self.npv(today, fwd_crv_f_d, discount_crv, vol_surf_f_d_up_up, daycount)            
            npv = self.npv(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount)
            volga = (npv_up_up + npv - 2 * npv_up) / ((tweak) ** 2)
        
        return volga
    

    def vanna(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
              daycount=ql.Actual365Fixed(), tweak=1):
        vol_surf_f_d_up = vol_surf_f_d.vol_tweak(tweak / 100)
        vol_surf_f_d_down = vol_surf_f_d.vol_tweak(-tweak / 100)
        delta_up = self.delta(today, fwd_crv_f_d, discount_crv, vol_surf_f_d_up, daycount)
        try:
            delta_down = self.delta(today, fwd_crv_f_d, discount_crv, vol_surf_f_d_down, daycount)
            vanna = (delta_up - delta_down) / (2 * tweak)
        except NegativeSigmaError as e:
            print("当前波动率较小，采用单边前向差分法计算vanna")
            delta = self.delta(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount)
            vanna = (delta_up - delta) / tweak 
        
        return vanna


    # Theta wrt 1 day change     
    def theta(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
              daycount=ql.Actual365Fixed(), tweak=1):
        npv = self.npv(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount)    
        tmr = self.calendar.advance(today, ql.Period(str(tweak) + 'D'))
        npv_tmr = self.npv(tmr, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount) 
        
        return (npv_tmr - npv) / tweak
    

    # Rho(DV01) wrt 0.01% change in Domestic Currency interest rate (discount curve)  
    def rho(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
            daycount=ql.Actual365Fixed(), tweak=1, tweak_type='pillar_rate'):
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
        npv_up = self.npv(today, fwd_crv_f_d_up, discount_crv_up, vol_surf_f_d, daycount) 
        npv_down = self.npv(today, fwd_crv_f_d_down, discount_crv_down, vol_surf_f_d, daycount) 
 
        return (npv_up - npv_down) / (2 * tweak)


    # Phi(DV01) wrt 0.01% change in Foreign Currency interest rate
    def phi(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
            daycount=ql.Actual365Fixed(), tweak=1, tweak_type='pillar_rate'):
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
        npv_up = self.npv(today, fwd_crv_f_d_down, discount_crv, vol_surf_f_d, daycount) 
        npv_down = self.npv(today, fwd_crv_f_d_up, discount_crv, vol_surf_f_d, daycount)
 
        return (npv_up - npv_down) / (2 * tweak)
    


    # REPORT GREEKS
    def report_delta(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
                     daycount=ql.Actual365Fixed(), tweak=1):
        
        return self.delta(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount, tweak)
    
    
    def report_gamma(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
                     daycount=ql.Actual365Fixed(), tweak=1):
        
        return self.gamma(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount, tweak)
    

    def report_vega(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d,  
                    daycount=ql.Actual365Fixed(), tweak=1):
        vega = self.vega(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount, tweak)
        
        return vega * 100
    

    def report_theta(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
                     daycount=ql.Actual365Fixed()):
        theta = self.theta(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount, tweak=1)
        tmr = self.calendar.advance(today, ql.Period('1D'))
        dt = daycount.yearFraction(today, tmr)
        
        return theta / dt
    

    def report_rho(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
                   daycount=ql.Actual365Fixed(), tweak=1):
        rho = self.rho(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount, tweak)
        
        return rho * 10000
    

    def report_delta_cash(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
                          daycount=ql.Actual365Fixed(), tweak=1):
        report_delta = self.report_delta(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
                                         daycount, tweak)
        
        return report_delta * fwd_crv_f_d.spot
    

    def report_gamma_cash(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d,  
                          daycount=ql.Actual365Fixed(), tweak=1):
        gamma_1pct = self.gamma_1pct(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, daycount, tweak)
        
        return gamma_1pct * fwd_crv_f_d.spot
    

    def report_vega_cash(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
                         daycount=ql.Actual365Fixed(), tweak=1):
        report_vega = self.report_vega(today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
                                       daycount, tweak)
        
        return report_vega * 0.01
    
    
    # Report pricing parameters at initial
    def pricing_param(self, today, fwd_crv_f_d, discount_crv, 
                      vol_surf_f_d, daycount=ql.Actual365Fixed()):
        if today > self.expiry:
            raise Exception('Today is later than expiry!')
        
        sigma_f_d = vol_surf_f_d.interp_vol(self.expiry, self.strike)
        r = discount_crv.curve.zeroRate(self.expiry, daycount, ql.Continuous).rate()
        
        return {'PricingVol': sigma_f_d, 'RiskFreeRate': r}
    

    def _set_target_date(self):
        
        return self.expiry
    

    def _common_valuation_param(self, today, target_date, fwd_crv_f_d, 
                                discount_crv, daycount=ql.Actual365Fixed()):
        if today > target_date:
            raise Exception('Today is later than valuation target_date!')
        
        r_d = discount_crv.curve.zeroRate(target_date, daycount, ql.Continuous).rate()
        r_f_d = fwd_crv_f_d.curve.zeroRate(target_date, daycount, ql.Continuous).rate()
        r_f = r_d - r_f_d
        spot_f_d = fwd_crv_f_d.spot
        forward_f_d = fwd_crv_f_d.get_forward(target_date)
        tweak_param = get_pair_tweak_param(self.f_ccy + self.d_ccy)
        forward_point_f_d = (forward_f_d - spot_f_d) * tweak_param
        
        return {'spot_f_d': spot_f_d,
                'forward_f_d': forward_f_d,
                'forward_point_f_d': forward_point_f_d,
                'r_f': r_f, 
                'r_d': r_d}


    def _specific_valuation_param(self, today, fwd_crv_f_d, discount_crv, 
                                  vol_surf_f_d, daycount=ql.Actual365Fixed()):
        sigma_f_d = vol_surf_f_d.interp_vol(self.expiry, self.strike)

        return {'sigma_f_d': sigma_f_d}


    def valuation_param(self, today, fwd_crv_f_d, discount_crv, vol_surf_f_d, 
                        daycount=ql.Actual365Fixed()):
        target_date = self._set_target_date()
        params = self._common_valuation_param(today, target_date, fwd_crv_f_d, 
                                              discount_crv, daycount)
        params_2 = self._specific_valuation_param(today, fwd_crv_f_d,discount_crv, 
                                                  vol_surf_f_d, daycount)

        return dict(params, **params_2)
    
    
