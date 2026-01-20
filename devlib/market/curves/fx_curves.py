import warnings
warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
import QuantLib as ql
import datetime as dt
import copy

from ...utils.fx_utils import get_pair_tweak_param
from ...utils.ql_date_utils import ql_date
from ...utils.fx_utils import get_fx_all_tenor_settle_dates




# FX fwd curve
# 目前仅支持主流币种，spot settle on T+2 (USDCAD/USDPHP/USDMNT/USDRUB spot settle on T+1)
class FxForwardCurve:
    def __init__(self, today, spot, fx_fwd_data, f_ccy, d_ccy, calendar, daycount):
        self.today = today
        self.spot = spot
        self.fx_fwd_data = fx_fwd_data.copy()
        self.f_ccy = f_ccy
        self.d_ccy = d_ccy
        self.calendar = calendar
        self.daycount = daycount
        self.curve = self._build(self.today, self.spot, self.fx_fwd_data, 
                                 self.calendar, self.daycount)
        
        
    def _build(self, today, spot, fx_fwd_data, calendar, daycount):
        fx_fwd_data['SettleDate'] = fx_fwd_data['SettleDate'].map(lambda x: ql_date(x))

        try:
            on = fx_fwd_data.loc[fx_fwd_data.loc[:, 'Tenor']=='ON', 'Spread'].values[0]  
            on_settle_date = fx_fwd_data.loc[fx_fwd_data.loc[:, 'Tenor']=='ON', 'SettleDate'].values[0]
        except:
            raise Exception('Missing ON spread data!')
        try:
            tn = fx_fwd_data.loc[fx_fwd_data.loc[:, 'Tenor']=='TN', 'Spread'].values[0]  
            tn_settle_date = fx_fwd_data.loc[fx_fwd_data.loc[:, 'Tenor']=='TN', 'SettleDate'].values[0]
        except:
            exist_tn = False
        else:
            exist_tn = True
        try:
            self.spot_date = fx_fwd_data.loc[fx_fwd_data.loc[:, 'Tenor']=='SPOT', 'SettleDate'].values[0]
        except:
            if self.f_ccy + self.d_ccy in ['USDCAD', 'CADUSD', 'USDPHP', 'PHPUSD', 'USDMNT', 'MNTUSD', 'USDRUB', 'RUBUSD']:
                self.spot_date = on_settle_date
            else:
                self.spot_date = get_fx_all_tenor_settle_dates(self.f_ccy, self.d_ccy, self.today, ['SPOT'])['SPOT']
            
        fwd_point_param = get_pair_tweak_param(self.f_ccy + self.d_ccy)

        fx_fwd_data_after_spot = fx_fwd_data.loc[fx_fwd_data['SettleDate'] > self.spot_date, :].copy()
        fx_fwd_data_after_spot = fx_fwd_data_after_spot.drop_duplicates(subset=['SettleDate'], keep='last')
        fx_fwd_points = list(fx_fwd_data_after_spot['Spread'])
        fx_fwd_dates = list(fx_fwd_data_after_spot['SettleDate'])
            
        if self.f_ccy + self.d_ccy in ['USDCAD', 'CADUSD', 'USDPHP', 'PHPUSD', 'USDMNT', 'MNTUSD', 'USDRUB', 'RUBUSD']:
            fx_fwd_points = [-on, 0.0] + fx_fwd_points
            fx_fwd_dates = [today, self.spot_date] + fx_fwd_dates

        else:
            if exist_tn and (not on_settle_date == tn_settle_date):
                fx_fwd_points = [-(on + tn), -tn, 0.0] + fx_fwd_points
                fx_fwd_dates = [today, on_settle_date, self.spot_date] + fx_fwd_dates
            else:
                fx_fwd_points = [-on, 0.0] + fx_fwd_points
                fx_fwd_dates = [today, self.spot_date] + fx_fwd_dates

        # df = spot(today) / fwd(future_date) = exp[(rf - rd) * t]     
        fx_fwds = [spot + s / fwd_point_param for s in fx_fwd_points]
        self.spot_today = fx_fwds[0]
        self.fx_fwd_dfs = [self.spot_today / fx_fwd for fx_fwd in fx_fwds]
        # fx_fwd_dfs = [spot / (spot + s/fwd_point_param) for s in fx_fwd_points]
        # today_fwd_df = fx_fwd_dfs[0]
        # self.spot_today = self.spot / today_fwd_df
        # fx_fwd_dfs = [df / today_fwd_df for df in fx_fwd_dfs]
        # self.spot_df = 1 / today_fwd_df 
        self.fx_fwd_dates = fx_fwd_dates
        # self.fx_fwd_dfs = fx_fwd_dfs
        curve = ql.DiscountCurve(fx_fwd_dates, self.fx_fwd_dfs, daycount, calendar)
        curve.enableExtrapolation()

        return curve 


    def get_forward(self, date):
        # 按settle date获取fx forward
        return self.spot_today / self.curve.discount(date)
    
    def get_forward_spot(self, date):
        # 按spot date获取fx forward
        real_date = date #当前默认T+0
        return self.get_forward(real_date)
    

    def tweak_spot(self, tweak):
        tweaked_curve = copy.copy(self)
        tweaked_curve.spot_today = self.spot_today * (self.spot + tweak) / self.spot
        tweaked_curve.spot = self.spot + tweak

        return tweaked_curve
    

    # rd up or rf down
    def tweak_parallel(self, tweak):
        tweaked_curve = copy.copy(self)
        tweaked_curve.fx_fwd_dfs = copy.deepcopy(self.fx_fwd_dfs)
        today = self.today
        fx_fwd_dates = self.fx_fwd_dates
        calendar = self.calendar
        daycount = self.daycount
        for i in range(len(tweaked_curve.fx_fwd_dfs)):
            tweaked_curve.fx_fwd_dfs[i] *= np.exp(-tweak * daycount.yearFraction(today, fx_fwd_dates[i]))
        
        curve = ql.DiscountCurve(fx_fwd_dates, tweaked_curve.fx_fwd_dfs, daycount, calendar)
        curve.enableExtrapolation()
        tweaked_curve.curve = curve
        tweaked_curve.spot = tweaked_curve.get_forward(self.spot_date)

        return tweaked_curve
    

    # forward curve after dccy curve tweak
    def tweak_dccy_curve(self, dccy_curve_orig, dccy_curve_tweaked):
        tweaked_curve = copy.copy(self)
        tweaked_curve.fx_fwd_dfs = copy.deepcopy(self.fx_fwd_dfs)
        today = self.today
        fx_fwd_dates = self.fx_fwd_dates
        calendar = self.calendar
        daycount = self.daycount
        for i in range(len(tweaked_curve.fx_fwd_dfs)):
            dccy_df_orig = (dccy_curve_orig.curve.discount(fx_fwd_dates[i]) / 
                            dccy_curve_orig.curve.discount(today))
            dccy_df_tweaked = (dccy_curve_tweaked.curve.discount(fx_fwd_dates[i]) / 
                               dccy_curve_tweaked.curve.discount(today))
            tweaked_curve.fx_fwd_dfs[i] *= dccy_df_tweaked / dccy_df_orig

        curve = ql.DiscountCurve(fx_fwd_dates, tweaked_curve.fx_fwd_dfs, daycount, calendar)
        curve.enableExtrapolation()
        tweaked_curve.curve = curve

        return tweaked_curve


class CryptoFxForwardCurve(FxForwardCurve):
    def __init__(self, today, spot, spot_date, fx_fwd_data, f_ccy, d_ccy, calendar, daycount):
        self.today = today
        self.spot = spot
        self.spot_date = spot_date
        self.fx_fwd_data = fx_fwd_data.copy()
        self.f_ccy = f_ccy
        self.d_ccy = d_ccy
        self.calendar = calendar
        self.daycount = daycount
        self.curve = self._build()

    def _build(self):
        self.spot_today = self.spot
        spot_data = pd.DataFrame({
            'QlDate': [self.today, self.spot_date],
            'Price': [self.spot_today, self.spot]
        })
        fwd_data = self.fx_fwd_data.copy()
        fwd_data['QlDate'] = self.fx_fwd_data['SettleDate'].map(lambda x: ql_date(x))
        all_data = pd.concat([spot_data, fwd_data[['QlDate', 'Price']]], ignore_index=True)
        all_data.drop_duplicates(subset=['QlDate'], keep='first', inplace=True)
        self.fx_fwd_dates = list(all_data['QlDate'])
        self.fx_fwd_dfs = self.spot_today / np.array(list(all_data['Price']))
        curve = ql.DiscountCurve(self.fx_fwd_dates, self.fx_fwd_dfs, self.daycount, self.calendar)
        curve.enableExtrapolation()
        return curve


# FX implied fwd curve
# 由给定日期的汇率与两条折线曲线推导
class FxImpliedForwardCurve:
    def __init__(self, today, spot, f_dis_curve, d_dis_curve, f_ccy, d_ccy, spot_date=None):
        self.today = today
        self.spot = spot
        self.f_dis_curve = copy.copy(f_dis_curve)
        self.d_dis_curve = copy.copy(d_dis_curve)
        self.f_ccy = f_ccy
        self.d_ccy = d_ccy

        if spot_date is None:
            self.spot_date = today
        else:
            self.spot_date = spot_date


    def get_forward(self, date):
        f_dis_crv = self.f_dis_curve.curve
        d_dis_crv = self.d_dis_curve.curve
        
        forward = self.spot * f_dis_crv.discount(date) / d_dis_crv.discount(date) \
            * d_dis_crv.discount(self.spot_date) / f_dis_crv.discount(self.spot_date)
        
        return forward
    
    
    def get_forward_spot(self, date):
        # 按spot date获取fx forward
        real_date = date #当前默认T+0
        return self.get_forward(real_date)
    
    
    # forward curve after dccy curve tweak
    def tweak_dccy_curve(self, tweak):
        tweaked_curve = copy.copy(self)
        tweaked_d_dis_curve = self.d_dis_curve.tweak_parallel(tweak)
        tweaked_curve.d_dis_curve = tweaked_d_dis_curve

        return tweaked_curve


    # forward curve after fccy curve tweak
    def tweak_fccy_curve(self, tweak):
        tweaked_curve = copy.copy(self)
        tweaked_f_dis_curve = self.f_dis_curve.tweak_parallel(tweak)
        tweaked_curve.f_dis_curve = tweaked_f_dis_curve

        return tweaked_curve
    
    
    def tweak_spot(self, tweak):
        tweaked_curve = copy.copy(self)
        tweaked_curve.spot = self.spot + tweak

        return tweaked_curve


#FX implied curve (interest rate curve)
class FxImpliedAssetCurve:
    def __init__(self, today, base_curve, fx_fwd_crv, calendar, daycount, 
                 interpolation_method="zerolinear", tweak=0.0):
        self.today = today
        self.base_curve = base_curve
        self.fx_fwd_crv = fx_fwd_crv
        self.calendar = calendar
        self.daycount = daycount
        self.interpolation_method = interpolation_method
        self.tweak = tweak

        if base_curve.ccy == fx_fwd_crv.d_ccy:
            self.ccy = fx_fwd_crv.f_ccy
        else:
            self.ccy = fx_fwd_crv.d_ccy
        
        self.curve = self._build(self.today, self.base_curve, self.fx_fwd_crv, self.calendar, 
                                 self.daycount, self.interpolation_method, self.tweak)
        self.index = None
        
        
    def _build(self, today, base_curve, fx_fwd_crv, calendar, daycount, 
               interpolation_method="dfloglinear", tweak=0.0):
        asset_dates = list(base_curve.curve.dates())
        if not asset_dates[0] == today:
            raise Exception('Date error')
        
        if base_curve.ccy == fx_fwd_crv.d_ccy:
            asset_dfs = [1] + [base_curve.curve.discount(d) / fx_fwd_crv.curve.discount(d) * 
                               np.exp(-tweak * daycount.yearFraction(today, d)) 
                               for d in asset_dates[1:]]
        else:
            asset_dfs = [1] + [base_curve.curve.discount(d) * fx_fwd_crv.curve.discount(d) * 
                               np.exp(-tweak * daycount.yearFraction(today, d)) 
                               for d in asset_dates[1:]]
            
        if interpolation_method == "zerolinear":
            asset_zeros = [-np.log(df) / daycount.yearFraction(today, date) 
                           for df, date in zip(asset_dfs[1:], asset_dates[1:])]
            asset_zeros = [asset_zeros[0]] + asset_zeros
            asset_crv = ql.ZeroCurve(asset_dates, asset_zeros, daycount, calendar)      
        elif interpolation_method == "dfloglinear":
            asset_crv = ql.DiscountCurve(asset_dates, asset_dfs, daycount, calendar)
        else:
            raise Exception(f'Unsupported interpolation method: {interpolation_method}')     

        asset_crv.enableExtrapolation()

        return asset_crv 


    def tweak_parallel(self, tweak):
        today = self.today
        base_curve = self.base_curve
        fx_fwd_crv = self.fx_fwd_crv
        calendar = self.calendar
        daycount = self.daycount
        interpolation_method = self.interpolation_method

        return FxImpliedAssetCurve(today, base_curve, fx_fwd_crv, calendar, daycount, 
                                   interpolation_method=interpolation_method, tweak=tweak)
