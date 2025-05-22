import sys
import os
parant_folder_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(parant_folder_path)

import QuantLib as ql
import pandas as pd

from devlib.market.curves.overnight_index_curves import Effr
from devlib.products.rates.irs.general_irs import *

from nemesis.products.rates import *

today = ql.Date(17, 12, 2024)
ql.Settings.instance().evaluationDate = today

mkt_file_path = './unit_test/data/effr_curve_data_20241217.xlsx'
swap_mkt_data_1 = pd.read_excel(mkt_file_path, sheet_name='swap')  # only fed funds ois swap
fixing_data = pd.DataFrame()

index_curve = Effr(today, swap_mkt_data=swap_mkt_data_1, fixing_data=fixing_data)
discount_curve = index_curve

ccy = 'USD'
index_name = 'EFFR'
sch_calendar = ql.UnitedStates(ql.UnitedStates.FederalReserve)
fixing_calendar = ql.UnitedStates(ql.UnitedStates.FederalReserve)   
payment_calendar = ql.UnitedStates(ql.UnitedStates.FederalReserve)
date_generation_rule = ql.DateGeneration.Backward
payment_delay = 2
fixing_days = 0
end_of_month = True
is_ois_leg = True

effective_date = ql.Date(19, 12, 2024)
# maturity_date = sch_calendar.advance(effective_date, ql.Period('1Y'), sch_convention)
maturity_date = ql.Date(19, 12, 2025)
fixed_leg_pay_freq = '1Y'
float_leg_pay_freq = '1Y'
reset_freq = 'None'
notional = 1e10
fixed_rate = 0.042
multiplier = 1
spread = 0
fixed_leg_daycount = ql.Actual360()
float_leg_daycount = ql.Actual360()
fixed_leg_direction = 'receive'
float_leg_direction = 'pay'

inst = StandardFloatFixedIrs(
    ccy, index_name, effective_date, maturity_date, fixed_leg_pay_freq, 
    float_leg_pay_freq, reset_freq, notional, fixed_rate, multiplier, spread, 
    fixed_leg_daycount, float_leg_daycount, payment_delay, fixing_days, 
    sch_calendar, fixing_calendar, payment_calendar, fixed_leg_direction, 
    float_leg_direction, date_generation_rule=date_generation_rule, 
    end_of_month=end_of_month, is_ois_leg=is_ois_leg)

npv_dev = inst.npv(today, index_curve, discount_curve)
par_dev = inst.fair_rate(today, index_curve, discount_curve)
dv01_dev = inst.dv01_parallel(today, index_curve, discount_curve,tweak=1e-4)



value_dt = Date(17,12,2024)
curve = QLCurve(value_dt, index_curve, dc_type=DayCountTypes.ACT_360, interp_type=InterpTypes.LINEAR_ZERO_RATES)

swap = GeneralSwap(
    effective_dt=Date(19,12,2024),
    term_dt_or_tenor=Date(19,12,2025),
    fixed_leg_type=SwapTypes.RECEIVE,
    fixed_cpn=0.042,
    fixed_freq_type=FrequencyTypes.ANNUAL,
    fixed_dc_type=DayCountTypes.ACT_360,
    notional=1e10,
    payment_lag=2,
    float_multiplier=1,
    float_spread=0,
    float_compounding_type='ExcludeSprd',
    float_freq_type=FrequencyTypes.ANNUAL,
    float_dc_type=DayCountTypes.ACT_360,
    cal_type=CalendarTypes.UNITED_STATES,
    bd_type=BusDayAdjustTypes.MODIFIED_FOLLOWING,
    dg_type=DateGenRuleTypes.BACKWARD,
    reset_freq='None',
    fixing_days=0,
    end_of_month= False,
    is_ois_leg=True,
)

npv_val = swap.value(value_dt, curve, curve)
par_val = swap.swap_rate(value_dt, curve, curve)
dv01_val = swap.dv01(value_dt, curve, curve)

result = pd.DataFrame({"NPV": [npv_dev, npv_val], "Par": [par_dev, par_val], "DV01": [dv01_dev, dv01_val]})
result.index = ["FI", "RM"]
result = result.T
result["diff"] = result["FI"] - result["RM"]
result["diff%"] = result["diff"] / result["RM"]
print(result)