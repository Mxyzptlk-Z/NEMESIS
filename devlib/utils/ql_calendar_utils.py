import sys
import os
qcu_path = os.path.dirname(os.path.realpath(__file__))

import QuantLib as ql
import pandas as pd



def calendar_modify(calendar: ql.Calendar, 
                    remove_holidays: list, 
                    add_holidays: list):
    
    for d in remove_holidays:
        ql_date = ql.DateParser.parseFormatted(d, '%Y-%m-%d')
        calendar.removeHoliday(ql_date)

    for d in add_holidays:
        ql_date = ql.DateParser.parseFormatted(d, '%Y-%m-%d')
        calendar.addHoliday(ql_date)   
    


def generate_new_calendar(name: str,
                          weekend_num: list = [1, 7],
                          remove_holidays: list = [], 
                          add_holidays: list = []):
    calendar = ql.BespokeCalendar(name)
    for i in weekend_num:
        calendar.addWeekend(i)
    
    calendar_modify(calendar, remove_holidays, add_holidays)

    return calendar



def joint_calendar(calendar_map: dict, 
                   calendar_names: list, 
                   join_type: int = ql.JoinHolidays):
    if len(calendar_names) == 0:
        raise Exception('No calendar names input!')
    elif len(calendar_names) == 1:
        return calendar_map[calendar_names[0]]
    else:
        calendar = ql.JointCalendar(calendar_map[calendar_names[0]], 
                                    calendar_map[calendar_names[1]], join_type)
        for cld_name in calendar_names[2:]:
            calendar = ql.JointCalendar(calendar, calendar_map[cld_name], join_type)
        
        return calendar



# China IB calendar adjust
china_ib_cld_remove_holidays = []
china_ib_cld_add_holidays = []
calendar_modify(ql.China(ql.China.IB), china_ib_cld_remove_holidays, china_ib_cld_add_holidays)

# South Korea calendar adjust
sk_cld_remove_holidays = ['2024-12-31', '2025-12-31', '2026-05-25', '2026-12-31', '2027-12-27', '2027-12-31', '2028-12-29']
sk_cld_add_holidays = ['2027-03-03', '2028-12-25']
calendar_modify(ql.SouthKorea(), sk_cld_remove_holidays, sk_cld_add_holidays)

# # CFETS FX calendar map
# supported_cfets_ccys = ['CNY', 'USD', 'EUR', 'JPY', 'HKD', 'GBP', 'AUD', 'NZD', 'SGD', 'CHF', 'CAD']
# def get_cfets_fx_calendar_map(ccys):
#     cfets_fx_calendar_map = dict()
#     for ccy in ccys:
#         try:
#             holidays = pd.read_excel('cfets_fx_calendar.xlsx', sheet_name=ccy)
#         except:
#             holidays = pd.read_excel(qcu_path + '/cfets_fx_calendar.xlsx', sheet_name=ccy)

#         holidays['holiday'] = holidays['holiday'].apply(str)
#         holidays = list(holidays['holiday'])
#         weekend_num = [6, 7] if ccy == 'SAR' else [1, 7]
#         ccy_cld = generate_new_calendar(ccy, weekend_num=weekend_num, add_holidays=holidays)
#         cfets_fx_calendar_map[ccy] = ccy_cld
    
#     return cfets_fx_calendar_map

# cfets_fx_calendar_map = get_cfets_fx_calendar_map(supported_cfets_ccys)
    









# class QuantoRACalendar:
    
#     def __init__(self):
        
#         self.calendar = ql.BespokeCalendar('QuantoRACalendar')
        
#         removeList = []
        
#         holidayList = ['2021-01-01',
#                    '2021-12-31',
#                    '2021-02-11',
#                    '2021-02-12',
#                    '2021-02-13',
#                    '2021-02-14',
#                    '2021-02-15',
#                    '2021-02-16',
#                    '2021-02-17',
#                    '2021-04-05',
#                    '2021-05-01',
#                    '2021-05-02',
#                    '2021-05-03',
#                    '2021-05-04',
#                    '2021-05-05',
#                    '2021-06-14',
#                    '2021-09-19',
#                    '2021-09-20',
#                    '2021-09-21',
#                    '2021-10-01',
#                    '2021-10-02',
#                    '2021-10-03',
#                    '2021-10-04',
#                    '2021-10-05',
#                    '2021-10-06',
#                    '2021-10-07',
                   
#                    '2022-01-03',
#                    '2022-01-31',
#                    '2022-02-01',
#                    '2022-02-02',
#                    '2022-02-03',
#                    '2022-02-04',
#                    '2022-02-05',
#                    '2022-02-06',
#                    '2022-04-04',
#                    '2022-04-05',
#                    '2022-05-02',
#                    '2022-05-03',
#                    '2022-05-04',
#                    '2022-06-03',
#                    '2022-09-12',
#                    '2022-10-01',
#                    '2022-10-02',
#                    '2022-10-03',
#                    '2022-10-04',
#                    '2022-10-05',
#                    '2022-10-06',
#                    '2022-10-07']
        
#         for d in removeList:
#             qlDate = ql.DateParser.parseFormatted(d,'%Y-%m-%d')
#             self.calendar.removeHoliday(qlDate)
        
#         for d in holidayList:
#             qlDate = ql.DateParser.parseFormatted(d,'%Y-%m-%d')
#             self.calendar.addHoliday(qlDate)   
            
#         self.calendar.addWeekend(1)
#         self.calendar.addWeekend(7)


# def calendarModifyChina(calendar):
    
#     removeList = ['2021-02-07',
#                   '2021-02-20',
#                   '2021-04-25',
#                   '2021-05-08',
#                   '2021-09-18',
#                   '2021-09-26',
#                   '2021-10-09',
                  
                  
#                   '2022-01-29',
#                   '2022-01-30',
#                   '2022-04-02',
#                   '2022-04-24',
#                   '2022-05-07',
#                   '2022-10-08',
#                   '2022-10-09']
    

#     addList = ['2021-01-01',
#                '2021-12-31',
#                '2021-02-11',
#                '2021-02-12',
#                '2021-02-13',
#                '2021-02-14',
#                '2021-02-15',
#                '2021-02-16',
#                '2021-02-17',
#                '2021-04-05',
#                '2021-05-01',
#                '2021-05-02',
#                '2021-05-03',
#                '2021-05-04',
#                '2021-05-05',
#                '2021-06-14',
#                '2021-09-19',
#                '2021-09-20',
#                '2021-09-21',
#                '2021-10-01',
#                '2021-10-02',
#                '2021-10-03',
#                '2021-10-04',
#                '2021-10-05',
#                '2021-10-06',
#                '2021-10-07',
               

#                '2022-01-03',
#                '2022-01-31',
#                '2022-02-01',
#                '2022-02-02',
#                '2022-02-03',
#                '2022-02-04',
#                '2022-02-05',
#                '2022-02-06',
#                '2022-04-04',
#                '2022-04-05',
#                '2022-05-02',
#                '2022-05-03',
#                '2022-05-04',
#                '2022-06-03',
#                '2022-09-12',
#                '2022-10-01',
#                '2022-10-02',
#                '2022-10-03',
#                '2022-10-04',
#                '2022-10-05',
#                '2022-10-06',
#                '2022-10-07']
    
#     for d in removeList:
#         qlDate = ql.DateParser.parseFormatted(d,'%Y-%m-%d')
#         calendar.removeHoliday(qlDate)
    
#     for d in addList:
#         qlDate = ql.DateParser.parseFormatted(d,'%Y-%m-%d')
#         calendar.addHoliday(qlDate)   
        
#     return calendar
