import sys
import os
parant_folder_path = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.realpath(__file__))))
sys.path.append(parant_folder_path)

import numpy as np
import pandas as pd
import QuantLib as ql

from utils.fx_utils import get_ccy_pair, fx_ccy_trans
from utils.ql_date_utils import ql_date_str
from utils.fx_utils import get_calendar

from products.fx import fx_forward
from market.curves.overnight_index_curves import Sofr
from market.curves.shibor import Shibor3M
from market.curves.flat_rate_curve import FlatRateCurve
from market.curves.fx_curves import FxForwardCurve, FxImpliedAssetCurve
from market.curves.fx_implied_discount_curve import FxUSDImpliedDiscountCurve



def valuation(inst, today, fx_fwd_crv, discount_crv):
    # 模型不提供结算后（包括结算日当天）相关估值
    npv = inst.npv(today, fx_fwd_crv, discount_crv, including_settle=False)
    delta = inst.delta(today, fx_fwd_crv, discount_crv, tweak=1, including_settle=False)
    gamma = inst.gamma(today, fx_fwd_crv, discount_crv)
    theta = inst.theta(today, fx_fwd_crv, discount_crv, tweak=1, including_settle=False)
    
    rho1 = inst.rho(today, fx_fwd_crv, discount_crv, tweak=100, tweak_type='market') * 100
    rho2 = inst.rho(today, fx_fwd_crv, discount_crv, tweak=100, tweak_type='pillar_rate') * 100
    phi1 = inst.phi(today, fx_fwd_crv, discount_crv, tweak=100, tweak_type='market') * 100
    phi2 = inst.phi(today, fx_fwd_crv, discount_crv, tweak=100, tweak_type='pillar_rate') * 100

    print(f'npv: {npv}')
    print(f'delta: {delta}')
    print(f'gamma: {gamma}')
    print(f'theta: {theta}')
    print(f'rho(market): {rho1}')
    print(f'rho(pillar_rate): {rho2}')
    print(f'phi(market): {phi1}')
    print(f'phi(pillar_rate): {phi2}')



#%%
# pricer example1(fx forward, physical settle)
print('\nPricer example1:')

# market data and date setting
today = ql.Date(18, 4, 2023)
ql.Settings.instance().evaluationDate = today

mkt_file_path = parant_folder_path + '\\market\\curves\\market_data\\fx_forward_mkt_data_20230418.xlsx'

##############
# market data
# fx pair
f_ccy = 'EUR'
d_ccy = 'USD'

# spot data
ccypair = f_ccy + d_ccy
spot_data = pd.read_excel(mkt_file_path, sheet_name='FX_spot')
spot = spot_data.loc[0, ccypair]

# fwd curve
fx_fwd_data = pd.read_excel(mkt_file_path, sheet_name=ccypair+'_forwards')
fx_fwd_data['SettleDate'] = fx_fwd_data['SettleDate'].apply(lambda x: x.strftime('%Y-%m-%d'))
if "ON" not in fx_fwd_data["Tenor"].values:
    new_row = pd.DataFrame({'Tenor': ["ON"], 'SettleDate': [ql_date_str(today, '%Y-%m-%d')], 'Spread': [0]}) 
    fx_fwd_data = pd.concat([new_row, fx_fwd_data]).reset_index(drop=True)
fx_calendar = get_calendar(f_ccy, d_ccy)
fwd_daycount = ql.Actual365Fixed()
fx_fwd_crv = FxForwardCurve(today, spot, fx_fwd_data, f_ccy, d_ccy, fx_calendar, fwd_daycount)


# d_ccy curve
curve_name = "Sofr"
swap_mkt_data = pd.read_excel(mkt_file_path, sheet_name=curve_name+'_swap')
fixing_data = pd.read_excel(mkt_file_path, sheet_name=curve_name+'_fixing')
usd_crv = Sofr(today, swap_mkt_data=swap_mkt_data, fixing_data=fixing_data)
# usd_crv = FlatRateCurve(0.05, d_ccy, daycount=ql.Actual365Fixed())


# fx forward example 1.1 (尚未交割)
###############
# product parameter
settle_date = ql.Date(20, 6, 2024)
strike = 1.1
notional_fccy = 1e6
notional_dccy = notional_fccy * strike
flavor_fccy = 'buy'
calendar = get_calendar(f_ccy, d_ccy)

##############
# construct tradable and valuation
inst = fx_forward.FxForward(
    d_ccy, f_ccy, calendar, settle_date, notional_dccy, notional_fccy, flavor_fccy)
print(f'Fx forward of {f_ccy}{d_ccy}(physical settle on {str(settle_date.to_date())}):')
valuation(inst, today, fx_fwd_crv, usd_crv)



#%%
# pricer example2(ndf, cash settle)
print('\nPricer example2:')

# market data and date setting
today = ql.Date(18, 4, 2023)
ql.Settings.instance().evaluationDate = today

mkt_file_path = parant_folder_path + '\\market\\curves\\market_data\\fx_forward_mkt_data_20230418.xlsx'


##############
# market data
# fx pair
f_ccy = 'USD'
d_ccy = 'KRW'

# spot data
ccypair = f_ccy + d_ccy
spot_data = pd.read_excel(mkt_file_path, sheet_name='FX_spot')
spot = spot_data.loc[0, ccypair]

# fwd curve
fx_fwd_data = pd.read_excel(mkt_file_path, sheet_name=ccypair+'_forwards')
fx_fwd_data['SettleDate'] = fx_fwd_data['SettleDate'].apply(lambda x: x.strftime('%Y-%m-%d'))
if "ON" not in fx_fwd_data["Tenor"].values:
    new_row = pd.DataFrame({'Tenor': ["ON"], 'SettleDate': [ql_date_str(today, '%Y-%m-%d')], 'Spread': [0]}) 
    fx_fwd_data = pd.concat([new_row, fx_fwd_data]).reset_index(drop=True)
fx_calendar = get_calendar(f_ccy, d_ccy)
fwd_daycount = ql.Actual365Fixed()
fx_fwd_crv = FxForwardCurve(today, spot, fx_fwd_data, f_ccy, d_ccy, fx_calendar, fwd_daycount)


# d_ccy curve
curve_name = "Sofr"
swap_mkt_data = pd.read_excel(mkt_file_path, sheet_name=curve_name+'_swap')
fixing_data = pd.read_excel(mkt_file_path, sheet_name=curve_name+'_fixing')
base_crv = Sofr(today, swap_mkt_data=swap_mkt_data, fixing_data=fixing_data)
calendar = get_calendar(f_ccy, d_ccy)
daycount = ql.Actual365Fixed()
krw_crv = FxUSDImpliedDiscountCurve(today, d_ccy, f_ccy+d_ccy, spot, fx_fwd_data, calendar,
                                    swap_mkt_data, fixing_data, calendar, daycount)


# krw_crv = FlatRateCurve(0.05, d_ccy, daycount=ql.Actual365Fixed())


# fx forward example 2.1 (尚未定价)
###############
# product parameter
settle_date = ql.Date(20, 6, 2024)
strike = 1300
notional_fccy = 1e6
notional_dccy = notional_fccy * strike
flavor_fccy = 'buy'
calendar = get_calendar(f_ccy, d_ccy)

##############
# construct tradable and valuationpricing_date = calendar.advance(settle_date, ql.Period('-2D')) 
pricing_date = calendar.advance(settle_date, ql.Period('-2D')) 
pricing_fx_rate = None
inst = fx_forward.FxForward(
    d_ccy, f_ccy, calendar, settle_date, notional_dccy, notional_fccy, flavor_fccy, 
    settle_type='cash', settle_ccy=f_ccy, pricing_date=pricing_date, pricing_fx_rate=pricing_fx_rate)
print(f'Fx forward of {f_ccy}{d_ccy}({f_ccy} cash settle on {str(settle_date.to_date())}):')
valuation(inst, today, fx_fwd_crv, krw_crv)


# inst = fx_forward.FxForward(
#     d_ccy, f_ccy, calendar, settle_date, notional_dccy, notional_fccy, flavor_fccy, 
#     settle_type='cash', settle_ccy=d_ccy, pricing_date=pricing_date, pricing_fx_rate=pricing_fx_rate)
# print(f'Fx forward of {f_ccy}{d_ccy}({d_ccy} cash settle on {str(settle_date.to_date())}):')
# valuation(inst, today, fx_fwd_crv, krw_crv)


# fx forward example 2.2 (已定价)
###############
# product parameter
settle_date = ql.Date(20, 4, 2023)
strike = 1300
notional_fccy = 1e6
notional_dccy = notional_fccy * strike
flavor_fccy = 'buy'
calendar = get_calendar(f_ccy, d_ccy)

##############
# construct tradable and valuation
pricing_date = calendar.advance(settle_date, ql.Period('-2D')) 
pricing_fx_rate = 1318.65
inst = fx_forward.FxForward(
    d_ccy, f_ccy, calendar, settle_date, notional_dccy, notional_fccy, flavor_fccy, 
    settle_type='cash', settle_ccy=f_ccy, pricing_date=pricing_date, pricing_fx_rate=pricing_fx_rate)
print(f'Fx forward of {f_ccy}{d_ccy}({f_ccy} cash settle on {str(settle_date.to_date())}):')
valuation(inst, today, fx_fwd_crv, krw_crv)


# inst = fx_forward.FxForward(
#     d_ccy, f_ccy, calendar, settle_date, notional_dccy, notional_fccy, flavor_fccy, 
#     settle_type='cash', settle_ccy=d_ccy, pricing_date=pricing_date, pricing_fx_rate=pricing_fx_rate)
# print(f'Fx forward of {f_ccy}{d_ccy}({d_ccy} cash settle on {str(settle_date.to_date())}):')
# valuation(inst, today, fx_fwd_crv, krw_crv)


#%%
# pricer example3(swap(fx forward), phisical settle)
print('\nPricer example3:')

# market data and date setting
today = ql.Date(18, 4, 2023)
ql.Settings.instance().evaluationDate = today

mkt_file_path = parant_folder_path + '\\market\\curves\\market_data\\fx_forward_mkt_data_20230418.xlsx'

##############
# market data
# fx pair
f_ccy = 'EUR'
d_ccy = 'USD'

# spot data
ccypair = f_ccy + d_ccy
spot_data = pd.read_excel(mkt_file_path, sheet_name='FX_spot')
spot = spot_data.loc[0, ccypair]

# fwd curve
fx_fwd_data = pd.read_excel(mkt_file_path, sheet_name=ccypair+'_forwards')
fx_fwd_data['SettleDate'] = fx_fwd_data['SettleDate'].apply(lambda x: x.strftime('%Y-%m-%d'))
if "ON" not in fx_fwd_data["Tenor"].values:
    new_row = pd.DataFrame({'Tenor': ["ON"], 'SettleDate': [ql_date_str(today, '%Y-%m-%d')], 'Spread': [0]}) 
    fx_fwd_data = pd.concat([new_row, fx_fwd_data]).reset_index(drop=True)
fx_calendar = get_calendar(f_ccy, d_ccy)
fwd_daycount = ql.Actual365Fixed()
fx_fwd_crv = FxForwardCurve(today, spot, fx_fwd_data, f_ccy, d_ccy, fx_calendar, fwd_daycount)


# d_ccy curve
curve_name = "Sofr"
swap_mkt_data = pd.read_excel(mkt_file_path, sheet_name=curve_name+'_swap')
fixing_data = pd.read_excel(mkt_file_path, sheet_name=curve_name+'_fixing')
usd_crv = Sofr(today, swap_mkt_data=swap_mkt_data, fixing_data=fixing_data)
# usd_crv = FlatRateCurve(0.05, d_ccy, daycount=ql.Actual365Fixed())

##############
# product parameter
settle_date_1 = ql.Date(27, 4, 2023)
settle_date_2 = ql.Date(20, 6, 2024)
strike_1 = 1.09
strike_2 = 1.1
flavor_fccy_1 = 'sell'
flavor_fccy_2 = 'buy'
notional = 1e6
notional_dccy_1 = notional * strike_1
notional_fccy_1 = notional
notional_dccy_2 = notional * strike_2
notional_fccy_2 = notional

calendar = get_calendar(f_ccy, d_ccy)

##############
# construct tradable and valuation
inst = fx_forward.FxSwap(d_ccy, f_ccy, calendar, settle_date_1, settle_date_2, 
                         notional_dccy_1, notional_fccy_1, notional_dccy_2, notional_fccy_2, 
                         flavor_fccy_1, flavor_fccy_2)
print(f'\nFx swap of {f_ccy}{d_ccy}(physical settle):')
valuation(inst, today, fx_fwd_crv, usd_crv)
print(f'\nSub fx forward 1 ({str(inst.forward_1.settle_date.to_date())} settle):')
valuation(inst.forward_1, today, fx_fwd_crv, usd_crv)
print(f'\nSub fx forward 2 ({str(inst.forward_2.settle_date.to_date())} settle):')
valuation(inst.forward_2, today, fx_fwd_crv, usd_crv)



#%%
# pricer example4(swap(fx ndf), cash settle)
print('\nPricer example4:')

# market data and date setting
today = ql.Date(18, 4, 2023)
ql.Settings.instance().evaluationDate = today

mkt_file_path = parant_folder_path + '\\market\\curves\\market_data\\fx_forward_mkt_data_20230418.xlsx'


##############
# market data
# fx pair
f_ccy = 'USD'
d_ccy = 'KRW'

# spot data
ccypair = f_ccy + d_ccy
spot_data = pd.read_excel(mkt_file_path, sheet_name='FX_spot')
spot = spot_data.loc[0, ccypair]

# fwd curve
fx_fwd_data = pd.read_excel(mkt_file_path, sheet_name=ccypair+'_forwards')
fx_fwd_data['SettleDate'] = fx_fwd_data['SettleDate'].apply(lambda x: x.strftime('%Y-%m-%d'))
if "ON" not in fx_fwd_data["Tenor"].values:
    new_row = pd.DataFrame({'Tenor': ["ON"], 'SettleDate': [ql_date_str(today, '%Y-%m-%d')], 'Spread': [0]}) 
    fx_fwd_data = pd.concat([new_row, fx_fwd_data]).reset_index(drop=True)
fx_calendar = get_calendar(f_ccy, d_ccy)
fwd_daycount = ql.Actual365Fixed()
fx_fwd_crv = FxForwardCurve(today, spot, fx_fwd_data, f_ccy, d_ccy, fx_calendar, fwd_daycount)


# d_ccy curve
curve_name = "Sofr"
swap_mkt_data = pd.read_excel(mkt_file_path, sheet_name=curve_name+'_swap')
fixing_data = pd.read_excel(mkt_file_path, sheet_name=curve_name+'_fixing')
base_crv = Sofr(today, swap_mkt_data=swap_mkt_data, fixing_data=fixing_data)
calendar = get_calendar(f_ccy, d_ccy)
daycount = ql.Actual365Fixed()
krw_crv = FxUSDImpliedDiscountCurve(today, d_ccy, f_ccy+d_ccy, spot, fx_fwd_data, calendar,
                                    swap_mkt_data, fixing_data, calendar, daycount)
# krw_crv = FlatRateCurve(0.05, d_ccy, daycount=ql.Actual365Fixed())

##############
# product parameter
settle_date_1 = ql.Date(27, 4, 2023)
settle_date_2 = ql.Date(20, 6, 2024)
strike_1 = 1300
strike_2 = 1250
flavor_fccy_1 = 'sell'
flavor_fccy_2 = 'buy'
notional = 1e6
notional_dccy_1 = notional * strike_1
notional_fccy_1 = notional
notional_dccy_2 = notional * strike_2
notional_fccy_2 = notional

calendar = get_calendar(f_ccy, d_ccy)

##############
# construct tradable and valuation

pricing_date_1 = calendar.advance(settle_date_1, ql.Period('-2D')) 
pricing_fx_rate_1 = 1318.65
pricing_date_2 = calendar.advance(settle_date_2, ql.Period('-2D')) 
pricing_fx_rate_2 = None

# inst = fx_forward.FxSwap(d_ccy, f_ccy, calendar, settle_date_1, settle_date_2, 
#                          notional_dccy_1, notional_fccy_1, notional_dccy_2, notional_fccy_2, 
#                          flavor_fccy_1, flavor_fccy_2, settle_type='cash', settle_ccy=d_ccy, 
#                          pricing_date_1=pricing_date_1, pricing_date_2=pricing_date_2, 
#                          pricing_fx_rate_1=pricing_fx_rate_1, pricing_fx_rate_2=pricing_fx_rate_2)
# print(f'\nFx swap of {f_ccy}{d_ccy}({d_ccy} cash settle):')
# valuation(inst, today, fx_fwd_crv, krw_crv)
# print(f'\nSub fx forward 1 ({str(inst.forward_1.settle_date.to_date())} settle):')
# valuation(inst.forward_1, today, fx_fwd_crv, krw_crv)
# print(f'\nSub fx forward 2 ({str(inst.forward_2.settle_date.to_date())} settle):')
# valuation(inst.forward_2, today, fx_fwd_crv, krw_crv)

inst = fx_forward.FxSwap(d_ccy, f_ccy, calendar, settle_date_1, settle_date_2, 
                          notional_dccy_1, notional_fccy_1, notional_dccy_2, notional_fccy_2, 
                          flavor_fccy_1, flavor_fccy_2, settle_type='cash', settle_ccy=f_ccy, 
                          pricing_date_1=pricing_date_1, pricing_date_2=pricing_date_2, 
                          pricing_fx_rate_1=pricing_fx_rate_1, pricing_fx_rate_2=pricing_fx_rate_2)
print(f'\nFx swap of {f_ccy}{d_ccy}({f_ccy} cash settle):')
valuation(inst, today, fx_fwd_crv, krw_crv)
print(f'\nSub fx forward 1 ({str(inst.forward_1.settle_date.to_date())} settle):')
valuation(inst.forward_1, today, fx_fwd_crv, krw_crv)
print(f'\nSub fx forward 2 ({str(inst.forward_2.settle_date.to_date())} settle):')
valuation(inst.forward_2, today, fx_fwd_crv, krw_crv)