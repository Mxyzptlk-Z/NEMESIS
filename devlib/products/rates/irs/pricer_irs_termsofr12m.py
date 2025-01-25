# -*- coding: utf-8 -*-
"""
Created on Thu Sep  5 09:17:42 2024

@author: Guanzhifan
"""

import sys
import os
parant_folder_path = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.realpath(__file__)))))
sys.path.append(parant_folder_path)

import QuantLib as ql
import pandas as pd
import json

from utils.curve_utils import curve_test
from market.curves.cme_term_sofr_curve import CmeTermSofr12M
from products.rates.irs.general_irs import StandardFloatFixedIrs


#%%
today = ql.Date(9, 7, 2024)
ql.Settings.instance().evaluationDate = today

mkt_file_path = parant_folder_path + '/market/curves/market_data/tsfr12m_curve_data_20240709.xlsx'
deposit_mkt_data = pd.read_excel(mkt_file_path, sheet_name='deposit')
base_curve_swap_mkt_data = pd.read_excel(mkt_file_path, sheet_name='base_curve_swap')

tsfr12m_curve = CmeTermSofr12M(today, deposit_mkt_data=deposit_mkt_data,
                             base_curve_swap_mkt_data=base_curve_swap_mkt_data)

print("-----------------------------------------------------")
print('Curve result:')
curve_result = curve_test(tsfr12m_curve)


#%%
index_name = 'TSFR12M'
index_curve = tsfr12m_curve
discount_curve = tsfr12m_curve

ccy = 'USD'
sch_calendar = ql.UnitedStates(ql.UnitedStates.FederalReserve)
fixing_calendar = ql.Sofr().fixingCalendar()
payment_calendar = ql.UnitedStates(ql.UnitedStates.FederalReserve)
date_generation_rule=ql.DateGeneration.Forward
sch_convention=ql.ModifiedFollowing
end_convention=ql.ModifiedFollowing
payment_convention=ql.ModifiedFollowing
fixing_convention=ql.ModifiedPreceding
payment_delay = 2
fixing_days = 2
end_of_month = True

effective_date = ql.Date(26, 7, 2024)
maturity_date = sch_calendar.advance(effective_date, ql.Period('10Y'), sch_convention)
reset_freq = 'None'
notional = 1e7
fixed_rate = 0.05
multiplier = 1
spread = 0
fixed_leg_pay_freq = '12M'
float_leg_pay_freq = '12M'
fixed_leg_daycount = ql.Actual360()
float_leg_daycount = ql.Actual360()
fixed_leg_direction = 'receive'
float_leg_direction = 'pay'

inst = StandardFloatFixedIrs(
    ccy, index_name, effective_date, maturity_date, fixed_leg_pay_freq, 
    float_leg_pay_freq, reset_freq, notional, fixed_rate, multiplier, spread, 
    fixed_leg_daycount, float_leg_daycount, payment_delay, fixing_days, 
    sch_calendar, fixing_calendar, payment_calendar, fixed_leg_direction, float_leg_direction)

npv = inst.npv(today, index_curve, discount_curve)
par = inst.fair_rate(today, index_curve, discount_curve)
dv01_p = inst.dv01_parallel(today, index_curve, discount_curve)
dv01_key = inst.dv01_keytenor(today, index_curve, discount_curve)

print("-----------------------------------------------------")
print('IRS example result:')
print('npv:', npv)
print('par:', par)
print('dv01_parallel:', dv01_p)
print('dv01_keytenor:\n', json.dumps(dv01_key, indent=2))

