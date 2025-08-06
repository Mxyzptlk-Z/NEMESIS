# -*- coding: utf-8 -*-
"""
Created on Wed Nov  6 15:44:39 2024

@author: Guanzhifan
"""


import sys
import os
parent_folder_path = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.realpath(__file__)))))
sys.path.append(parent_folder_path)

import QuantLib as ql
import numpy as np
import pandas as pd

from devlib.market.curves.overnight_index_curves import Sofr, Estr
from devlib.market.curves.credit_curve_generator import MarketDataCreditCurve, CdsConfig
from devlib.products.credit.cds import Cds

from devlib.utils.ql_date_utils import ql_date_str
from devlib.utils.cds_utils import cds_maturity_date, calendar_5u


#%%
def valuation(inst, today, discount_curve, credit_curve, valuation_mode='FI', credit_curve_change=True):
    print(f'\nValuation Date: {ql_date_str(today)}')
    npv = inst.npv(today, discount_curve, credit_curve, valuation_mode)
    print(f'MTM: {npv}')
    dv01_spread = inst.dv01_spread(today, discount_curve, credit_curve, valuation_mode, tweak=1)
    print(f'Spread DV01: {dv01_spread}')
    dv01_ir = inst.dv01_ir(today, discount_curve, credit_curve, valuation_mode, tweak=1e-4, credit_curve_change=credit_curve_change)
    print(f'IR DV01: {dv01_ir}')

def price(inst, today, discount_curve, credit_curve, valuation_mode='FI', settle_date=None, settle_calendar_type='USD'):
    print('\n')
    price_info = inst.price_calculation(today, discount_curve, credit_curve, valuation_mode,
                                        settle_date, settle_calendar_type)
    for i in price_info.keys():
        print(i, price_info[i])
        


#%%
print('\nExample 1: standard, cds index, eur discount')
today = ql.Date(1,11,2024)
ql.Settings.instance().evaluationDate = today

mkt_file_path = parent_folder_path + '/unit_test/data/ICVS530_curve_data_20241101.xlsx'
swap_mkt_data = pd.read_excel(mkt_file_path, sheet_name='swap')
discount_curve = Estr(today, swap_mkt_data=swap_mkt_data)

entity = 'EUROPE'
mkt_file_path = parent_folder_path + '/unit_test/data/credit_curve_data_20241101.xlsx'
cds_type = 'index'
cds_data = pd.read_excel(mkt_file_path, sheet_name=cds_type)

cds_config = CdsConfig(recovery_rate = 0.4,
                        daycount = ql.Actual360(),
                        calendar = ql.WeekendsOnly())
daycount = ql.Actual360()

credit_curve = MarketDataCreditCurve(today, entity, cds_data, discount_curve, cds_type, cds_config, daycount)
print('Credit Curve:')
for date in credit_curve.curve.hazard_rate_series.index:
    print(ql_date_str(date), round(1-credit_curve.curve.survival_probability(date),4))


#%%
tenor = '10Y'
spread = 100

calendar = ql.WeekendsOnly()

effective_date = ql.Date(1,11,2024)
maturity_date = cds_maturity_date(effective_date, tenor)
coupon_schedule = ql.Schedule(ql.Date(20,9,2024), maturity_date, ql.Period('3M'),
                              calendar, ql.Following, ql.Unadjusted,
                              ql.DateGeneration.CDS, False).dates()
coupon_start_dates = np.array(coupon_schedule[:-1])
coupon_end_dates = np.array(coupon_schedule[1:])
coupon_end_dates[:-1] -= 1
coupon_payment_dates = np.array(coupon_schedule[1:])
coupon_payment_dates[-1] = calendar.adjust(coupon_payment_dates[-1])

protection_start_dates = None #等价于np.array([effective_date])
protection_end_dates = None #等价于np.array([maturity_date])

direction = 'long'
notional = 1e7
upfront_amount = 0
upfront_payment_date = ql.Date(6,11,2024)
coupon_pay_front = False
daycount = ql.Actual360()
accrual_coupon_type = 'ToDefaultDate'
accrual_coupon_payment_date_type = 'DefaultDate'
recovery_rate = 0.4
protection_payment_date_type = 'DefaultDate'

inst = Cds(direction, notional, effective_date, maturity_date,
           upfront_amount, upfront_payment_date, coupon_pay_front, spread, daycount,
           coupon_start_dates, coupon_end_dates, coupon_payment_dates,
           accrual_coupon_type, accrual_coupon_payment_date_type,
           protection_start_dates, protection_end_dates, protection_payment_date_type, recovery_rate)


#%%
valuation_mode = 'FI'
valuation(inst, today, discount_curve, credit_curve, valuation_mode, credit_curve_change=True)
price(inst, today, discount_curve, credit_curve, valuation_mode, settle_calendar_type='EUR')

cashflow_schedule = inst.cashflow_schedule(today, discount_curve, credit_curve, valuation_mode)
# cashflow_schedule.to_excel(parent_folder_path + f'/products/credit/cashflow_{cds_type}.xlsx')



#%%
print('\nExample 2: standard, single name cds, usd discount')
today = ql.Date(1,11,2024)
ql.Settings.instance().evaluationDate = today

mkt_file_path = parent_folder_path + '/unit_test/data/ICVS531_curve_data_20241101.xlsx'
swap_mkt_data = pd.read_excel(mkt_file_path, sheet_name='swap')
discount_curve = Sofr(today, swap_mkt_data=swap_mkt_data)

entity = 'CHINAGOV'
mkt_file_path = parent_folder_path + '/unit_test/data/credit_curve_data_20241101.xlsx'
cds_type = 'single_name'
cds_data = pd.read_excel(mkt_file_path, sheet_name=cds_type)

cds_config = CdsConfig(recovery_rate = 0.4,
                        daycount = ql.Actual360(),
                        calendar = calendar_5u())
daycount = ql.Actual360()

credit_curve = MarketDataCreditCurve(today, entity, cds_data, discount_curve, cds_type, cds_config, daycount)
print('Credit Curve:')
for date in credit_curve.curve.hazard_rate_series.index:
    print(ql_date_str(date), round(1-credit_curve.curve.survival_probability(date),4))
    

#%%
tenor = '10Y'
spread = 500

calendar = calendar_5u()

effective_date = ql.Date(1,11,2024)
maturity_date = cds_maturity_date(effective_date, tenor)
coupon_schedule = ql.Schedule(ql.Date(20,9,2024), maturity_date, ql.Period('3M'),
                              calendar, ql.Following, ql.Unadjusted,
                              ql.DateGeneration.CDS, False).dates()
coupon_start_dates = np.array(coupon_schedule[:-1])
# coupon_start_dates[0] = step_in_date
coupon_end_dates = np.array(coupon_schedule[1:])
coupon_end_dates[:-1] -= 1
coupon_payment_dates = np.array(coupon_schedule[1:])
coupon_payment_dates[-1] = calendar.adjust(coupon_payment_dates[-1])

protection_start_dates = None
protection_end_dates = None

direction = 'long'
notional = 1e7
upfront_amount = 0
upfront_payment_date = ql.Date(6,11,2024)
coupon_pay_front = False
daycount = ql.Actual360()
accrual_coupon_type = 'ToDefaultDate'
accrual_coupon_payment_date_type = 'DefaultDate'
recovery_rate = 0.4
protection_payment_date_type = 'DefaultDate'

inst = Cds(direction, notional, effective_date, maturity_date,
           upfront_amount, upfront_payment_date,
           coupon_pay_front, spread, daycount,
           coupon_start_dates, coupon_end_dates, coupon_payment_dates,
           accrual_coupon_type, accrual_coupon_payment_date_type,
           protection_start_dates, protection_end_dates, protection_payment_date_type, recovery_rate)


#%%
valuation_mode = 'FI'
valuation(inst, today, discount_curve, credit_curve, valuation_mode, credit_curve_change=True)
price(inst, today, discount_curve, credit_curve, valuation_mode, settle_calendar_type='USD')

cashflow_schedule = inst.cashflow_schedule(today, discount_curve, credit_curve, valuation_mode)
# cashflow_schedule.to_excel(parent_folder_path + f'/products/credit/cashflow_{cds_type}.xlsx')



#%%
print('\nExample 3: spread=0, single name cds, usd discount')

spread = 0

calendar = calendar_5u()

effective_date = ql.Date(1,11,2024)
maturity_date = ql.Date(1,11,2029)

coupon_start_dates = None
coupon_end_dates = None
coupon_payment_dates = None
protection_start_dates = None
protection_end_dates = None

direction = 'long'
notional = 1e7
upfront_amount = 3e5
upfront_payment_date = ql.Date(6,11,2024)
coupon_pay_front = True
daycount = ql.Actual360()
accrual_coupon_type = 'ToDefaultDate'
accrual_coupon_payment_date_type = 'DefaultDate'
recovery_rate = 0.4
protection_payment_date_type = 'DefaultDate'

inst = Cds(direction, notional, effective_date, maturity_date,
           upfront_amount, upfront_payment_date,
           coupon_pay_front, spread, daycount,
           coupon_start_dates, coupon_end_dates, coupon_payment_dates,
           accrual_coupon_type, accrual_coupon_payment_date_type,
           protection_start_dates, protection_end_dates, protection_payment_date_type, recovery_rate)


#%%
valuation(inst, today, discount_curve, credit_curve, credit_curve_change=True)
price(inst, today, discount_curve, credit_curve, settle_date=ql.Date(6,11,2024))



#%%
print('\nExample 4: pay coupon in advance, no returning, single name cds, usd discount')

spread = 500

calendar = calendar_5u()

effective_date = ql.Date(1,11,2024)
maturity_date = ql.Date(1,11,2029)
coupon_schedule = ql.Schedule(effective_date, maturity_date, ql.Period('3M'),
                              calendar, ql.Following, ql.Unadjusted,
                              ql.DateGeneration.Forward, False).dates()
coupon_start_dates = np.array(coupon_schedule[:-1])
coupon_end_dates = np.array(coupon_schedule[1:])
coupon_end_dates[:-1] -= 1
coupon_payment_dates = coupon_start_dates[:]

protection_start_dates = None
protection_end_dates = None

direction = 'long'
notional = 1e7
upfront_amount = 0
upfront_payment_date = ql.Date(6,11,2024)
coupon_pay_front = True
daycount = ql.Actual360()
accrual_coupon_type = 'ToPeriodEndDate'
accrual_coupon_payment_date_type = 'DefaultDate'
recovery_rate = 0.4
protection_payment_date_type = 'DefaultDate'

inst = Cds(direction, notional, effective_date, maturity_date,
           upfront_amount, upfront_payment_date,
           coupon_pay_front, spread, daycount,
           coupon_start_dates, coupon_end_dates, coupon_payment_dates,
           accrual_coupon_type, accrual_coupon_payment_date_type,
           protection_start_dates, protection_end_dates, protection_payment_date_type, recovery_rate)


#%%
valuation(inst, today, discount_curve, credit_curve, credit_curve_change=True)
price(inst, today, discount_curve, credit_curve, settle_date=ql.Date(6,11,2024))

cashflow_schedule = inst.cashflow_schedule(today, discount_curve, credit_curve)
# cashflow_schedule.to_excel(parent_folder_path + f'/products/credit/cashflow_{cds_type}_PaidInAdvance.xlsx')


#%%
print('\nExample 5: pay coupon in advance, returning part, single name cds, usd discount')

spread = 500

calendar = calendar_5u()

effective_date = ql.Date(1,11,2024)
maturity_date = ql.Date(1,11,2029)
coupon_schedule = ql.Schedule(effective_date, maturity_date, ql.Period('3M'),
                              calendar, ql.Following, ql.Unadjusted,
                              ql.DateGeneration.Forward, False).dates()
coupon_start_dates = np.array(coupon_schedule[:-1])
coupon_end_dates = np.array(coupon_schedule[1:])
coupon_end_dates[:-1] -= 1
coupon_payment_dates = coupon_start_dates[:]

protection_start_dates = None
protection_end_dates = None

direction = 'long'
notional = 1e7
upfront_amount = 0
upfront_payment_date = ql.Date(6,11,2024)
coupon_pay_front = True
daycount = ql.Actual360()
accrual_coupon_type = 'ToDefaultDate'
accrual_coupon_payment_date_type = 'DefaultDate'
recovery_rate = 0.4
protection_payment_date_type = 'DefaultDate'

inst = Cds(direction, notional, effective_date, maturity_date,
           upfront_amount, upfront_payment_date,
           coupon_pay_front, spread, daycount,
           coupon_start_dates, coupon_end_dates, coupon_payment_dates,
           accrual_coupon_type, accrual_coupon_payment_date_type,
           protection_start_dates, protection_end_dates, protection_payment_date_type, recovery_rate)


#%%
valuation(inst, today, discount_curve, credit_curve, credit_curve_change=True)
price(inst, today, discount_curve, credit_curve, settle_date=ql.Date(6,11,2024))

cashflow_schedule = inst.cashflow_schedule(today, discount_curve, credit_curve)
# cashflow_schedule.to_excel(parent_folder_path + f'/products/credit/cashflow_{cds_type}_PaidInAdvance.xlsx')

