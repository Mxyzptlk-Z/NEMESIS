# -*- coding: utf-8 -*-
"""
Created on Thu Oct 30 15:26:09 2025

@author: Liuli5
"""



import sys
import os
parent_folder_path = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.realpath(__file__)))))
sys.path.append(parent_folder_path)

import QuantLib as ql
import pandas as pd
import numpy as np
from devlib.market.curves.pm_curves import PmForwardCurve
from devlib.products.fx import fx_vanilla, fx_digital, fx_range_accrual, fx_knock
from devlib.market.volatility.fx_vol_surface import FxVolSurfaceHK
from devlib.market.volatility.constant_vol_surface import ConstantVolSurface
from devlib.market.curves.fx_curves import FxImpliedAssetCurve
from devlib.market.curves.overnight_index_curves import Sofr
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

# market data
today = ql.Date(11,8,2025)
ql.Settings.instance().evaluationDate = today

# pm forward_curve
d_ccy = 'USD'
f_ccy = 'XAU'
mkt_file_path = parent_folder_path + '/unit_test/data/market_data_fivs_20250811.xlsx'
pm_fwd_data = pd.read_excel(mkt_file_path, sheet_name='precious metal')
pm_fwd_data = pm_fwd_data.loc[pm_fwd_data['TYPE'] == f_ccy+d_ccy, ['TENOR', 'SETTLE_DT', 'PX_LAST']]
pm_fwd_data.columns = ['Tenor', 'SettleDate', 'Rate']
pm_fwd_data.loc[pm_fwd_data.loc[:,'Tenor']!='SPOT', 'Rate'] /= 100
spot = pm_fwd_data.loc[pm_fwd_data.loc[:,'Tenor']=='SPOT', 'Rate'].values[0]
calendar = get_calendar(f_ccy, d_ccy, is_with_usd=True)
fx_fwd_crv = PmForwardCurve(today, spot, pm_fwd_data, f_ccy, d_ccy, calendar=calendar, daycount=ql.Actual365Fixed(), data_type='rate')

# d_curve
mkt_file = parent_folder_path + "/unit_test/data/sofr_curve_data_20250811.xlsx"
swap_mkt_data = pd.read_excel(mkt_file, sheet_name="swap")
fixing_data = pd.read_excel(mkt_file, sheet_name="fixing")
d_crv = Sofr(today, swap_mkt_data=swap_mkt_data, fixing_data=fixing_data)

# f_curve
calendar = get_calendar(f_ccy, d_ccy, is_with_usd=True)
f_crv = FxImpliedAssetCurve(today, d_crv, fx_fwd_crv, calendar, ql.Actual365Fixed())

# vol_surface
vol_file = parent_folder_path + r"\unit_test\data\XAUUSD_voldata_20250811.xlsx"
vol_data = pd.read_excel(vol_file, sheet_name="vol_data")
calendar = get_calendar(f_ccy, d_ccy, is_with_usd=True)
vol_surface = FxVolSurfaceHK(today, vol_data, spot, d_ccy, f_ccy,
                             fx_fwd_crv, d_crv, f_crv, calendar, daycount=ql.Actual365Fixed())

# Dual Currency Note (Cash Settle) / Long Option Note -> vanilla option
d_ccy = 'USD'
f_ccy = 'XAU'
calendar = get_calendar(f_ccy, d_ccy, is_with_usd=True)
expiry = ql.Date(13,11,2025)
payment_date = calendar.advance(expiry, ql.Period(2, ql.Days))
flavor = 'call'
strike = 3200
notional = 1e4
notional_ccy = 'USD'
trade_direction = 'long'

inst = fx_vanilla.FxVanilla(d_ccy, f_ccy, calendar, expiry, payment_date, flavor, strike,
                            notional, notional_ccy, trade_direction)

print('\nPricer example (vanilla):')
valuation(inst, today, fx_fwd_crv, d_crv, vol_surface, daycount=ql.Actual365Fixed())

# Digital Note -> digital option
d_ccy = 'USD'
f_ccy = 'XAU'
calendar = get_calendar(f_ccy, d_ccy, is_with_usd=True)
expiry = ql.Date(13,11,2025)
payment_date = calendar.advance(expiry, ql.Period(2, ql.Days))
flavor = 'call'
strike = 3200
pay_equal = False # 到期时若汇率等于strike，支付cash则为True，否则为False
cash = 3e4
cash_ccy = 'USD'
trade_direction = 'long'
cash_settle = True #本币交割为True，外币交割为False

inst = fx_digital.FxBinary(d_ccy, f_ccy, calendar, expiry, payment_date, flavor, strike,
                            pay_equal, cash, cash_ccy, trade_direction, cash_settle)
print('\nPricer example (binary):')
valuation(inst, today, fx_fwd_crv, d_crv, vol_surface, daycount=ql.Actual365Fixed())

d_ccy = 'USD'
f_ccy = 'XAU'
calendar = get_calendar(f_ccy, d_ccy, is_with_usd=True)
expiry = ql.Date(13,11,2025)
payment_date = calendar.advance(expiry, ql.Period(2, ql.Days))
strike = 3200
left_in = False # 到期时若汇率等于strike，支付coupon_left则为True，支付coupon_right则为False
coupon_left = 3e4
coupon_right = 1e4
cash_ccy = 'USD'
trade_direction = 'long'
cash_settle = True # 本币交割为True，外币交割为False

inst = fx_digital.FxDigital(d_ccy, f_ccy, calendar, expiry, payment_date, strike,
                            left_in, coupon_left, coupon_right, cash_ccy, trade_direction, cash_settle)
print('\nPricer example (digital):')
valuation(inst, today, fx_fwd_crv, d_crv, vol_surface, daycount=ql.Actual365Fixed())

# EKI & EKO Note (Sharkfin) -> knock option
d_ccy = 'USD'
f_ccy = 'XAU'
calendar = get_calendar(f_ccy, d_ccy, is_with_usd=True)
expiry = ql.Date(13,11,2025)
payment_date = calendar.advance(expiry, ql.Period(2, ql.Days))
barrier_type = 'upout'
barrier = 3100
barrier_at_coupon = True #到期时若价格等于barrier，属于coupon情形则为True，属于option情形则为False
flavor = 'put'
strike = 3200
notional = 1e6
notional_ccy = 'USD'
trade_direction = 'long'

inst = fx_knock.FxKnock(d_ccy, f_ccy, calendar, expiry, payment_date,
                        barrier_type, barrier, barrier_at_coupon, flavor, strike,
                        notional, notional_ccy, trade_direction)
vol_surface = ConstantVolSurface(today, 0.15)
print('\nPricer example (knock in/out):')
valuation(inst, today, fx_fwd_crv, d_crv, vol_surface, daycount=ql.Actual365Fixed())

# Range Accrual Note -> range accrual option
d_ccy = 'USD'
f_ccy = 'XAU'
calendar = get_calendar(f_ccy, d_ccy, is_with_usd=True)
start_date = ql.Date(10,11,2025)
end_date = ql.Date(13,11,2025)
obs_end_date = end_date
obs_freq = ql.Period('1D')
obs_schedule = np.array(ql.Schedule(start_date, obs_end_date, obs_freq,
                                    calendar, ql.ModifiedFollowing, ql.ModifiedFollowing,
                                    ql.DateGeneration.Forward, False).dates())
payment_date = calendar.advance(end_date, ql.Period(2, ql.Days))

trade_direction = 'long'
notional = 1e6
cash_ccy = 'USD'
cash_settle = True # 当前默认是cash settle模式，与bbg保持一致

range_down = 3250
down_in = True # 左闭为True，否则为False
range_up = 3350
up_in = True # 右闭为True，否则为False
range_in_coupon_rate = 1
range_out_coupon_rate = 0
range_in_coupon = range_in_coupon_rate * notional
range_out_coupon = range_out_coupon_rate * notional

fx_fixing = pd.Series([spot], index=[today])

inst = fx_range_accrual.FxRangeAccrual(d_ccy, f_ccy, calendar, obs_schedule, payment_date,
                                       range_down, down_in, range_up, up_in,
                                       range_in_coupon, range_out_coupon, cash_ccy, trade_direction, fx_fixing, cash_settle)
vol_surface = ConstantVolSurface(today, 0.15)
print('\nPricer example (range accrual):')
valuation(inst, today, fx_fwd_crv, d_crv, vol_surface, daycount=ql.Actual365Fixed())



