import sys
import os
parant_folder_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(parant_folder_path)

from devlib.market.curves.ccs_curve import CnyUsdCcsCurve
from devlib.market.curves.overnight_index_curves import Sofr
from devlib.products.rates.irs.general_ccs import StandardFixedFixedCcs
import QuantLib as ql
import pandas as pd
import json

from nemesis.utils import *
from nemesis.products.rates import *
from nemesis.products.rates.xccy_swap import FixedFixedXCcySwap

today = ql.Date(5, 8, 2024)
calendar = ql.JointCalendar(ql.China(ql.China.IB), ql.UnitedStates(ql.UnitedStates.FederalReserve), ql.JoinHolidays)
convention = ql.ModifiedFollowing
valuation_date = today

ql.Settings.instance().evaluationDate = valuation_date

############
pair = 'USDCNY'
fx_spot = 7.1396

# 构建usd discount curve
mkt_file_path = './unit_test/data/sofr_curve_data_20240805.xlsx'
swap_mkt_data = pd.read_excel(mkt_file_path, sheet_name='swap')
sofr_curve = Sofr(today, swap_mkt_data=swap_mkt_data)

# 构建cnh discount curve (cicc ccs curve version)
mkt_file_path =  './unit_test/data/USDCNY_ccs_curve_data_20240805.xlsx'
fx_swap_mkt_data = pd.read_excel(mkt_file_path, sheet_name='fx')
ccs_mkt_data = pd.read_excel(mkt_file_path, sheet_name='ccs')

cny_discount_curve = CnyUsdCcsCurve(today, collateral_index_curve=sofr_curve, collateral_discount_curve=sofr_curve,
                                    ccs_mkt_data=ccs_mkt_data, fx_swap_mkt_data=fx_swap_mkt_data)


start = ql.Date(7, 8, 2024)
expiry = ql.Date(7, 8, 2029)
ccy1, ccy2 = 'CNY', 'USD'
direction1, direction2 = 'receive', 'pay'
notional1, notional2 = 7.1396e6, 1e6
freq1, freq2 = '3M', '6M'
rate1, rate2 = 3e-2, 1e-2
daycount1, daycount2 = ql.Actual365Fixed(), ql.Thirty360(ql.Thirty360.BondBasis)
settlement_ccy = 'CNY'
settlement_delay = 0
initial_notional_ex = True
final_notional_ex = True
notional_pay_delay = 0

############
inst = StandardFixedFixedCcs(
    ccy1, ccy2, settlement_ccy, pair, start, expiry, freq1, freq2, notional1, notional2, 
    rate1, rate2, daycount1, daycount2, settlement_delay, calendar, calendar, direction1, direction2, 
    is_init_notional_ex=initial_notional_ex, is_final_notional_ex=final_notional_ex,
    final_notional_ex_payment_delay=notional_pay_delay)


print('CICC CCS CURVE DISCOUNT VERSION:')
npv = inst.npv(today, cny_discount_curve, sofr_curve, fx_spot)
print('NPV: ', npv)
print('DV01 SETTLE CCY:')
dv01s_settle = inst.dv01s_parallel_settle_ccy(today, cny_discount_curve, sofr_curve, fx_spot)
print(json.dumps(dv01s_settle, indent=2))
dv01s_ori = inst.dv01s_parallel_orig_ccy(today, cny_discount_curve, sofr_curve)
print('DV01 ORI CCY:')
print(json.dumps(dv01s_ori, indent=2))


value_dt = Date(5,8,2024)
cny_curve =  QLCurve(value_dt, cny_discount_curve, dc_type=DayCountTypes.ACT_360, interp_type=InterpTypes.LINEAR_ZERO_RATES, is_index=False)
usd_curve = QLCurve(value_dt, sofr_curve, dc_type=DayCountTypes.ACT_360, interp_type=InterpTypes.LINEAR_ZERO_RATES)

ccs = FixedFixedXCcySwap(
    effective_dt=Date(7,8,2024),
    term_dt_or_tenor=Date(7,8,2029),
    fixed_ccy_1="CNY",
    fixed_ccy_2="USD",
    settle_ccy="CNY",
    fx_pair="USDCNY",
    fixed_leg_type_1=SwapTypes.RECEIVE,
    fixed_leg_type_2=SwapTypes.PAY,
    fixed_cpn_1=3e-2,
    fixed_cpn_2=1e-2,
    fixed_freq_type_1=FrequencyTypes.QUARTERLY,
    fixed_freq_type_2=FrequencyTypes.SEMI_ANNUAL,
    fixed_dc_type_1=DayCountTypes.ACT_365F,
    fixed_dc_type_2=DayCountTypes.THIRTY_360_BOND,
    notional_1=7.1396e6,
    notional_2=1e6,
    payment_lag=0,
    cal_type=JointCalendar([CalendarTypes.CHINA, CalendarTypes.UNITED_STATES]),
    bd_type=BusDayAdjustTypes.MODIFIED_FOLLOWING,
    dg_type=DateGenRuleTypes.FORWARD,
    is_init_notional_ex=True,
    is_final_notional_ex=True
)

npv = ccs.value(value_dt, cny_curve, usd_curve, fx_spot)
print("npv: ", npv)
dv01 = ccs.dv01_settle_ccy(value_dt, cny_curve, usd_curve, tweak=1e-4)
print("dv01: ", dv01)