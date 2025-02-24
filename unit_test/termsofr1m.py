import sys
import os
parant_folder_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(parant_folder_path)

import QuantLib as ql
import pandas as pd

from devlib.market.curves.cme_term_sofr_curve import CmeTermSofr1M
from devlib.products.rates.irs.general_irs import *

from nemesis.products.rates import *

today = ql.Date(9, 7, 2024)
ql.Settings.instance().evaluationDate = today

mkt_file_path = './unit_test/data/tsfr1m_curve_data_20240709.xlsx'
deposit_mkt_data = pd.read_excel(mkt_file_path, sheet_name='deposit')
base_curve_swap_mkt_data = pd.read_excel(mkt_file_path, sheet_name='base_curve_swap')

tsfr1m_curve = CmeTermSofr1M(today, deposit_mkt_data=deposit_mkt_data,
                             base_curve_swap_mkt_data=base_curve_swap_mkt_data)

index_name = 'TSFR1M'
index_curve = tsfr1m_curve
discount_curve = tsfr1m_curve

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
fixed_leg_pay_freq = '1M'
float_leg_pay_freq = '1M'
fixed_leg_daycount = ql.Actual360()
float_leg_daycount = ql.Actual360()
fixed_leg_direction = 'receive'
float_leg_direction = 'pay'

inst = StandardFloatFixedIrs(
    ccy, index_name, effective_date, maturity_date, fixed_leg_pay_freq, 
    float_leg_pay_freq, reset_freq, notional, fixed_rate, multiplier, spread, 
    fixed_leg_daycount, float_leg_daycount, payment_delay, fixing_days, 
    sch_calendar, fixing_calendar, payment_calendar, fixed_leg_direction, float_leg_direction)

npv_dev = inst.npv(today, index_curve, discount_curve)
par_dev = inst.fair_rate(today, index_curve, discount_curve)
dv01_dev = inst.dv01_parallel(today, index_curve, discount_curve)


value_dt = Date(9,7,2024)
curve = QLCurve(value_dt, tsfr1m_curve, dc_type=DayCountTypes.ACT_360, interp_type=InterpTypes.LINEAR_ZERO_RATES)

swap = GeneralSwap(
    effective_dt=Date(26,7,2024),
    term_dt_or_tenor="10Y",
    fixed_leg_type=SwapTypes.RECEIVE,
    fixed_cpn=0.05,
    fixed_freq_type=FrequencyTypes.MONTHLY,
    fixed_dc_type=DayCountTypes.ACT_360,
    notional=1e7,
    payment_lag=2,
    float_multiplier=1,
    float_spread=0,
    float_compounding_type='ExcludeSprd',
    float_freq_type=FrequencyTypes.MONTHLY,
    float_dc_type=DayCountTypes.ACT_360,
    cal_type=CalendarTypes.UNITED_STATES,
    bd_type=BusDayAdjustTypes.MODIFIED_FOLLOWING,
    dg_type=DateGenRuleTypes.FORWARD,
    reset_freq='None',
    fixing_days=2,
    end_of_month= False,
    is_ois_leg=False,
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