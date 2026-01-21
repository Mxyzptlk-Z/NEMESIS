import warnings
warnings.filterwarnings('ignore')
import copy 
import numpy as np
import QuantLib as ql

from .fx_curves import FxForwardCurve, FxImpliedAssetCurve
from .overnight_index_curves import Sofr


#FX implied discount curve using sofr curve and forward curve
class FxUSDImpliedDiscountCurve:
    def __init__(self, today, ccy, ccy_pair, spot, fx_fwd_data, fx_calendar, 
                 sofr_swap_mkt_data, sofr_fixing_data, calendar, daycount):
        self.ccy = ccy
        self.ccy_pair = ccy_pair
        self.today = today
        self.spot = spot
        self.fx_fwd_data = fx_fwd_data.copy()
        self.fx_calendar = fx_calendar
        self.sofr_swap_mkt_data = sofr_swap_mkt_data.copy()
        self.sofr_fixing_data = sofr_fixing_data.copy()
        self.calendar = calendar
        self.daycount = daycount

        self.fx_fwd_curve = FxForwardCurve(today, spot, fx_fwd_data, ccy_pair[:3], ccy_pair[3:],
                                           fx_calendar, daycount)
        self.sofr_curve = Sofr(today, swap_mkt_data=sofr_swap_mkt_data, fixing_data=sofr_fixing_data)
        self.curve = FxImpliedAssetCurve(today, self.sofr_curve, self.fx_fwd_curve, 
                                         calendar, daycount).curve


    def tweak_parallel(self, tweak):
        tweaked_curve = copy.copy(self)
        tweaked_curve.sofr_curve = self.sofr_curve.tweak_parallel(tweak)
        tweaked_curve.sofr_swap_mkt_data = tweaked_curve.sofr_curve.swap_mkt_data
        tweaked_curve.curve = FxImpliedAssetCurve(tweaked_curve.today, tweaked_curve.sofr_curve, tweaked_curve.fx_fwd_curve, 
                                                  tweaked_curve.calendar, tweaked_curve.daycount).curve
        return tweaked_curve


    def tweak_discount_curve(self, tweak, tweak_daycount=ql.Actual365Fixed(), tweak_type='zerolinear'):
        curve_tweak = copy.copy(self)
        if tweak_type == 'zerolinear':
            dfs = []
            dates = list(self.curve.dates())
            for date in dates:
                df = self.curve.discount(date)
                dcf = tweak_daycount.yearFraction(self.today, date)
                df *= np.exp(-tweak * dcf)    
                dfs.append(df)

            zeros = [-np.log(df) / tweak_daycount.yearFraction(self.today, date) 
                     for df, date in zip(dfs[1:], dates[1:])]
            zeros = [zeros[0]] + zeros
            curve_tweak.curve = ql.ZeroCurve(dates, zeros, tweak_daycount, ql.China(ql.China.IB))
        else:
            raise Exception(f'Unsupported discount curve tweak type: {tweak_type}!')
        
        return curve_tweak
