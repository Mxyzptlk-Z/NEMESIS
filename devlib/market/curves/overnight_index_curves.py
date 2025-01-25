import QuantLib as ql

import devlib.market.curves.curve_generator as cg
from devlib.market.curves.curve_generator import GeneralCurveGenerator



class Sofr(cg.GeneralCurve):
    def curve_config_set(self):
        self.index_config = cg.OvernightIndexConfig(
            curve_name = "SOFR",
            ois_index_class=ql.Sofr)
        
        self.deposit_config = None
        
        self.swap_config = cg.OisRateHelperConfig(
            settlement_delay=2,
            calendar=ql.UnitedStates(ql.UnitedStates.FederalReserve), 
            payment_lag=2,
            payment_freq=ql.Annual, 
            payment_convention=ql.Following,
            spread=0, 
            forward_start=0)
        
        self.fra_config = None
        
        self.future_config = None
        
        self.curve_generator_config = GeneralCurveGenerator



class Estr(cg.GeneralCurve):
    def curve_config_set(self):
        self.index_config = cg.OvernightIndexConfig(
            curve_name = "ESTR",
            ois_index_class=ql.Eonia)
        
        self.deposit_config = None
        
        self.swap_config = cg.OisRateHelperConfig(
            settlement_delay=2,
            calendar=ql.TARGET(), 
            payment_lag=1,
            payment_freq=ql.Annual, 
            payment_convention=ql.Following,
            spread=0, 
            forward_start=0)
        
        self.fra_config = None
        
        self.future_config = None
        
        self.curve_generator_config = GeneralCurveGenerator



class Tona(cg.GeneralCurve):
    def curve_config_set(self):
        self.index_config = cg.GeneralOvernightIndexConfig(
            curve_name='TONA', 
            settlement_delay=0, 
            currency=ql.JPYCurrency(),
            calendar=ql.Japan(), 
            daycount=ql.Actual365Fixed())
        
        self.deposit_config = None
        
        self.swap_config = cg.OisRateHelperConfig(
            settlement_delay=2,
            calendar=ql.Japan(), 
            payment_lag=2,
            payment_freq=ql.Annual, 
            payment_convention=ql.Following,
            spread=0, 
            forward_start=0)
        
        self.fra_config = None
        
        self.future_config = None
        
        self.curve_generator_config = GeneralCurveGenerator



class TthoronOisRateHelperConfig(cg.OisRateHelperConfig):
    def __init__(
            self, 
            settlement_delay: int,
            calendar: ql.Calendar, 
            payment_lag:int, 
            payment_convention: int, 
            spread: float, 
            forward_start: int, 
            ):
        self.settlement_delay = settlement_delay
        self.calendar = calendar
        self.payment_lag = payment_lag
        self.payment_convention = payment_convention
        self.spread = spread
        self.forward_start = forward_start
        
    def build_swap_helper(
            self, 
            tenor: str, 
            rate: float, 
            index: ql.Index, 
            ):
        if ql.Period(tenor) < ql.Period("1Y"):
            payment_freq = ql.Annual
        else:
            payment_freq = ql.Quarterly
            
        if ql.Period(tenor) > ql.Period(payment_freq):
            pillar_date_type = ql.Pillar.LastRelevantDate
        else:
            pillar_date_type = ql.Pillar.MaturityDate
            
        hp = ql.OISRateHelper(
            self.settlement_delay, ql.Period(tenor), 
            ql.QuoteHandle(ql.SimpleQuote(rate)), index,
            ql.YieldTermStructureHandle(), True, self.payment_lag,
            self.payment_convention, payment_freq, self.calendar,
            ql.Period(str(self.forward_start) + 'D'),
            self.spread, pillar_date_type, ql.Date())   
        
        return hp    



class Tthoron(cg.GeneralCurve):
    def curve_config_set(self):
        self.index_config = cg.GeneralOvernightIndexConfig(
            curve_name='TTHORON', 
            settlement_delay=0, 
            currency=ql.THBCurrency(),
            calendar=ql.Thailand(), 
            daycount=ql.Actual365Fixed())
        
        self.deposit_config = None
        
        self.swap_config = TthoronOisRateHelperConfig(
            settlement_delay=2,
            calendar=ql.Thailand(), 
            payment_lag=2, 
            payment_convention=ql.ModifiedFollowing, 
            spread=0, 
            forward_start=0)
        
        self.fra_config = None
        
        self.future_config = None
        
        self.curve_generator_config = GeneralCurveGenerator



class Honia(cg.GeneralCurve):
    def curve_config_set(self):
        self.index_config = cg.GeneralOvernightIndexConfig(
            curve_name='HONIA', 
            settlement_delay=0, 
            currency=ql.HKDCurrency(),
            calendar=ql.HongKong(), 
            daycount=ql.Actual365Fixed())
        
        self.deposit_config = None
        
        self.swap_config = cg.OisRateHelperConfig(
            settlement_delay=2,
            calendar=ql.HongKong(), 
            payment_lag=2,
            payment_freq=ql.Quarterly, 
            payment_convention=ql.Following,
            spread=0, 
            forward_start=0)
        
        self.fra_config = None
        
        self.future_config = None
        
        self.curve_generator_config = GeneralCurveGenerator
        
        
class Sora(cg.GeneralCurve):
    def curve_config_set(self):
        self.index_config = cg.GeneralOvernightIndexConfig(
            curve_name='SORA', 
            settlement_delay=0, 
            currency=ql.SGDCurrency(),
            calendar=ql.Singapore(), 
            daycount=ql.Actual365Fixed())
        
        self.deposit_config = None
        
        self.swap_config = SoraOisRateHelperConfig(
            settlement_delay=2,
            calendar=ql.Singapore(), 
            payment_lag=2,
            payment_convention=ql.ModifiedFollowing,
            spread=0, 
            forward_start=0)
        
        self.fra_config = None
        
        self.future_config = None
        
        self.curve_generator_config = GeneralCurveGenerator


class SoraOisRateHelperConfig(cg.OisRateHelperConfig):
    def __init__(
            self, 
            settlement_delay: int,
            calendar: ql.Calendar, 
            payment_lag:int, 
            payment_convention: int, 
            spread: float, 
            forward_start: int, 
            ):
        self.settlement_delay = settlement_delay
        self.calendar = calendar
        self.payment_lag = payment_lag
        self.payment_convention = payment_convention
        self.spread = spread
        self.forward_start = forward_start
        
    def build_swap_helper(
            self, 
            tenor: str, 
            rate: float, 
            index: ql.Index, 
            ):
        if ql.Period(tenor) < ql.Period("1Y"):
            payment_freq = ql.Annual
        else:
            payment_freq = ql.Semiannual
            
        if ql.Period(tenor) > ql.Period(payment_freq):
            pillar_date_type = ql.Pillar.LastRelevantDate
        else:
            pillar_date_type = ql.Pillar.MaturityDate
            
        hp = ql.OISRateHelper(
            self.settlement_delay, ql.Period(tenor), 
            ql.QuoteHandle(ql.SimpleQuote(rate)), index,
            ql.YieldTermStructureHandle(), True, self.payment_lag,
            self.payment_convention, payment_freq, self.calendar,
            ql.Period(str(self.forward_start) + 'D'),
            self.spread, pillar_date_type, ql.Date())   
        
        return hp    

    
class Saron(cg.GeneralCurve):
    def curve_config_set(self):
        self.index_config = cg.GeneralOvernightIndexConfig(
            curve_name='SARON', 
            settlement_delay=0, 
            currency=ql.CHFCurrency(),
            calendar=ql.Switzerland(), 
            daycount=ql.Actual360())
        
        self.deposit_config = None
        
        self.swap_config = cg.OisRateHelperConfig(
            settlement_delay=2,
            calendar=ql.Switzerland(), 
            payment_lag=2,
            payment_freq=ql.Annual, 
            payment_convention=ql.ModifiedFollowing,
            spread=0, 
            forward_start=0)
        
        self.fra_config = None
        
        self.future_config = None
        
        self.curve_generator_config = GeneralCurveGenerator