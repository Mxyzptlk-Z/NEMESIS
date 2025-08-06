# -*- coding: utf-8 -*-
"""
Created on Wed Sep 20 09:26:52 2023

@author: Liuli5
"""

import QuantLib as ql
import numpy as np
import pandas as pd

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.realpath(__file__))))))

from products.general.trs import future_trs, funding_leg


#%%
# pricer example 1 (非跨境，fixed funding leg)
print('\nPricer example 1:')
underlying = 'SFRZ5'
point_value = 2500

# trade info
direction = 'pay' 
qty = 100
init_price = 96.115
start_date = ql.Date(13, 12, 2024)
expiry_date = ql.Date(13, 2, 2025)
reset_dates = np.array([expiry_date])
payment_dates = np.array([ql.Date(15, 2, 2025)])
ref_prices = pd.Series(dtype=np.float64) 

#funding leg #体现期初手续费（期末支付），平仓费用不计入估值
fundingleg_1_direction = 'receive' 
fundingleg_1_notionals = np.ones(1) * qty * point_value * init_price
fundingleg_1_start_dates = np.array([start_date])
fundingleg_1_end_dates = np.array([expiry_date])
fundingleg_1_payment_dates = np.array([ql.Date(15, 2, 2025)])
fundingleg_1_fixed_rate = 0.0003
fundingleg_1_daycount = None

fundingleg_1 = funding_leg.FixedFundingLeg(
    fundingleg_1_direction, fundingleg_1_notionals, 
    fundingleg_1_start_dates, fundingleg_1_end_dates, fundingleg_1_payment_dates, 
    fundingleg_1_fixed_rate, fundingleg_1_daycount)
funding_legs = {'fundingleg_1': fundingleg_1}

inst = future_trs.FutureTrs(
    direction, qty*point_value, init_price, start_date, expiry_date, 
    reset_dates, payment_dates, ref_prices=ref_prices, funding_legs=funding_legs)

# market data
today = ql.Date(31, 12, 2024)
ql.Settings.instance().evaluationDate = today
latest_price = 96.055

# valuation
npv = inst.npv(today, latest_price, is_only_unsettled=True)
print('npv:', npv)
npv_realized = inst.npv(today, latest_price, is_only_realized=True)
print('npv_realized:', npv_realized)


#%%
# pricer example 2 (跨境，fixed funding leg)
print('\nPricer example 2:')
underlying = 'SFRZ5'
point_value = 2500

# trade info
direction = 'pay' 
qty = 100
init_price = 96.115
start_date = ql.Date(13, 12, 2024)
expiry_date = ql.Date(13, 2, 2025)
reset_dates = np.array([expiry_date])
payment_dates = np.array([ql.Date(15, 2, 2025)])
ref_prices = pd.Series(dtype=np.float64) 

asset_ccy = 'USD'
settle_ccy = 'CNY'
ccy_pair = 'USDCNY'
fx_fixing_dates = reset_dates[:]
fx_fixings = pd.Series(dtype=np.float64) 

#funding leg
fundingleg_1_direction = 'receive' 
fundingleg_1_notionals = np.ones(1) * qty * point_value * init_price
fundingleg_1_start_dates = np.array([start_date])
fundingleg_1_end_dates = np.array([expiry_date])
fundingleg_1_payment_dates = np.array([ql.Date(15, 2, 2025)])
fundingleg_1_fixed_rate = 0.0003
fundingleg_1_daycount = None

fundingleg_1_funding_ccy = 'USD'
fundingleg_1_settle_ccy = 'CNY'
fundingleg_1_ccy_pair = 'USDCNY'
fundingleg_1_fx_fixing_dates = fundingleg_1_end_dates
fundingleg_1_fx_fixings = pd.Series(dtype=np.float64) 

fundingleg_1 = funding_leg.CrossBorderFixedFundingLeg(
    fundingleg_1_direction, fundingleg_1_funding_ccy, fundingleg_1_settle_ccy, 
    fundingleg_1_ccy_pair, fundingleg_1_notionals, fundingleg_1_start_dates,
    fundingleg_1_end_dates, fundingleg_1_payment_dates, fundingleg_1_fx_fixing_dates, 
    fundingleg_1_fixed_rate, fundingleg_1_daycount, fx_fixings=fundingleg_1_fx_fixings)
funding_legs = {'fundingleg_1': fundingleg_1}

inst = future_trs.CrossBorderFutureTrs(
    direction, asset_ccy, settle_ccy, ccy_pair, qty*point_value,
    init_price, start_date, expiry_date, reset_dates, payment_dates,
    fx_fixing_dates, ref_prices=ref_prices, fx_fixings=fx_fixings, funding_legs=funding_legs)


# market data
today = ql.Date(31, 12, 2024)
ql.Settings.instance().evaluationDate = today
latest_price = 96.055
fx_spot = 7.2993

# valuation
npv_settle_ccy = inst.npv(today, latest_price, fx_spot, is_only_unsettled=True)
print('npv_settle_ccy:', npv_settle_ccy)
npv_settle_ccy_realized = inst.npv(today, latest_price, fx_spot, is_only_realized=True)
print('npv_settle_ccy_realized:', npv_settle_ccy_realized)

npv_asset_ccy = inst.npv_asset_ccy(today, latest_price, is_only_unsettled=True)
print('npv_asset_ccy:', npv_asset_ccy)
npv_asset_ccy_realized = inst.npv_asset_ccy(today, latest_price, is_only_realized=True)
print('npv_asset_ccy_realized:', npv_asset_ccy_realized)