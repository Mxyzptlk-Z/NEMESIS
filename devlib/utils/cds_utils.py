# -*- coding: utf-8 -*-
"""
Created on Wed Dec  4 18:37:36 2024

@author: Guanzhifan
"""

import numpy as np
import QuantLib as ql
from utils.ql_calendar_utils import generate_new_calendar


def cds_maturity_date(today, tenor):
    year = today.year()
    if today <= ql.Date(19,3,year):
        ref_date = ql.Date(20,12,year-1)
    elif today <= ql.Date(19,9,year):
        ref_date = ql.Date(20,6,year)
    else:
        ref_date = ql.Date(20,12,year)
    return ref_date + ql.Period(tenor)


def next_adjusted_imm_date(date, calendar):
    year = date.year()
    unadjusted_imm_dates = [ql.Date(20,12,year-1),
                            ql.Date(20,3,year),
                            ql.Date(20,6,year),
                            ql.Date(20,9,year),
                            ql.Date(20,12,year),
                            ql.Date(20,3,year+1)]
    adjusted_imm_dates = [calendar.adjust(date) for date in unadjusted_imm_dates]
    index = np.searchsorted(adjusted_imm_dates, date, side='right')
    return adjusted_imm_dates[index]
        

def adjusted_oldcds_schedule(step_in_date, maturity_date, calendar):
    unadjusted_schedule = ql.Schedule(step_in_date, maturity_date, ql.Period('3M'),
                                      calendar, ql.Following, ql.Unadjusted,
                                      ql.DateGeneration.OldCDS, False).dates()
    compare_schedule_date = unadjusted_schedule[1]
    if (step_in_date + ql.Period('1M') > compare_schedule_date) & (len(unadjusted_schedule) > 2):
        return [unadjusted_schedule[0]] + list(unadjusted_schedule[2:])
    compare_imm_date = next_adjusted_imm_date(step_in_date, calendar)
    if step_in_date + ql.Period('1M') <= compare_imm_date < compare_schedule_date:
        return [unadjusted_schedule[0], compare_imm_date] + list(unadjusted_schedule[1:])
    else:
        return list(unadjusted_schedule)



def calendar_5u(): #2010-2050
    add_holiday_list = ['2022-06-20',
                        '2033-06-20',
                        '2039-06-20',
                        '2044-06-20',
                        '2050-06-20']
    calendar = generate_new_calendar(name='5U', add_holidays=add_holiday_list)
    return calendar


def get_settle_date(today, settle_calendar_type):
    if settle_calendar_type == 'USD':
        settle_calendar = ql.JointCalendar(ql.UnitedStates(ql.UnitedStates.GovernmentBond),
                                           ql.UnitedKingdom())        
    elif settle_calendar_type == 'EUR':
        settle_calendar = ql.JointCalendar(ql.TARGET(),
                                           ql.UnitedKingdom())
    else:
        raise Exception(f'Unsupported settle calendar type: {settle_calendar_type}!')
    settle_date = settle_calendar.advance(today, ql.Period('3D'))
    return settle_date

    
