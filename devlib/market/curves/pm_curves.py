import QuantLib as ql
import pandas as pd

from .fx_curves import FxForwardCurve

from ...utils.ql_date_utils import ql_date, ql_date_str
from ...utils.fx_utils import get_fx_all_tenor_settle_dates


class PmForwardCurve(FxForwardCurve):
    def __init__(self, today, spot, pm_fwd_data, f_ccy, d_ccy, calendar, daycount, data_type):
        self.today = today
        self.spot = spot
        self.fx_fwd_data = pm_fwd_data.copy()
        self.f_ccy = f_ccy
        self.d_ccy = d_ccy
        self.calendar = calendar
        self.daycount = daycount
        
        if data_type == 'rate':
            self.data_type = data_type
            self.rate_daycount = ql.Actual360()
        elif data_type == 'spread':
            self.data_type = data_type
        else:
            raise Exception(f'Unsupported data type: {data_type}!')
        
        super().__init__(self.today, self.spot, self.fx_fwd_data, self.f_ccy, self.d_ccy, self.calendar, self.daycount)
        
        self.curve = self._build(self.today, self.spot, self.fx_fwd_data, self.calendar, self.daycount)
        
        
    def _build(self, today, spot, fx_fwd_data, calendar, daycount):
        fx_fwd_data['SettleDate'] = fx_fwd_data['SettleDate'].map(lambda x: ql_date(x))
        
        try:
            self.spot_date = fx_fwd_data.loc[fx_fwd_data.loc[:,'Tenor']=='SPOT', 'SettleDate'].values[0]
        except:
            self.spot_date = get_fx_all_tenor_settle_dates(self.f_ccy, self.d_ccy, self.today, ['SPOT'])['SPOT']
        fx_fwd_data_after_spot = fx_fwd_data.loc[fx_fwd_data['SettleDate'] > self.spot_date, :].copy()
        fx_fwd_data_after_spot = fx_fwd_data_after_spot.drop_duplicates(subset=['SettleDate'], keep='last')
        
        self.fx_fwd_dates = [today, self.spot_date] + list(fx_fwd_data_after_spot['SettleDate'])
        if self.data_type == 'rate':
            fx_fwd_rates = [0.0, 0.0] + list(fx_fwd_data_after_spot['Rate'])
            fx_fwds = [spot + spot * r * self.rate_daycount.yearFraction(self.spot_date, d)
                       for r,d in zip(fx_fwd_rates, self.fx_fwd_dates)]
        else:
            fx_fwd_points = [0.0, 0.0] + list(fx_fwd_data_after_spot['Spread'])
            fx_fwds = [spot + p / 100 for p in fx_fwd_points]
        self.spot_today = fx_fwds[0]
        self.fx_fwd_dfs = [self.spot_today / f for f in fx_fwds]
        
        curve = ql.DiscountCurve(self.fx_fwd_dates, self.fx_fwd_dfs, daycount, calendar)
        curve.enableExtrapolation()
        return curve
    
    
        
class XauCnhForwardCurve(PmForwardCurve):
    def __init__(self, today, spot, spot_date,
                 usd_cnh_spot, usd_cnh_fwd_data,
                 xau_usd_spot, xau_usd_fwd_data,
                 calendar, daycount):
        
        self.today = today
        self.spot = spot
        self.spot_date = spot_date
        self.usd_cnh_spot = usd_cnh_spot
        self.usd_cnh_fwd_data = usd_cnh_fwd_data.copy()
        self.xau_usd_spot = xau_usd_spot
        self.xau_usd_fwd_data = xau_usd_fwd_data.copy()
        self.f_ccy = 'XAU'
        self.d_ccy = 'CNH'
        self.calendar = calendar
        self.daycount = daycount
        
        usd_cnh_forward_curve = FxForwardCurve(
            today, usd_cnh_spot, usd_cnh_fwd_data, 'USD', self.d_ccy,
            ql.NullCalendar(), ql.Actual365Fixed())
        xau_usd_forward_curve = PmForwardCurve(
            today, xau_usd_spot, xau_usd_fwd_data, self.f_ccy, 'USD',
            ql.NullCalendar(), ql.Actual365Fixed(), 'rate')
        
        spot_data = pd.DataFrame(data={'Tenor': ['SPOT'],
                                       'SettleDate': [spot_date],
                                       'Spread': [spot]})

        tenors = list(xau_usd_fwd_data['Tenor'][xau_usd_fwd_data['Tenor']!='SPOT'])
        tenor_settle_dates = get_fx_all_tenor_settle_dates(self.f_ccy, self.d_ccy, self.today, tenors)

        pm_fwd_data_after_spot = pd.DataFrame({'Tenor': tenors})
        pm_fwd_data_after_spot['SettleDate'] = tenor_settle_dates.values
        pm_fwd_data_after_spot['Spread'] = pm_fwd_data_after_spot['SettleDate'].\
            map(lambda x: (usd_cnh_forward_curve.get_forward(x)
                           * xau_usd_forward_curve.get_forward(x) - spot) * 100)
        
        pm_fwd_data = pd.concat([spot_data, pm_fwd_data_after_spot], ignore_index=True)
        pm_fwd_data['SettleDate'] = pm_fwd_data['SettleDate'].map(lambda x: ql_date_str(x))

        super().__init__(self.today, self.spot, pm_fwd_data, self.f_ccy, self.d_ccy, self.calendar, self.daycount, 'spread')



