# -*- coding: utf-8 -*-
"""
Created on Thu Jun 20 20:30:43 2024

@author: Guanzhifan
"""


import QuantLib as ql
import pandas as pd
import numpy as np 

import sys
import os
parent_folder_path = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.realpath(__file__))))
sys.path.append(parent_folder_path)

from products.fx.fx_range_accrual import FxRangeAccrual
from market.volatility.fx_vol_surface import FxVolSurfaceHK
from market.curves.fx_curves import FxForwardCurve, FxImpliedAssetCurve
from market.curves.overnight_index_curves import Sofr
from market.curves.fx_implied_discount_curve import FxUSDImpliedDiscountCurve

from utils.ql_date_utils import ql_date, ql_date_str
from utils.fx_utils import get_calendar



def valuation(inst, today, forward_curve, d_curve, vol_surface, daycount=ql.Actual365Fixed()):
    npv = inst.npv(today, forward_curve, d_curve, vol_surface, daycount)
    delta = inst.delta(today, forward_curve, d_curve, vol_surface, daycount, tweak=1)
    gamma = inst.gamma_1pct(today, forward_curve, d_curve, vol_surface, daycount, tweak=1)
    vega = inst.vega(today, forward_curve, d_curve, vol_surface, daycount, tweak=1)
    theta = inst.theta(today, forward_curve, d_curve, vol_surface, daycount, tweak=1)
    rho1 = inst.rho(today, forward_curve, d_curve, vol_surface, daycount, tweak=100, tweak_type='market') * 100
    rho2 = inst.rho(today, forward_curve, d_curve, vol_surface, daycount, tweak=100, tweak_type='pillar_rate') * 100
    phi1 = inst.phi(today, forward_curve, d_curve, vol_surface, daycount, tweak=100, tweak_type='market') * 100
    phi2 = inst.phi(today, forward_curve, d_curve, vol_surface, daycount, tweak=100, tweak_type='pillar_rate') * 100

    print(f'npv: {npv}')
    print(f'delta: {delta}')
    print(f'gamma: {gamma}')
    print(f'vega: {vega}')
    print(f'theta: {theta}')
    print(f'rho(market): {rho1}')
    print(f'rho(pillar_rate): {rho2}')
    print(f'phi(market): {phi1}')
    print(f'phi(pillar_rate): {phi2}')


#%% 
# pricer example 1
print('\nPricer example 1: USDCNH')
# trade info
d_ccy = 'CNH'
f_ccy = 'USD'
calendar = get_calendar(f_ccy, d_ccy)

start_date = ql.Date(10,7,2024)
end_date = ql.Date(9,10,2024)
obs_end_date = end_date 
obs_freq = ql.Period('1D')
obs_schedule = np.array(ql.Schedule(start_date, obs_end_date, obs_freq, 
                                    calendar, ql.ModifiedFollowing, ql.ModifiedFollowing,
                                    ql.DateGeneration.Forward, False).dates())
payment_date = ql.Date(11,10,2024)

trade_direction = 'long'
notional = 1e6
cash_ccy = 'USD'
cash_settle = True #当前默认是cash settle模式，与bbg保持一致

range_down = 7.1
down_in = True #左闭为True，否则为False
range_up = 7.3
up_in = True #右闭为True，否则为False
range_in_coupon_rate = 1
range_out_coupon_rate = 0
range_in_coupon = range_in_coupon_rate * notional
range_out_coupon = range_out_coupon_rate * notional

fx_fixing = pd.Series()

inst = FxRangeAccrual(d_ccy, f_ccy, calendar, obs_schedule, payment_date, 
                      range_down, down_in, range_up, up_in,
                      range_in_coupon, range_out_coupon, cash_ccy, trade_direction, fx_fixing, cash_settle)

# market data
today = ql.Date(9,7,2024)
ql.Settings.instance().evaluationDate = today
spot_f_d = 7.28865
## forward_curve
forward_calendar = get_calendar(f_ccy, d_ccy)
forward_curve_file = parent_folder_path + r'\market\curves\market_data\USDCNH_curve_data_20240709.xlsx'
forward_curve_data = pd.read_excel(forward_curve_file)
forward_curve_data['SettleDate'] = forward_curve_data['SettleDate'].apply(lambda x: ql_date_str(ql_date(x)))
forward_curve = FxForwardCurve(today, spot_f_d, forward_curve_data, f_ccy, d_ccy, forward_calendar, daycount=ql.Actual365Fixed())
## f_curve
f_curve_file = parent_folder_path + r'\market\curves\market_data\sofr_curve_data_20240709.xlsx'
swap_mkt_data = pd.read_excel(f_curve_file, sheet_name='swap')
fixing_data = pd.DataFrame()
f_curve = Sofr(today, swap_mkt_data=swap_mkt_data, fixing_data=fixing_data)
## d_curve
d_curve = FxUSDImpliedDiscountCurve(today, d_ccy, f_ccy+d_ccy, spot_f_d, forward_curve_data, forward_calendar,
                                    swap_mkt_data, fixing_data, calendar, daycount=ql.Actual365Fixed())
## vol_surface
vol_surface_file = parent_folder_path + r'\market\volatility\market_data\USDCNH_vol_data_20240709.xlsx'
vol_surface_data = pd.read_excel(vol_surface_file)
vol_surface = FxVolSurfaceHK(today, vol_surface_data, spot_f_d, d_ccy, f_ccy,
                             forward_curve, d_curve, f_curve, forward_calendar, daycount=ql.Actual365Fixed())

valuation(inst, today, forward_curve, d_curve, vol_surface, daycount=ql.Actual365Fixed())


#%% 
# pricer example 2
print('\nPricer example 2: EURUSD')
# trade info
d_ccy = 'USD'
f_ccy = 'EUR'
calendar = get_calendar(f_ccy, d_ccy)

start_date = ql.Date(10,7,2024)
end_date = ql.Date(9,10,2024)
obs_end_date = end_date 
obs_freq = ql.Period('1D')
obs_schedule = np.array(ql.Schedule(start_date, obs_end_date, obs_freq, 
                                    calendar, ql.ModifiedFollowing, ql.ModifiedFollowing,
                                    ql.DateGeneration.Forward, False).dates())
payment_date = ql.Date(11,10,2024)

trade_direction = 'long'
notional = 1e6
cash_ccy = 'USD'
cash_settle = True #当前默认是cash settle模式，与bbg保持一致

range_down = 1.06
down_in = True #左闭为True，否则为False
range_up = 1.1
up_in = True #右闭为True，否则为False
range_in_coupon_rate = 1
range_out_coupon_rate = 0
range_in_coupon = range_in_coupon_rate * notional
range_out_coupon = range_out_coupon_rate * notional

fx_fixing = pd.Series()

inst = FxRangeAccrual(d_ccy, f_ccy, calendar, obs_schedule, payment_date, 
                      range_down, down_in, range_up, up_in,
                      range_in_coupon, range_out_coupon, cash_ccy, trade_direction, fx_fixing, cash_settle)

# market data
today = ql.Date(9,7,2024)
ql.Settings.instance().evaluationDate = today
spot_f_d = 1.0813
## forward_curve
forward_calendar = get_calendar(f_ccy, d_ccy)
forward_curve_file = parent_folder_path + r'\market\curves\market_data\EURUSD_curve_data_20240709.xlsx'
forward_curve_data = pd.read_excel(forward_curve_file)
forward_curve_data['SettleDate'] = forward_curve_data['SettleDate'].apply(lambda x: ql_date_str(ql_date(x)))
forward_curve = FxForwardCurve(today, spot_f_d, forward_curve_data, f_ccy, d_ccy, forward_calendar, daycount=ql.Actual365Fixed())
## d_curve
d_curve_file = parent_folder_path + r'\market\curves\market_data\sofr_curve_data_20240709.xlsx'
swap_mkt_data = pd.read_excel(d_curve_file, sheet_name='swap')
fixing_data = pd.DataFrame()
d_curve = Sofr(today, swap_mkt_data=swap_mkt_data, fixing_data=fixing_data)
## f_curve
f_curve = FxImpliedAssetCurve(today, d_curve, forward_curve, calendar, daycount=ql.Actual360(), 
                              interpolation_method="zerolinear", tweak=0.0)
## vol_surface
vol_surface_file = parent_folder_path + r'\market\volatility\market_data\EURUSD_vol_data_20240709.xlsx'
vol_surface_data = pd.read_excel(vol_surface_file)
vol_surface = FxVolSurfaceHK(today, vol_surface_data, spot_f_d, d_ccy, f_ccy,
                              forward_curve, d_curve, f_curve, forward_calendar, ql.Actual365Fixed())

valuation(inst, today, forward_curve, d_curve, vol_surface, daycount=ql.Actual365Fixed())


