# -*- coding: utf-8 -*-
"""
Created on Fri Mar 10 15:44:37 2023

@author: xieyushan
"""

import numpy as np
import pandas as pd
import QuantLib as ql
import datetime as dt
from typing import Union



def trs_schedule_ql_trans(schedule):
    schedule.loc[:, 'fixDate'] = [ql.Date().from_date(x) for x in schedule['fixDate']]
    schedule.loc[:, 'startDate'] = [ql.Date().from_date(x) for x in schedule['startDate']]
    schedule.loc[:, 'endDate'] = [ql.Date().from_date(x) for x in schedule['endDate']]
    schedule.loc[:, 'payDate'] = [ql.Date().from_date(x) for x in schedule['payDate']]
    
    return schedule



def ql_date(date_str: Union[dt.datetime, str, ql.Date], format='%Y-%m-%d'):
    if type(date_str) == ql.Date:
        return date_str
    else:
        return ql.DateParser.parseFormatted(str(date_str), format)