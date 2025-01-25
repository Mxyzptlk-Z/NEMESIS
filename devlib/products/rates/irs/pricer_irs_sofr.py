import sys
import os
parant_folder_path = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.realpath(__file__)))))
sys.path.append(parant_folder_path)

import QuantLib as ql
import pandas as pd
import json

from utils.curve_utils import curve_test
from market.curves.overnight_index_curves import Sofr
from products.rates.irs.general_irs import *


today = ql.Date(27, 11, 2024)
ql.Settings.instance().evaluationDate = today

mkt_file_path = parant_folder_path + '/market/curves/market_data/sofr_curve_data_20241127.xlsx'
swap_mkt_data = pd.read_excel(mkt_file_path, sheet_name='swap')
fixing_data = pd.read_excel(mkt_file_path, sheet_name='fixing')

index_curve = Sofr(today, swap_mkt_data=swap_mkt_data, fixing_data=fixing_data)
curve_result = curve_test(index_curve)
discount_curve = Sofr(today, swap_mkt_data=swap_mkt_data, fixing_data=fixing_data)


#%% irs example1
ccy = 'USD'
index_name = 'SOFR'
sch_calendar = ql.UnitedStates(ql.UnitedStates.FederalReserve)
fixing_calendar = ql.Sofr().fixingCalendar()    
payment_calendar = ql.UnitedStates(ql.UnitedStates.FederalReserve)
date_generation_rule = ql.DateGeneration.Backward
payment_delay = 0
fixing_days = 0
end_of_month = True
is_ois_leg = True

effective_date = ql.Date(19, 7, 2024)
# maturity_date = sch_calendar.advance(effective_date, ql.Period('1Y'), sch_convention)
maturity_date = ql.Date(18, 7, 2027)
fixed_leg_pay_freq = '1Y'
float_leg_pay_freq = '1Y'
reset_freq = 'None'
notional = 32061781.09
fixed_rate = 0.05558
multiplier = 1
spread = 0
fixed_leg_daycount = ql.Actual360()
float_leg_daycount = ql.Actual360()
fixed_leg_direction = 'pay'
float_leg_direction = 'receive'

inst = StandardFloatFixedIrs(
    ccy, index_name, effective_date, maturity_date, fixed_leg_pay_freq, 
    float_leg_pay_freq, reset_freq, notional, fixed_rate, multiplier, spread, 
    fixed_leg_daycount, float_leg_daycount, payment_delay, fixing_days, 
    sch_calendar, fixing_calendar, payment_calendar, fixed_leg_direction, 
    float_leg_direction, date_generation_rule=date_generation_rule, 
    end_of_month=end_of_month, is_ois_leg=is_ois_leg)

npv = inst.npv(today, index_curve, discount_curve)
# par = inst.fair_rate(today, index_curve, discount_curve)
# dv01_p = inst.dv01_parallel(today, index_curve, discount_curve,tweak=1e-3)

print("-----------------------------------------------------")
print("SOFR example1 result:")
print('npv:', npv)
# print('par:', par)
# print('dv01_parallel:', dv01_p)



#%% irs example2
# ccy = 'USD'
# index_name = 'SOFR'
# sch_calendar = ql.UnitedStates(ql.UnitedStates.FederalReserve)
# fixing_calendar = ql.Sofr().fixingCalendar() 
# payment_calendar = ql.UnitedStates(ql.UnitedStates.FederalReserve)
# date_generation_rule = ql.DateGeneration.Backward
# payment_delay = 0
# fixing_days = 0
# end_of_month = True
# is_ois_leg = True

# effective_date = ql.Date(16, 7, 2024)
# # maturity_date = sch_calendar.advance(effective_date, ql.Period('1Y'), sch_convention)
# maturity_date = ql.Date(15, 7, 2025)
# fixed_leg_pay_freq = '1Y'
# float_leg_pay_freq = '1Y'
# reset_freq = 'None'
# notional = 32051416.02
# fixed_rate = 0.0567
# multiplier = 1
# spread = 0
# fixed_leg_daycount = ql.Actual360()
# float_leg_daycount = ql.Actual360()
# fixed_leg_direction = 'pay'
# float_leg_direction = 'receive'

# inst = StandardFloatFixedIrs(
#     ccy, index_name, effective_date, maturity_date, fixed_leg_pay_freq, 
#     float_leg_pay_freq, reset_freq, notional, fixed_rate, multiplier, spread, 
#     fixed_leg_daycount, float_leg_daycount, payment_delay, fixing_days, 
#     sch_calendar, fixing_calendar, payment_calendar, fixed_leg_direction, 
#     float_leg_direction, date_generation_rule=date_generation_rule, 
#     end_of_month=end_of_month, is_ois_leg=is_ois_leg)

# npv = inst.npv(today, index_curve, discount_curve)
# par = inst.fair_rate(today, index_curve, discount_curve)
# dv01_p = inst.dv01_parallel(today, index_curve, discount_curve)

# print("-----------------------------------------------------")
# print("SOFR example2 result:")
# print('npv:', npv)
# print('par:', par)
# print('dv01_parallel:', dv01_p)

