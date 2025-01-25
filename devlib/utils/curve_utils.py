# -*- coding: utf-8 -*-
"""
Created on Wed Oct 18 13:48:37 2023

@author: xieyushan
"""

import numpy as np
import pandas as pd
import QuantLib as ql

import devlib.utils.ql_date_utils as qdu



def add_fixing(index, calendar, fixing_data, today):
    fixing_data_ql = fixing_data.copy()
    if len(fixing_data_ql) == 0:
        pass
    else:
        fixing_data_ql['Date'] = fixing_data_ql['Date'].apply(lambda x: qdu.ql_date(x))
        for i in fixing_data_ql.index:
            date1 = fixing_data_ql.loc[i, 'Date']
            f = fixing_data_ql.loc[i, 'Fixing']
            tmp_date = date1
            try:
                date2 = fixing_data_ql.loc[i + 1, 'Date']
            except:
                date2 = today
                while tmp_date <= date2:
                    if calendar.isBusinessDay(tmp_date): 
                        index.addFixing(tmp_date, f, True)
                    else:
                        pass
                    tmp_date = calendar.advance(tmp_date, 1, ql.Days)
            else:
                while tmp_date < date2:
                    if calendar.isBusinessDay(tmp_date): 
                        index.addFixing(tmp_date, f, True)
                    else:
                        pass
                    tmp_date = calendar.advance(tmp_date, 1, ql.Days)

    return index



def curve_test(index_curve, tweak=1e-4, bbg_mode=True):
    crv = index_curve.curve
    crv_up = index_curve.tweak_parallel(tweak).curve
    crv_down = index_curve.tweak_parallel(-tweak).curve
    pivot_point = list(crv.dates())
    
    key_dates = []
    zero_rates = []
    dfs = []
    zero_rates_up = []
    zero_rates_down = []
    
    for key_date in pivot_point[1:]:
        df = crv.discount(key_date)
        zero_rate = crv.zeroRate(key_date, ql.Actual365Fixed(), ql.Continuous).rate() * 100
        zero_rate_up = crv_up.zeroRate(key_date, ql.Actual365Fixed(), ql.Continuous).rate() * 100
        zero_rate_down = crv_down.zeroRate(key_date, ql.Actual365Fixed(), ql.Continuous).rate() * 100
        key_date_str = str(key_date.to_date())
        
        key_dates.append(key_date_str)
        if bbg_mode:
            zero_rates.append(round(zero_rate, 5))
            dfs.append(round(df, 6))
        else:
            zero_rates.append(round(zero_rate, 10))
            dfs.append(round(df, 10))
        zero_rates_up.append(round(zero_rate_up, 5))
        zero_rates_down.append(round(zero_rate_down, 5))

    curve_result = pd.DataFrame({'Date': key_dates, 'zero_rate': zero_rates, 'df': dfs, 
                                 'zr_up': zero_rates_up, 'zr_down': zero_rates_down})
    
    print(curve_result)
    
    return curve_result



def get_real_fixing_date(index_curve, fixing_date, product_type='linear'):
    index = index_curve.index
    name = index_curve.name
    calendar = index.fixingCalendar()
    if not calendar.isBusinessDay(fixing_date):
        fixing_date = calendar.adjust(fixing_date, ql.Preceding)
    
    if name in ["LPR1Y", "LPR5Y"]:
        fixing_date_this_month = ql.Date(20, fixing_date.month(), fixing_date.year())
        fixing_date_this_month = calendar.adjust(fixing_date_this_month)
        if fixing_date_this_month <= fixing_date:
            real_fixing_date = fixing_date_this_month
        else:
            fixing_date_ = fixing_date - ql.Period('1M')
            fixing_date_last_month = ql.Date(
                20, fixing_date_.month(), fixing_date_.year())
            fixing_date_last_month = calendar.adjust(fixing_date_last_month)
            real_fixing_date = fixing_date_last_month
        if product_type == 'linear' and real_fixing_date > index_curve.today:
            real_fixing_date = fixing_date
        else:
            pass                                                                                                                                        
    else:
        real_fixing_date = fixing_date

    return real_fixing_date



def get_forward_rate(index_curve, today, fixing_date, use_last_fixing=False, product_type='linear'):
    if today < index_curve.today:
        raise Exception('Valuation date should not be earlier than curve date!')
    
    try:
        rate = index_curve.get_forward_rate(today, fixing_date)
    except:
        index = index_curve.index
        curve= index_curve.curve
        freq = index.tenor()
        calendar = index.fixingCalendar()
        daycount = index.dayCounter()
        convention = index.businessDayConvention()
        end_of_month = index.endOfMonth()
        
        # settlement_delay = 0 
        settlement_delay = index.fixingDays()
        default_compounding_method = ql.Simple
        
        real_fixing_date = get_real_fixing_date(index_curve, fixing_date, product_type=product_type)
            
        if real_fixing_date <= today:
            if real_fixing_date <= index_curve.today:
                # history fixing data exist
                rate = index.fixing(real_fixing_date)
            else:
                # real_fixing_date > index_curve.today, so fixing data does not exist
                if use_last_fixing:
                    last_fixing_date = calendar.adjust(index_curve.today, ql.Preceding)
                    rate = index.fixing(last_fixing_date)
                else:
                    real_date = calendar.advance(
                        real_fixing_date, ql.Period(settlement_delay, ql.Days))
                    real_end_date = calendar.advance(real_date, freq, convention, end_of_month)
                    rate = curve.forwardRate(
                        real_date, real_end_date, daycount, default_compounding_method).rate()
        else:
            real_date = calendar.advance(
                real_fixing_date, ql.Period(settlement_delay, ql.Days))
            real_end_date = calendar.advance(real_date, freq, convention, end_of_month)
            rate = curve.forwardRate(
                real_date, real_end_date, daycount, default_compounding_method).rate()
                
    # print(f'fixing date: {str(fixing_date.to_date())}, reset rate: {rate}')
    
    return rate



def get_fixing_rates(index_curve, today, fixing_dates, use_last_fixing=False, product_type='linear'):
    rate_list = []
    for fixing_date in fixing_dates:
        rate = get_forward_rate(index_curve, today, fixing_date, 
                                use_last_fixing=use_last_fixing, product_type=product_type)
        rate_list.append(rate)
    
    return np.array(rate_list)
    
    

def get_ois_float_rate(index_curve, today, start_date, end_date, daycount, spread, use_last_fixing=False):
    # standard ois采用简便算法
    curve = index_curve.curve
    index = index_curve.index
    index_daycount = index.dayCounter()
    if start_date > today:
        float_rate = curve.forwardRate(
            start_date, end_date, index_daycount, ql.Simple).rate()
    else:
        if index_curve.name == 'SOFR':
            calendar = ql.UnitedStates(ql.UnitedStates.FederalReserve)
        else:
            calendar = index.fixingCalendar()
        
        last_reset_date = calendar.advance(end_date, ql.Period('-1D'))
        last_fixing_date = get_real_fixing_date(index_curve, last_reset_date)
        # 仍有未知的fixing rate
        if today < last_fixing_date:
            if calendar.adjust(today, ql.Preceding) == start_date:
                fixed_dates = np.array([today])
            else:
                fixed_dates = np.array(
                    ql.Schedule(start_date, today, ql.Period('1D'), 
                                calendar, ql.Following, ql.Preceding, 
                                ql.DateGeneration.Forward, False))
            fixed_rates = get_fixing_rates(index_curve, today, fixed_dates, 
                                           use_last_fixing=use_last_fixing)
            next_reset_date = calendar.advance(today, ql.Period('1D'))
            future_forward_rate = curve.forwardRate(
                next_reset_date, end_date, index_daycount, ql.Simple).rate()
            rate_array = np.append(fixed_rates, future_forward_rate)
            reset_dates = np.append(fixed_dates, [next_reset_date, end_date])
        else:
            if start_date == last_reset_date:
                fixed_dates = np.array([start_date])
            else:
                fixed_dates = np.array(
                    ql.Schedule(start_date, last_reset_date, ql.Period('1D'), 
                                calendar, ql.Following, ql.Unadjusted, 
                                ql.DateGeneration.Forward, False))
            rate_array = get_fixing_rates(index_curve, today, fixed_dates, 
                                          use_last_fixing=use_last_fixing)
            reset_dates = np.append(fixed_dates, end_date)
        
        reset_period_dcf = np.array(
            [daycount.yearFraction(reset_dates[i], reset_dates[i+1]) 
                for i in range(np.size(reset_dates) - 1)])
        float_rate = ((np.prod(rate_array * reset_period_dcf + 1) - 1)
                        / np.sum(reset_period_dcf))
    float_rate += spread / 10000.0
    
    return float_rate



def get_comp_float_rate(index_curve, today, fixing_dates, reset_dates, end_date, multiplier, 
                        spread, daycount, compounding_type, use_last_fixing=False, product_type='linear'):
    # get fixed rate and forward rate
    rate_array = get_fixing_rates(index_curve, today, fixing_dates, 
                                  use_last_fixing=use_last_fixing, product_type=product_type)
    # print(rate_array)
    rate_array *= multiplier
    reset_dates = np.append(reset_dates, end_date)
    reset_period_dcf = np.array(
        [daycount.yearFraction(reset_dates[i], reset_dates[i+1]) 
         for i in range(np.size(reset_dates) - 1)])
    
    if len(rate_array) == 1:
        # ibor类 float leg
        float_rate = rate_array[0] + spread / 10000.0
        
    elif compounding_type == 'ExcludeSprd':
        float_rate = ((np.prod(rate_array * reset_period_dcf + 1) - 1) 
                        / np.sum(reset_period_dcf))
        float_rate += spread / 10000.0
        
    elif compounding_type == 'IncludeSprd':
        rate_array = rate_array + spread / 10000.0
        float_rate = ((np.prod(rate_array * reset_period_dcf + 1) - 1)
                        / np.sum(reset_period_dcf))
        
    elif compounding_type == 'Simple':
        float_rate = (np.sum(rate_array * reset_period_dcf)
                        / np.sum(reset_period_dcf))
        float_rate += spread / 10000.0
        
    elif compounding_type == 'Average':
        float_rate = np.mean(rate_array)
        float_rate += spread / 10000.0

    else:
        raise Exception(f'Unsupported compounding type: {compounding_type}')
    
    return float_rate


class OldCurveFunc():
    def __init__(self, curve):
        self.curve = curve[0]
        self.index = curve[1]



def quant_curve_to_fis(curve, daycount=ql.Actual365Fixed()):
    zero_rates = []
    pillar_dates = list(curve.curve.dates())
    try:
        currency = curve.index.currency().code()
    except:
        try:
            currency = curve.ccy
        except:
            raise Exception('Currency info lost!')

    today = curve.today
    if not pillar_dates[0] == today:
        pillar_dates = [today] + pillar_dates
    for date in pillar_dates[1:]:
        year_time = daycount.yearFraction(today, date)
        zero_rates.append((year_time, curve.curve.zeroRate(date, daycount, ql.Continuous).rate()))
    zero_rates = [(0, zero_rates[0][1])] + zero_rates

    curve_info = {'Curve': zero_rates, 'Currency': currency, 'DayCount': daycount.name()}
    
    return curve_info



def fivs_curve_to_fis(today: str, fivs_curve_df, currency: str, calendar: ql.Calendar, 
                      daycount=ql.Actual365Fixed(), tenor_type='tenor'):
    # today and effective date format: 'yyyy-mm-dd'
    today = qdu.ql_date(today)
    if tenor_type == 'tenor':
        effective_dates = [calendar.advance(today, ql.Period(tenor)) 
                           for tenor in fivs_curve_df.loc[:, 'TENOR'].values]
    elif tenor_type == 'effective_date':
        effective_dates = qdu.ql_date_array(fivs_curve_df.loc[:, 'EFFECTIVE_DATE'])
    else:
        raise Exception(f'Wrong tenor type for FIVS: {tenor_type}')

    zero_rates = []
    for date, df in zip(effective_dates, fivs_curve_df.loc[:, 'DISCOUNT_FACTOR']):
        year_time = daycount.yearFraction(today, date)
        zr = -np.log(df) / year_time
        zero_rates.append((year_time, zr))
    zero_rates = [(0, zero_rates[0][1])] + zero_rates

    curve_info = {'Curve': zero_rates, 'Currency': currency, 'DayCount': daycount.name()}

    return curve_info



def commodity_forward_curve_to_fis(base_date, comdty_forward_curve, calendar=ql.UnitedKingdom()):
    tenors = ['1W', '1M', '2M', '3M', '6M', '9M', '12M', '18M', '2Y', '3Y', '4Y', '5Y']
    forward_curve_data = []
    for tenor in tenors:
        date = calendar.advance(base_date, ql.Period(tenor))
        forward_price = comdty_forward_curve.interp_forward_price(date)
        forward_curve_data.append((tenor, forward_price))

    curve_info = {'Base_Date': qdu.ql_date_str(base_date, '%Y%m%d'), 'Curve': forward_curve_data}

    return curve_info



def pm_forward_curve_to_fis(base_date, pm_forward_curve):
    tenors = ['1M', '3M', '6M', '9M', '12M', '2Y']
    calendar = pm_forward_curve.calendar
    spot = pm_forward_curve.spot
    forward_curve_data = []
    for tenor in tenors:
        date = calendar.advance(base_date, ql.Period(tenor))
        try:
            forward_price = spot / pm_forward_curve.curve.discount(date)
        except:
            forward_price = spot
        forward_curve_data.append((tenor, forward_price))

    curve_info = {'Base_Date': qdu.ql_date_str(base_date, '%Y%m%d'), 'Curve': forward_curve_data}

    return curve_info



def credit_curve_to_fis(credit_curve):
    # convert to survival probabilities
    # mock function
    entity = 'IBM'
    survival_probabilities = [
        (0,0),
        (0.63561644,0.001259),
        (1.1369863,0.0036837),
        (2.1369863,0.0094632),
        (3.1369863,0.012523),
        (4.1369863,0.03629287),
        (5.13972603,0.05927358),
        (7.13972603,0.1076301),
        (10.14246575,0.17841482)
        ]
    recovery_rate = 0.4

    curve_info = {'Entity': entity, 'Curve': survival_probabilities, 'Recovery_Rate': recovery_rate}

    return curve_info



if __name__ == '__main__':
    pass
