# -*- coding: utf-8 -*-
"""
Created on Thu Jun 20 19:42:26 2024

@author: Guanzhifan
"""

import QuantLib as ql
import pandas as pd

import sys
import os
parent_folder_path = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
sys.path.append(parent_folder_path)

from devlib.products.fx import fx_vanilla
from devlib.market.volatility.fx_vol_surface import FxVolSurfaceHK
from devlib.market.curves.fx_curves import FxForwardCurve, FxImpliedAssetCurve
from devlib.market.curves.fx_implied_discount_curve import FxUSDImpliedDiscountCurve
from devlib.market.curves.shibor import Shibor3M
from devlib.market.curves.overnight_index_curves import Sofr

from devlib.utils import ql_calendar_utils
from devlib.utils.ql_date_utils import ql_date, ql_date_str
from devlib.utils.fx_utils import get_calendar



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
print('\nPricer example 1:')
# trade info
d_ccy = 'CNY'
f_ccy = 'USD'
calendar = get_calendar(f_ccy, d_ccy)
expiry = ql.Date(17,1,2025)
payment_date = calendar.advance(expiry, ql.Period(2, ql.Days))
flavor = 'call'
strike = 7.3
notional = 1e6
notional_ccy = 'USD'
trade_direction = 'long'

inst = fx_vanilla.FxVanilla(d_ccy, f_ccy, calendar, expiry, payment_date, flavor, strike,
                            notional, notional_ccy, trade_direction)


# market data
today = ql.Date(25,3,2024)
ql.Settings.instance().evaluationDate = today
spot_f_d = 7.21145
## forward_curve
forward_daycount = ql.Actual365Fixed()
forward_calendar = get_calendar(f_ccy, d_ccy)
forward_curve_file = parent_folder_path + r'\unit_test\data\USDCNY_curve_data_20240325.xlsx'
forward_curve_data = pd.read_excel(forward_curve_file)
forward_curve_data['SettleDate'] = forward_curve_data['SettleDate'].apply(lambda x: ql_date_str(ql_date(x)))
forward_curve = FxForwardCurve(today, spot_f_d, forward_curve_data, f_ccy, d_ccy, forward_calendar, forward_daycount)
## d_curve
d_curve_file = parent_folder_path + r'\unit_test\data\shibor3m_curve_data_20240325.xlsx'
deposit_mkt_data = pd.read_excel(d_curve_file, sheet_name='deposit')
swap_mkt_data = pd.read_excel(d_curve_file, sheet_name='swap')
fixing_data = pd.read_excel(d_curve_file, sheet_name='fixing')
d_curve = Shibor3M(today, deposit_mkt_data=deposit_mkt_data, swap_mkt_data=swap_mkt_data, fixing_data=fixing_data)
## f_curve
f_curve = FxImpliedAssetCurve(today, d_curve, forward_curve, calendar, daycount=ql.Actual365Fixed(), 
                              interpolation_method="zerolinear", tweak=0.0)
## vol_surface
vol_surface_file = parent_folder_path + r'\unit_test\data\USDCNY_vol_data_20240325.xlsx'
vol_surface_data = pd.read_excel(vol_surface_file)
vol_surface = FxVolSurfaceHK(today, vol_surface_data, spot_f_d, d_ccy, f_ccy,
                             forward_curve, d_curve, f_curve, forward_calendar, ql.Actual365Fixed())

valuation(inst, today, forward_curve, d_curve, vol_surface, daycount=ql.Actual365Fixed())


#%%
# pricer example 2
print('\nPricer example 2:')
# trade info
d_ccy = 'CNH'
f_ccy = 'USD'
daycount = ql.Actual365Fixed()
calendar = get_calendar(f_ccy, d_ccy)
expiry = ql.Date(13,11,2024)
payment_date = calendar.advance(expiry, ql.Period(2, ql.Days))
flavor = 'call'
strike = 7.3
notional = 3e4
notional_ccy = 'USD'
trade_direction = 'long'

inst = fx_vanilla.FxVanilla(d_ccy, f_ccy, calendar, expiry, payment_date, flavor, strike,
                            notional, notional_ccy, trade_direction)


# market data
today = ql.Date(9,7,2024)
ql.Settings.instance().evaluationDate = today
spot_f_d = 7.28865
## forward_curve
forward_daycount = ql.Actual365Fixed()
forward_calendar = get_calendar(f_ccy, d_ccy)
forward_curve_file = parent_folder_path + r'\market\curves\market_data\USDCNH_curve_data_20240709.xlsx'
forward_curve_data = pd.read_excel(forward_curve_file)
forward_curve_data['SettleDate'] = forward_curve_data['SettleDate'].apply(lambda x: ql_date_str(ql_date(x)))
forward_curve = FxForwardCurve(today, spot_f_d, forward_curve_data, f_ccy, d_ccy, forward_calendar, forward_daycount)
## f_curve
f_curve_file = parent_folder_path + r'\market\curves\market_data\sofr_curve_data_20240709.xlsx'
swap_mkt_data = pd.read_excel(f_curve_file, sheet_name='swap')
fixing_data = pd.DataFrame()
f_curve = Sofr(today, swap_mkt_data=swap_mkt_data, fixing_data=fixing_data)
## d_curve
d_curve = FxUSDImpliedDiscountCurve(today, d_ccy, f_ccy+d_ccy, spot_f_d, forward_curve_data, forward_calendar,
                                    swap_mkt_data, fixing_data, calendar, daycount)
## vol_surface
vol_surface_file = parent_folder_path + r'\market\volatility\market_data\USDCNH_vol_data_20240709.xlsx'
vol_surface_data = pd.read_excel(vol_surface_file)
vol_surface = FxVolSurfaceHK(today, vol_surface_data, spot_f_d, d_ccy, f_ccy,
                             forward_curve, d_curve, f_curve, forward_calendar, ql.Actual365Fixed())

valuation(inst, today, forward_curve, d_curve, vol_surface, daycount=ql.Actual365Fixed())


#%% 
# pricer example 3
print('\nPricer example 3:')
# trade info
d_ccy = 'USD'
f_ccy = 'EUR'
calendar = get_calendar(f_ccy, d_ccy)
expiry = ql.Date(13,11,2024)
payment_date = calendar.advance(expiry, ql.Period(2, ql.Days))
flavor = 'call'
strike = 1.1
notional = 3e4
notional_ccy = 'EUR'
trade_direction = 'long'

inst = fx_vanilla.FxVanilla(d_ccy, f_ccy, calendar, expiry, payment_date, flavor, strike,
                            notional, notional_ccy, trade_direction)


# market data
today = ql.Date(9,7,2024)
ql.Settings.instance().evaluationDate = today
spot_f_d = 1.0813
## forward_curve
forward_daycount = ql.Actual365Fixed()
forward_calendar = get_calendar(f_ccy, d_ccy)
forward_curve_file = parent_folder_path + r'\market\curves\market_data\EURUSD_curve_data_20240709.xlsx'
forward_curve_data = pd.read_excel(forward_curve_file)
forward_curve_data['SettleDate'] = forward_curve_data['SettleDate'].apply(lambda x: ql_date_str(ql_date(x)))
forward_curve = FxForwardCurve(today, spot_f_d, forward_curve_data, f_ccy, d_ccy, forward_calendar, forward_daycount)
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



