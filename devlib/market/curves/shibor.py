import QuantLib as ql

import devlib.market.curves.curve_generator as cg
from .curve_generator import GeneralCurveGenerator



class Shibor3M(cg.GeneralCurve):
    def curve_config_set(self):
        self.index_config = cg.IborIndexConfig(
            curve_name='SHIBOR3M', 
            tenor='3M', 
            settlement_delay=1, 
            currency=ql.CNYCurrency(),
            calendar=ql.China(ql.China.IB), 
            convention=ql.ModifiedFollowing, 
            end_of_month=False, 
            daycount=ql.Actual360())
        
        self.deposit_config = cg.DepositHelperConfig(
            settlement_delay=1, 
            calendar=ql.China(ql.China.IB), 
            convention=ql.ModifiedFollowing, 
            end_of_month=False, 
            daycount=ql.Actual360())
        
        self.swap_config = cg.SwapRateHelperConfig(
            calendar=ql.China(ql.China.IB), 
            fixed_pay_freq=ql.Quarterly, 
            fixed_convention=ql.ModifiedFollowing,
            fixed_daycount=ql.Actual365Fixed(), 
            spread=0, 
            forward_start=0, 
            end_of_month=False)
        
        self.fra_config = None
        
        self.future_config = None
        
        self.curve_generator_config = GeneralCurveGenerator        
