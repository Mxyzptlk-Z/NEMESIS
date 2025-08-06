import QuantLib as ql
import numpy as np
import pandas as pd

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.realpath(__file__))))))

from products.general.trs import future_trs

# pricer example1(北向国债期货TRS连接，单期支付，无 funding leg)
print('\nPricer example1:')

# trade info
direction = 'pay' 
qty = 20000
init_price = 102.9375

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

latest_price = 103

# valuation
#默认支付日后该期现金流不计入估值
npv = inst.npv(today, latest_price)
print('npv:', npv)
npv_realized = inst.npv(today, latest_price, is_only_realized=True)
print('npv_realized:', npv_realized)


# pricer example2(北向国债期货TRS对客，单期支付，无 funding leg)
print('\nPricer example2:')

# trade info
direction = 'pay' 
asset_ccy = 'CNY'
settle_ccy = 'USD'
ccy_pair = 'USDCNH'
init_price = 102.9375
qty = 20000


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

latest_price = 103
fx_spot = 7.2

# valuation
#默认支付日后该期现金流不计入估值
npv_settle_ccy = inst.npv(today, latest_price, fx_spot)
print('npv_settle_ccy:', npv_settle_ccy)
npv_settle_ccy_realized = inst.npv(today, latest_price, fx_spot, is_only_realized=True)
print('npv_settle_ccy_realized:', npv_settle_ccy_realized)

npv_asset_ccy = inst.npv_asset_ccy(today, latest_price)
print('npv_asset_ccy:', npv_asset_ccy)
npv_asset_ccy_realized = inst.npv_asset_ccy(today, latest_price, is_only_realized=True)
print('npv_asset_ccy_realized:', npv_asset_ccy_realized)


# pricer example3(南向国债期货TRS连接，单期支付，无 funding leg)
print('\nPricer example3:')

# trade info
direction = 'pay' 
asset_ccy = 'USD'
settle_ccy = 'CNY'
ccy_pair = 'USDCNH' # 根据实际簿记选择
init_price = 1.02749566
qty = 200000


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
today = ql.Date(22, 3, 2024)
ql.Settings.instance().evaluationDate = today

latest_price = 1.03
fx_spot = 7.2

# valuation
#默认支付日后该期现金流不计入估值
npv_settle_ccy = inst.npv(today, latest_price, fx_spot)
print('npv_settle_ccy:', npv_settle_ccy)
npv_settle_ccy_realized = inst.npv(today, latest_price, fx_spot, is_only_realized=True)
print('npv_settle_ccy_realized:', npv_settle_ccy_realized)

npv_asset_ccy = inst.npv_asset_ccy(today, latest_price)
print('npv_asset_ccy:', npv_asset_ccy)
npv_asset_ccy_realized = inst.npv_asset_ccy(today, latest_price, is_only_realized=True)
print('npv_asset_ccy_realized:', npv_asset_ccy_realized)