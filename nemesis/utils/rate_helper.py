import numpy as np

from .calendar import Calendar
from .day_count import DayCount
from .schedule import Schedule
from .error import FinError

from .day_count import DayCountTypes
from .calendar import BusDayAdjustTypes


def get_real_fixing_date(fixing_date, cal_type):
    calendar = Calendar(cal_type)
    if not calendar.is_business_day(fixing_date):
        fixing_date = calendar.adjust(fixing_date, bd_type=BusDayAdjustTypes.PRECEDING)
    real_fixing_date = fixing_date
    return real_fixing_date


def get_forward_rate(index_curve, cal_type, today, fixing_date, use_last_fixing=False):
    calendar = Calendar(cal_type)
    if today < index_curve.value_dt:
        raise FinError("Valuation date should not be earlier than curve date!")
    real_fixing_date = get_real_fixing_date(fixing_date, cal_type)
    if real_fixing_date <= today:
        if real_fixing_date <= index_curve.value_dt:
            rate = index_curve.fixing.loc[real_fixing_date.datetime().strftime("%Y%m%d")]["Fixing"]
        else:
            if use_last_fixing:
                last_fixing_date = calendar.adjust(index_curve.value_dt, bd_type=BusDayAdjustTypes.PRECEDING)
                rate = index_curve.fixing.loc[last_fixing_date.datetime().strftime("%Y%m%d")]["Fixing"]
            else:
                real_date = calendar.add_business_days(real_fixing_date, num_days=index_curve.spot_days)
                real_end_date = real_fixing_date.add_business_tenor(index_curve.tenor, cal_type)
                rate = index_curve.fwd_rate(real_date, real_end_date, dc_type=index_curve.dc_type)
    else:
        real_date = calendar.add_business_days(real_fixing_date, num_days=index_curve.spot_days)
        real_end_date = real_date.add_business_tenor(index_curve.tenor, cal_type)
        rate = index_curve.fwd_rate(real_date, real_end_date, dc_type=index_curve.dc_type)
    
    return rate


def get_fixing_rates(index_curve, cal_type, today, fixing_dates, use_last_fixing=False):
    rate_list = []
    for fixing_date in fixing_dates:
        rate = get_forward_rate(index_curve, cal_type, today, fixing_date, use_last_fixing=use_last_fixing)
        rate_list.append(rate)
    return np.array(rate_list)


def get_ois_float_rate(index_curve, fixing_freq_type, cal_type, dc_type, today, start_date, end_date, spread, use_last_fixing=False):
    calendar = Calendar(cal_type)
    day_count = DayCount(dc_type)
    if start_date > today:
        float_rate = index_curve.fwd_rate(start_date, end_date, dc_type)
    else:
        last_reset_date = calendar.add_business_days(end_date, num_days=-1)
        last_fixing_date = get_real_fixing_date(last_reset_date, cal_type)
        if today < last_fixing_date:
            if calendar.adjust(today, bd_type=BusDayAdjustTypes.PRECEDING) == start_date:
                fixed_dates = [today]
            else:
                sch = Schedule(start_date, today, fixing_freq_type, cal_type, bd_type=BusDayAdjustTypes.FOLLOWING)
                fixed_dates = sch.adjusted_dts
            fixed_rates = get_fixing_rates(index_curve, cal_type, today, fixed_dates, use_last_fixing)
            next_reset_date = calendar.add_business_days(today, num_days=1)
            future_forward_rate = index_curve.fwd_rate(next_reset_date, end_date, dc_type=DayCountTypes.ACT_360)
            rate_array = np.append(fixed_rates, future_forward_rate)
            reset_dates = np.append(fixed_dates, [next_reset_date, end_date])
        else:
            if start_date == last_reset_date:
                fixed_dates = [start_date]
            else:
                sch = Schedule(start_date, last_reset_date, fixing_freq_type, cal_type, bd_type=BusDayAdjustTypes.FOLLOWING)
                fixed_dates = sch.adjusted_dts
            rate_array = get_fixing_rates(index_curve, "1D", cal_type, today, fixed_dates, use_last_fixing)
            reset_dates = np.append(fixed_dates, end_date)
        reset_period_dcf = np.array([day_count.year_frac(reset_dates[i], reset_dates[i+1])[0] for i in range(np.size(reset_dates) - 1)])
        float_rate = (np.prod(rate_array * reset_period_dcf + 1) - 1) / np.sum(reset_period_dcf)
    float_rate += spread / 10000.0
    return float_rate


def get_comp_float_rate(index_curve, today, cal_type, fixing_dates, reset_dates, end_date, multiplier, spread, dc_type, compounding_type, use_last_fixing=False):
    day_count = DayCount(dc_type)
    rate_array = get_fixing_rates(index_curve, cal_type, today, fixing_dates, use_last_fixing)
    rate_array *= multiplier
    reset_dates = np.append(reset_dates, end_date)
    reset_period_dcf = np.array([day_count.year_frac(reset_dates[i], reset_dates[i+1]) for i in range(np.size(reset_dates) - 1)])

    if len(rate_array) == 1:
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