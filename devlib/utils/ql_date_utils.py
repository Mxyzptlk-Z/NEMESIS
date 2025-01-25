import QuantLib as ql
import pandas as pd
import numpy as np
import datetime as dt
from typing import Union



def ql_date(date_str: Union[dt.datetime, str, ql.Date], format='%Y-%m-%d'):
    if type(date_str) == ql.Date:
        return date_str
    else:
        return ql.DateParser.parseFormatted(str(date_str), format)
    
    
def ql_date_str(ql_date: ql.Date, format='%Y-%m-%d'):
    
    return ql_date.to_date().strftime(format)



def ql_date_array(dates):
    
    return np.array([ql_date(d) for d in dates])



def get_daycount(daycount_str: str):
    if daycount_str == 'ACT360':
        return ql.Actual360()
    elif daycount_str == 'ACT365':
        return ql.Actual365Fixed()
    elif daycount_str == 'ACTACT':
        return ql.ActualActual(ql.ActualActual.ISDA)
    elif daycount_str == 'EuropeanThirty360':
        return ql.Thirty360(ql.Thirty360.European)
    elif daycount_str == 'BondBasisThirty360':
        return ql.Thirty360(ql.Thirty360.BondBasis)
    elif daycount_str == 'USAThirty360':
        return ql.Thirty360(ql.Thirty360.USA)
    elif daycount_str == 'Term':
        return None
    else:
        raise Exception(f'Unsupported daycount type: {daycount_str}!')
    


def get_year_fraction(daycount:ql.DayCounter, start:ql.Date, end:ql.Date, 
                      day_stub='IncludeFirstExcludeEnd'):
    if daycount == None:
        return 1.0
    elif daycount in [ql.Thirty360(ql.Thirty360.BondBasis), 
                      ql.Thirty360(ql.Thirty360.European),
                      ql.Thirty360(ql.Thirty360.USA)]:
        return daycount.yearFraction(start, end)
    else:
        if day_stub == 'ExcludeFirstExcludeEnd':
            end = end - 1
        elif day_stub == 'IncludeFirstIncludeEnd':
            end = end + 1
        else:
            pass
        return daycount.yearFraction(start, end)
    


def sort_by_ql_period(df: pd.DataFrame, tenor_column: str):
    freq = df[tenor_column].values
    freq_ql = []
    for x in freq:
        if x == 'ON':
            x = '1D'
        elif x == 'TN':
            x = '2D'
        elif x == 'SN':
            x = '3D'
        else:
            pass
        freq_ql.append(ql.Period(x))
    df_ql = df.copy()
    df_ql['tenor_ql_tmp'] = freq_ql
    df_ql = df_ql.sort_values(by='tenor_ql_tmp')
    df_ql.drop(columns='tenor_ql_tmp', axis=1, inplace=True)
    df_ql.reset_index(drop=True, inplace=True)
    
    return df_ql



def sort_tenors(tenors: np.ndarray): 
    ql_peirod_tenors = []
    for x in tenors:
        if x == 'ON':
            x = '1D'
        elif x == 'TN':
            x = '2D'
        elif x == 'SN':
            x = '3D'
        else:
            pass
        ql_peirod_tenors.append(ql.Period(x))
    ql_peirod_tenors = np.array(ql_peirod_tenors)
    
    return tenors[np.argsort(ql_peirod_tenors)]
