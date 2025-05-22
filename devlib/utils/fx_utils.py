# -*- coding: utf-8 -*-
"""
Created on Tue Mar 21 13:58:41 2023

@author: xieyushan
"""

import QuantLib as ql
import numpy as np
import pandas as pd

from devlib.utils.ql_date_utils import ql_date_str



# fx pair tweak param dict
def get_pair_tweak_param(fx_pair):
    fx_pair_tweak_params = {'USDJPY': 1e2,
                            'JPYUSD': 1e6,
                            'EURJPY': 1e2,
                            'JPYEUR': 1e6,
                            'CNYJPY': 1e2,
                            'JPYCNY': 1e6,
                            'CNHJPY': 1e2,
                            'JPYCNH': 1e6,
                            'USDIDR': 1,
                            'IDRUSD': 1e8,
                            'USDTHB': 1e2,
                            'THBUSD': 1e6,
                            'USDKRW': 1,
                            'KRWUSD': 1e8,
                            'USDTWD': 1,
                            'TWDUSD': 1e8,
                            'HKDJPY': 1e2,
                            'JPYHKD': 1e6,
                            'GBPJPY': 1e2,
                            'JPYGBP': 1e6,
                            'USDINR': 1e2,
                            'INRUSD': 1e6,
                            }
    try:
        return fx_pair_tweak_params[fx_pair]
    except:
        return 1e4

def fx_trans(value: float, 
             value_ccy: str, 
             target_ccy: str, 
             ccy_pair: str, 
             fx_rate: float):   
    if value_ccy == target_ccy:
        return value
    
    else:
        # 模糊匹配CNH/CNY
        value_ccy = value_ccy.replace('CNH', 'CNY')
        target_ccy = target_ccy.replace('CNH', 'CNY')
        ccy_pair = ccy_pair[:3].replace('CNH', 'CNY') + ccy_pair[3:].replace('CNH', 'CNY')
        
        if ccy_pair == value_ccy + target_ccy:
            return value * fx_rate
        elif ccy_pair == target_ccy + value_ccy:
            return value / fx_rate
        else:
            raise Exception(f'Error! ccy_pair: {ccy_pair}, value_ccy: {value_ccy}, target_ccy: {target_ccy}')
    
    
    
# fx currency change
def fx_ccy_trans(value, orig_ccy, fx_rate, fx_pair='None', vague_match_cny_cnh=False):
    if fx_pair == 'None' or fx_pair == 'NONE':
        return value
    else:
        # support CNYCNH or CNHCNY pair
        if not(fx_pair == 'CNYCNH' or fx_pair == 'CNHCNY') and vague_match_cny_cnh:
            orig_ccy = orig_ccy.replace('CNH', 'CNY')
            fx_pair = fx_pair[:3].replace('CNH', 'CNY') + fx_pair[3:].replace('CNH', 'CNY')
            
        if orig_ccy == fx_pair[:3]:
            return value * fx_rate
        else:
            return value / fx_rate

        
def get_ccy_pair(ccy1, ccy2):
    pair1 = ccy1 + ccy2
    pair2 = ccy2 + ccy1

    special_pairs = ['CNHJPY', 'EURCNH', 'HKDCNH', 'USDCAD', 'USDCHF', 'USDCNH',
                     'USDHKD', 'USDIDR', 'USDJPY', 'USDSGD', 'USDTHB', 'USDINR', 
                     'USDNOK', 'USDSEK', 'USDCNY', 'USDKRW', 'USDTWD', 'AUDHKD', 
                     'EURJPY', 'SGDHKD', 'HKDJPY', 'SGDCNH', 'EURGBP', 'USDDKK', 
                     'USDBRL', 'USDPLN', 'USDZAR', 'GBPJPY'] 
    
    if pair1 in special_pairs:
        return pair1
    elif pair2 in special_pairs:
        return pair2
    elif ccy1 == 'USD':
        return pair2
    elif ccy2 == 'USD':
        return pair1
    elif ccy1 == 'CNY':
        return pair2
    elif ccy2 == 'CNY':
        return pair1
    elif ccy1 == 'CNH':
        return pair2
    elif ccy2 == 'CNH':
        return pair1
    else:
        return pair1
    
    
    
def get_trs_fx_spot(
        asset_ccy: str, 
        ccy_pair: str, 
        today: ql.Date, 
        fx_rate_fixing_date: ql.Date, 
        fx_fixings: pd.Series,
        fx_rate_spot: float
        ):
    if fx_rate_fixing_date <= today:
        try:
            fx_rate_spot = fx_fixings.loc[fx_rate_fixing_date]
        except:
            pass
   
    return fx_ccy_trans(1, asset_ccy, fx_rate_spot, ccy_pair, True)



def get_ndirs_fx_fwd(
        ref_ccy: str, 
        today: ql.Date, 
        fx_fixing_date: ql.Date, 
        fx_fixings: pd.Series,
        fx_fwd_crv,
        ):
    ccy_pair = fx_fwd_crv.f_ccy + fx_fwd_crv.d_ccy
    if fx_fixing_date <= today:
        try:
            fx_rate = fx_fixings.loc[fx_fixing_date]
        except:
            fx_rate = fx_fwd_crv.get_forward_spot(fx_fixing_date)
    else:
        fx_rate = fx_fwd_crv.get_forward_spot(fx_fixing_date)
   
    return fx_ccy_trans(1, ref_ccy, fx_rate, ccy_pair, True)



def map_fx_calendar(ccy):
    calendar_map = {'USD': ql.UnitedStates(ql.UnitedStates.FederalReserve), 
                    'CNY': ql.China(ql.China.IB),
                    'JPY': ql.Japan(),
                    'EUR': ql.TARGET(),
                    'IDR': ql.Indonesia(),
                    'GBP': ql.UnitedKingdom(),
                    'THB': ql.Thailand(),
                    'AUD': ql.Australia(),
                    'NZD': ql.NewZealand(),
                    'CAD': ql.Canada(), 
                    'CHF': ql.Switzerland(),
                    'KRW': ql.SouthKorea(),
                    'SGD': ql.Singapore(),
                    'CNH': ql.JointCalendar(ql.China(ql.China.IB), ql.HongKong(), ql.JoinHolidays), 
                    'BRL': ql.Brazil(),
                    'DKK': ql.Denmark(),
                    'PLN': ql.Poland(),
                    'ZAR': ql.SouthAfrica(),
                    'INR': ql.India(),
                    'NOK': ql.Norway(),
                    'SEK': ql.Sweden(),
                    'XAU': ql.UnitedKingdom(ql.UnitedKingdom.Metals),
                    'XAG': ql.UnitedKingdom(ql.UnitedKingdom.Metals),
                    'XPT': ql.UnitedKingdom(ql.UnitedKingdom.Metals),
                    'XPD': ql.UnitedKingdom(ql.UnitedKingdom.Metals), 
                    'X7S': ql.China()
                    }
    if ccy in calendar_map.keys():
        return calendar_map[ccy]
    else:
        return ql.HongKong()



def get_calendar(f_ccy, d_ccy, is_with_usd=False):
    if is_with_usd:
        return ql.JointCalendar(map_fx_calendar(f_ccy),
                                map_fx_calendar(d_ccy),
                                map_fx_calendar('USD'),
                                ql.JoinHolidays)
    else:
        return ql.JointCalendar(map_fx_calendar(f_ccy),
                                map_fx_calendar(d_ccy),
                                ql.JoinHolidays)



def get_spot_settlement_delay(f_ccy, d_ccy):
    special_pairs = ['CADUSD', 'USDCAD']
    
    if f_ccy + d_ccy in special_pairs:
        return 1
    else:
        return 2


def get_spot_settle_dates(f_ccy, d_ccy, today):
    if f_ccy == 'USD':
        calendar1 = get_calendar(d_ccy, d_ccy)
    elif d_ccy == 'USD':
        calendar1 = get_calendar(f_ccy, f_ccy)
    else:
        calendar1 = get_calendar(f_ccy, d_ccy)
    calendar2 = get_calendar(f_ccy, d_ccy, is_with_usd=True)
    
    spot_settlement_delay = get_spot_settlement_delay(f_ccy, d_ccy)
    on_settlement_date = calendar2.advance(today, ql.Period('1D'))
    if spot_settlement_delay == 2:
        tn_settlement_date = calendar2.adjust(calendar1.advance(today, ql.Period('2D')))
        spot_date = tn_settlement_date
        sn_settlement_date = calendar2.advance(spot_date, ql.Period('1D'))
    elif spot_settlement_delay == 1:
        spot_date = on_settlement_date
        sn_settlement_date = calendar2.advance(spot_date, ql.Period('1D'))
        tn_settlement_date = sn_settlement_date
    else:
        raise Exception(f'Unsupported spot settlement delay: {spot_settlement_delay}!')
    spot_dates = {}
    spot_dates['ON'] = on_settlement_date
    spot_dates['TN'] = tn_settlement_date
    spot_dates['SPOT'] = spot_date
    spot_dates['SN'] = sn_settlement_date
    
    return spot_dates



def get_forward_settle_date(f_ccy, d_ccy, spot_date, tenor): 
    if ql.Period(tenor) < ql.Period('1M'):
        convention = ql.Following
        end_of_month = False
    else:
        convention = ql.ModifiedFollowing
        end_of_month = True
    calendar2 = get_calendar(f_ccy, d_ccy, is_with_usd=True)
    
    return calendar2.advance(spot_date, ql.Period(tenor), convention, end_of_month)



def get_fx_all_tenor_settle_dates(f_ccy, d_ccy, today, tenors): 
    spot_dates = get_spot_settle_dates(f_ccy, d_ccy, today)
    spot_date = spot_dates['SPOT']
    all_settle_dates = []
    for tenor in tenors:
        if tenor in spot_dates.keys():
            settle_date = spot_dates[tenor]
        else:
            settle_date = get_forward_settle_date(f_ccy, d_ccy, spot_date, tenor)
        all_settle_dates.append(settle_date)
    
    return pd.Series(all_settle_dates, index=tenors)



def fx_vol_data_trans(vol_data_f_d: pd.DataFrame):
    
    vol_data_d_f = vol_data_f_d.copy()
    vol_data_d_f.loc[vol_data_d_f['Delta Type'].str.endswith('RR'),'Volatility'] *= -1
    
    return vol_data_d_f



def fx_fwd_data_trans(today: ql.Date,
                      spot_f_d: float, 
                      fwd_data_f_d: pd.DataFrame,
                      f_ccy: str,
                      d_ccy: str):

    fwd_data_d_f = fwd_data_f_d.copy()
    fwd_data_d_f['Spread'] = np.nan
    tenors = list(fwd_data_d_f['Tenor'])

    if f_ccy + d_ccy in ['USDCAD', 'CADUSD']:
        tenors_not_after_spot = ['ON', 'SPOT']
    else:
        tenors_not_after_spot = ['ON', 'TN', 'SPOT']
    
    spot_d_f = 1 / spot_f_d
    pair_tweak_param_d_f = get_pair_tweak_param(d_ccy + f_ccy)
    pair_tweak_param_f_d = get_pair_tweak_param(f_ccy + d_ccy)
    
    for idx in fwd_data_d_f.index:
        if fwd_data_f_d.loc[idx, 'Tenor'] not in tenors_not_after_spot:
            fwd_d_f = 1 / (spot_f_d + fwd_data_f_d.loc[idx, 'Spread'] / pair_tweak_param_f_d)
            fwd_point_d_f = fwd_d_f - spot_d_f
            fwd_data_d_f.loc[idx, 'Spread'] = fwd_point_d_f * pair_tweak_param_d_f
    
    fwd_data_d_f.loc[fwd_data_d_f['Tenor']=='SPOT', 'Spread'] = spot_d_f
    
    if (not f_ccy + d_ccy in ['USDCAD', 'CADUSD']) and 'TN' in tenors:
        tn_idx = fwd_data_f_d[fwd_data_f_d['Tenor']=='TN'].index[0]
        tn_spread_f_d = fwd_data_f_d.loc[tn_idx, 'Spread']
        fwd_d_f = 1 / (spot_f_d - tn_spread_f_d / pair_tweak_param_f_d)
        tn_fwd_point_d_f = spot_d_f - fwd_d_f
        fwd_data_d_f.loc[tn_idx, 'Spread'] = tn_fwd_point_d_f * pair_tweak_param_d_f
    else:
        tn_spread_f_d = 0
        tn_fwd_point_d_f = 0
    
    if 'ON' in tenors:
        on_idx = fwd_data_f_d[fwd_data_f_d['Tenor']=='ON'].index[0]
        on_spread_f_d = fwd_data_f_d.loc[on_idx, 'Spread']
        fwd_d_f = 1 / (spot_f_d - (tn_spread_f_d + on_spread_f_d) / pair_tweak_param_f_d)
        on_fwd_point_d_f = spot_d_f - fwd_d_f - tn_fwd_point_d_f
        fwd_data_d_f.loc[on_idx, 'Spread'] = on_fwd_point_d_f * pair_tweak_param_d_f
    else:
        new_row = pd.DataFrame({'Tenor': ['ON'], 'SettleDate': [ql_date_str(today, '%Y-%m-%d')], 'Spread': [0]}) 
        fwd_data_d_f = pd.concat([new_row, fwd_data_d_f]).reset_index(drop=True)
        
    return spot_d_f, fwd_data_d_f



if __name__ == '__main__':
    pass