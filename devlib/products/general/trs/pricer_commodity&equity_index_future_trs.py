import QuantLib as ql
import numpy as np
import pandas as pd

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.realpath(__file__))))))

from products.general.trs import future_trs, funding_leg

# pricer example1(北向期货TRS连接，单期支付，无 funding leg)
print('\nPricer example1:')

# trade info
direction = 'pay' 
qty = 1800
init_price = 3785.3889

start_date = ql.Date(12, 3, 2024) 
expiry_date = ql.Date(15, 5, 2024) 
reset_dates = np.array([expiry_date])
payment_dates = np.array([ql.Date(15, 5, 2024)])

ref_prices = pd.Series(dtype=np.float64)

inst = future_trs.FutureTrs(
    direction, qty, init_price, start_date, expiry_date, reset_dates, 
    payment_dates, ref_prices=ref_prices)

# market data
today = ql.Date(13, 3, 2024)
ql.Settings.instance().evaluationDate = today

latest_price = 3800

# valuation
#默认重置日后该期现金流不计入估值
npv = inst.npv(today, latest_price, is_only_unsettled=True)
print('npv:', npv)
npv_realized = inst.npv(today, latest_price, is_only_realized=True)
print('npv_realized:', npv_realized)


# pricer example2(北向期货TRS对客，单期支付，年化固定费用funding leg)
print('\nPricer example2:')

# trade info
direction = 'pay' 
asset_ccy = 'CNY'
settle_ccy = 'USD'
ccy_pair = 'USDCNY'
init_price = 3785.3889
qty = 1800


start_date = ql.Date(12, 3, 2024) 
expiry_date = ql.Date(15, 5, 2024) 
reset_dates = np.array([expiry_date])
payment_dates = np.array([ql.Date(17, 5, 2024)])

ref_prices = pd.Series(dtype=np.float64)
fx_fixing_dates = np.array([expiry_date])
fx_fixings = pd.Series(dtype=np.float64) 

# fixed rate
fundingleg_1_direction = "receive" 
fundingleg_1_funding_ccy = 'CNY'
fundingleg_1_settle_ccy = 'USD'
fundingleg_1_ccy_pair = "USDCNY"

fundingleg_1_notionals = np.array([1]) * qty * init_price
fundingleg_1_start_dates = np.array([ql.Date(12, 3, 2024)])
fundingleg_1_end_dates = np.array([ql.Date(15, 5, 2024)])
fundingleg_1_payment_dates = np.array([ql.Date(17, 5, 2024)])
fundingleg_1_fx_fixing_dates = np.array([ql.Date(15, 5, 2024)])
fundingleg_1_fixed_rate = 1/1000
fundingleg_1_daycount = ql.Actual365Fixed()

fundingleg_1_fx_fixings = pd.Series(dtype=np.float64) 

fundingleg_1 = funding_leg.CrossBorderFixedFundingLeg(
    fundingleg_1_direction, fundingleg_1_funding_ccy, fundingleg_1_settle_ccy, 
    fundingleg_1_ccy_pair, fundingleg_1_notionals, fundingleg_1_start_dates,
    fundingleg_1_end_dates, fundingleg_1_payment_dates, fundingleg_1_fx_fixing_dates, 
    fundingleg_1_fixed_rate, fundingleg_1_daycount, fundingleg_1_fx_fixings)

funding_legs = {'fixed rate': fundingleg_1}

# # 开仓费用
# fundingleg_2_direction = "receive" 
# fundingleg_2_funding_ccy = 'CNY'
# fundingleg_2_settle_ccy = 'USD'
# fundingleg_2_ccy_pair = "USDCNY"

# fixed_rate_amount = 100
# fundingleg_2_notionals = np.array([1]) * fixed_rate_amount
# fundingleg_2_start_dates = np.array([ql.Date(17, 5, 2024)]) # 可通过调整start来使得开仓费用是否计入估值
# # fundingleg_2_start_dates = np.array([ql.Date(12, 3, 2024)])
# fundingleg_2_end_dates = np.array([ql.Date(15, 5, 2024)])
# fundingleg_2_payment_dates = np.array([ql.Date(17, 5, 2024)])
# fundingleg_2_fx_fixing_dates = np.array([ql.Date(15, 5, 2024)])
# fundingleg_2_fixed_rate = 1
# fundingleg_2_daycount = None

# fundingleg_2_fx_fixings = pd.Series(dtype=np.float64) 

# fundingleg_2 = funding_leg.CrossBorderFixedFundingLeg(
#     fundingleg_2_direction, fundingleg_2_funding_ccy, fundingleg_2_settle_ccy, 
#     fundingleg_2_ccy_pair, fundingleg_2_notionals, fundingleg_2_start_dates,
#     fundingleg_2_end_dates, fundingleg_2_payment_dates, fundingleg_2_fx_fixing_dates, 
#     fundingleg_2_fixed_rate, fundingleg_2_daycount, fundingleg_2_fx_fixings)

# funding_legs = {'fixed rate amount': fundingleg_1, "fee": fundingleg_2}

inst = future_trs.CrossBorderFutureTrs(
    direction, asset_ccy, settle_ccy, ccy_pair, qty, init_price, start_date, 
    expiry_date, reset_dates, payment_dates, fx_fixing_dates, ref_prices=ref_prices, 
    fx_fixings=fx_fixings, funding_legs=funding_legs)

# market data
today = ql.Date(13, 3, 2024)
ql.Settings.instance().evaluationDate = today

latest_price = 3800
fx_spot = 7.2

# valuation
#默认重置日后该期现金流不计入估值
npv_settle_ccy = inst.npv(today, latest_price, fx_spot, is_only_unsettled=True)
print('npv_settle_ccy:', npv_settle_ccy)
npv_settle_ccy_realized = inst.npv(today, latest_price, fx_spot, is_only_realized=True)
print('npv_settle_ccy_realized:', npv_settle_ccy_realized)

npv_asset_ccy = inst.npv_asset_ccy(today, latest_price, is_only_unsettled=True)
print('npv_asset_ccy:', npv_asset_ccy)
npv_asset_ccy_realized = inst.npv_asset_ccy(today, latest_price, is_only_realized=True)
print('npv_asset_ccy_realized:', npv_asset_ccy_realized)


# pricer example3(南向期货TRS连接，单期支付，无 funding leg)
print('\nPricer example3:')

# trade info
direction = 'pay' 
asset_ccy = 'USD'
settle_ccy = 'CNY'
ccy_pair = 'USDCNH' # 根据实际簿记选择
init_price = 3785.3889
qty = 1800


start_date = ql.Date(12, 3, 2024) 
expiry_date = ql.Date(15, 5, 2024) 
reset_dates = np.array([expiry_date])
payment_dates = np.array([ql.Date(15, 5, 2024)])

ref_prices = pd.Series(dtype=np.float64)
fx_fixing_dates = np.array([expiry_date])
fx_fixings = pd.Series(dtype=np.float64) 

inst = future_trs.CrossBorderFutureTrs(
    direction, asset_ccy, settle_ccy, ccy_pair, qty, init_price, start_date, 
    expiry_date, reset_dates, payment_dates, fx_fixing_dates, ref_prices=ref_prices, 
    fx_fixings=fx_fixings)

# market data
today = ql.Date(13, 3, 2024)
ql.Settings.instance().evaluationDate = today

latest_price = 3800
fx_spot = 7.2

# valuation
#默认重置日后该期现金流不计入估值
npv_settle_ccy = inst.npv(today, latest_price, fx_spot, is_only_unsettled=True)
print('npv_settle_ccy:', npv_settle_ccy)
npv_settle_ccy_realized = inst.npv(today, latest_price, fx_spot, is_only_realized=True)
print('npv_settle_ccy_realized:', npv_settle_ccy_realized)

npv_asset_ccy = inst.npv_asset_ccy(today, latest_price, is_only_unsettled=True)
print('npv_asset_ccy:', npv_asset_ccy)
npv_asset_ccy_realized = inst.npv_asset_ccy(today, latest_price, is_only_realized=True)
print('npv_asset_ccy_realized:', npv_asset_ccy_realized)


#%%
# pricer example 4(option trs，非跨境，不含funding leg，asset端单期支付)
print('\nPricer example4: ')

underlying_ticker = 'CLZ4C 80.00 COMB Comdty'

# trade info
direction = 'pay' 
qty = 1e3
init_price = 0.70
start_date = ql.Date(18,10,2024)
expiry_date = ql.Date(20,1,2025)
reset_dates = np.array([expiry_date])
payment_dates = np.array([ql.Date(22,1,2025)])

ref_prices = pd.Series(dtype=np.float64)  #asset端单期支付则默认与init_price比较

inst = future_trs.FutureTrs(
    direction, qty, init_price, start_date, expiry_date, reset_dates, 
    payment_dates, ref_prices=ref_prices)


# market data
today = ql.Date(23,10,2024)
ql.Settings.instance().evaluationDate = today

latest_price = 1

# valuation
#默认重置日后该期现金流不计入估值
npv = inst.npv(today, latest_price, is_only_unsettled=True)
print('npv:', npv)
npv_realized = inst.npv(today, latest_price, is_only_realized=True)
print('npv_realized:', npv_realized)


###############################################################################
# pricer example 5(option trs，跨境，不含funding leg，asset端单期支付)
print('\nPricer example5:')

underlying_ticker = 'CLZ4C 80.00 COMB Comdty'

# trade info
asset_ccy = 'USD'
settle_ccy = 'CNY'
ccy_pair = 'USDCNY'

direction = 'pay' 
qty = 1e3
init_price = 0.70
start_date = ql.Date(18,10,2024)
expiry_date = ql.Date(20,1,2025)
reset_dates = np.array([expiry_date])
payment_dates = np.array([ql.Date(22,1,2025)])

ref_prices = pd.Series(dtype=np.float64)  #asset端单期支付则默认与init_price比较

fx_fixing_dates = reset_dates
fx_fixings = pd.Series(dtype=np.float64)

inst = future_trs.CrossBorderFutureTrs(
    direction, asset_ccy, settle_ccy, ccy_pair, qty, init_price, start_date, expiry_date, reset_dates, 
    payment_dates, fx_fixing_dates, ref_prices=ref_prices, fx_fixings=fx_fixings)


# market data
today = ql.Date(23,10,2024)
ql.Settings.instance().evaluationDate = today

latest_price = 1
fx_spot = 7.1263

# valuation
#默认重置日后该期现金流不计入估值
npv_settle_ccy = inst.npv(today, latest_price, fx_spot, is_only_unsettled=True)
print('npv_settle_ccy:', npv_settle_ccy)
npv_settle_ccy_realized = inst.npv(today, latest_price, fx_spot, is_only_realized=True)
print('npv_settle_ccy_realized:', npv_settle_ccy_realized)

npv_asset_ccy = inst.npv_asset_ccy(today, latest_price, is_only_unsettled=True)
print('npv_asset_ccy:', npv_asset_ccy)
npv_asset_ccy_realized = inst.npv_asset_ccy(today, latest_price, is_only_realized=True)
print('npv_asset_ccy_realized:', npv_asset_ccy_realized)
