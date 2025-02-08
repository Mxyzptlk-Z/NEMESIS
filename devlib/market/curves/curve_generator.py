from abc import abstractmethod
from typing import Union

import QuantLib as ql
import pandas as pd
import numpy as np
import copy
from math import exp

import devlib.utils.curve_utils as cu
from devlib.utils.ql_date_utils import ql_date



class IndexConfig:
    def __init__(self):
        pass


    @abstractmethod
    def build_index(self):
        pass


    @abstractmethod
    def build_index_with_curve_ts(self, curve_ts: ql.YieldTermStructureHandle):
        pass



class IborIndexConfig(IndexConfig):
    def __init__(
            self, 
            curve_name: str, 
            tenor: str, 
            settlement_delay: int, 
            currency: ql.Currency, 
            calendar: ql.Calendar, 
            convention: int, 
            end_of_month: bool, 
            daycount: ql.DayCounter, 
            ):
        self.curve_name = curve_name
        self.tenor = tenor
        self.settlement_delay = settlement_delay
        self.currency = currency
        self.calendar = calendar
        self.convention = convention
        self.end_of_month = end_of_month
        self.daycount = daycount
        

    def build_index(self):
        index = ql.IborIndex(
            self.curve_name, ql.Period(self.tenor), self.settlement_delay, self.currency, 
            self.calendar, self.convention, self.end_of_month, self.daycount)
        
        return index
    
    
    def build_index_with_curve_ts(self, curve_ts: ql.YieldTermStructureHandle): 
        index = ql.IborIndex(
            self.curve_name, ql.Period(self.tenor), self.settlement_delay, self.currency, 
            self.calendar, self.convention, self.end_of_month, self.daycount, curve_ts)
        
        return index



class GeneralOvernightIndexConfig(IndexConfig):
    def __init__(
            self, 
            curve_name: str, 
            settlement_delay: int, 
            currency: ql.Currency, 
            calendar: ql.Calendar, 
            daycount: ql.DayCounter, 
            ):
        self.curve_name = curve_name
        self.settlement_delay = settlement_delay
        self.currency = currency
        self.calendar = calendar
        self.daycount = daycount
        
    
    def build_index(self):
        index = ql.OvernightIndex(
            self.curve_name, self.settlement_delay, self.currency, 
            self.calendar, self.daycount)
        
        return index
    
    
    def build_index_with_curve_ts(self, curve_ts: ql.YieldTermStructureHandle): 
        index = ql.OvernightIndex(
            self.curve_name, self.settlement_delay, self.currency, 
            self.calendar, self.daycount, curve_ts)        
        return index            
    
    

class OvernightIndexConfig(IndexConfig):
    def __init__(
            self, 
            curve_name: str, 
            ois_index_class, 
            ):
        self.ois_index_class = ois_index_class
        
        self.curve_name = curve_name
        self.settlement_delay = self.ois_index_class().fixingDays()
        self.currency = self.ois_index_class().currency()
        self.calendar = self.ois_index_class().fixingCalendar()
        self.daycount = self.ois_index_class().dayCounter()
    

    def build_index(self):
        index = self.ois_index_class()
        return index
        
    
    def build_index_with_curve_ts(self, curve_ts: ql.YieldTermStructureHandle): 
        index = self.ois_index_class(curve_ts)        
        return index         



class DepositHelperConfig:
    def __init__(
            self, 
            settlement_delay: int, 
            calendar: ql.Calendar, 
            convention: int, 
            end_of_month: bool, 
            daycount: ql.DayCounter, 
            ):
        self.settlement_delay = settlement_delay
        self.calendar = calendar
        self.convention = convention
        self.end_of_month = end_of_month
        self.daycount = daycount
        
    
    @abstractmethod
    def build_deposit_helper(
            self, 
            curve_name: str, 
            currency: ql.Currency, 
            tenor: str, 
            rate: float, 
            ):
        index = ql.IborIndex(
            curve_name, ql.Period(tenor), self.settlement_delay, currency, 
            self.calendar, self.convention, self.end_of_month, self.daycount)
        hp = ql.DepositRateHelper(ql.QuoteHandle(ql.SimpleQuote(rate)), index)
        
        return hp
        
        
        
class SwapRateHelperConfig:
    def __init__(
            self, 
            calendar: ql.Calendar, 
            fixed_pay_freq: int, 
            fixed_convention: int, 
            fixed_daycount: ql.DayCounter, 
            spread: float, 
            forward_start: int, 
            end_of_month: bool, 
            ):
        self.calendar = calendar
        self.fixed_pay_freq = fixed_pay_freq
        self.fixed_convention = fixed_convention
        self.fixed_daycount = fixed_daycount
        self.spread = spread
        self.forward_start = forward_start
        self.end_of_month = end_of_month
        
    
    @abstractmethod
    def build_swap_helper(
            self, 
            tenor: str, 
            rate: float, 
            index: ql.Index, 
            ):
        hp = ql.SwapRateHelper(
            ql.QuoteHandle(ql.SimpleQuote(rate)), ql.Period(tenor), self.calendar, 
            self.fixed_pay_freq, self.fixed_convention, self.fixed_daycount, index, 
            ql.QuoteHandle(ql.SimpleQuote(self.spread)), 
            ql.Period(str(self.forward_start) + 'D'),
            ql.YieldTermStructureHandle(), index.fixingDays(), 
            ql.Pillar.LastRelevantDate, ql.Date(), self.end_of_month)
        
        return hp



class OisRateHelperConfig:
    def __init__(
            self, 
            settlement_delay: int,
            calendar: ql.Calendar, 
            payment_lag:int, 
            payment_freq: int, 
            payment_convention: int, 
            spread: float, 
            forward_start: int, 
            ):
        self.settlement_delay = settlement_delay
        self.calendar = calendar
        self.payment_lag = payment_lag
        self.payment_freq = payment_freq
        self.payment_convention = payment_convention
        self.spread = spread
        self.forward_start = forward_start
        
    
    @abstractmethod
    def build_swap_helper(
            self, 
            tenor: str, 
            rate: float, 
            index: ql.Index, 
            ):
  
        if ql.Period(tenor) > ql.Period(self.payment_freq):
            pillar_date_type = ql.Pillar.LastRelevantDate
        else:
            pillar_date_type = ql.Pillar.MaturityDate
        hp = ql.OISRateHelper(
            self.settlement_delay, ql.Period(tenor), 
            ql.QuoteHandle(ql.SimpleQuote(rate)), index,
            ql.YieldTermStructureHandle(), True, self.payment_lag,
            self.payment_convention, self.payment_freq, self.calendar,
            ql.Period(str(self.forward_start) + 'D'),
            self.spread, pillar_date_type, ql.Date())   
        return hp



class GeneralFraHelperConfig:
    def __init__(
            self, 
            settlement_delay: int, 
            calendar: ql.Calendar, 
            convention: int, 
            end_of_month, 
            daycount: ql.DayCounter,
            ):
        self.settlement_delay = settlement_delay
        self.calendar = calendar
        self.convention = convention
        self.end_of_month = end_of_month
        self.daycount = daycount
        
    
    def build_fra_helper(
            self, 
            rate: float, 
            month_to_start: int, 
            month_to_end:int
            ):
        hp = ql.FraRateHelper(
            ql.QuoteHandle(ql.SimpleQuote(rate)), 
            int(month_to_start), int(month_to_end), self.settlement_delay, 
            self.calendar, self.convention, self.end_of_month, 
            self.daycount, ql.Pillar.LastRelevantDate, ql.Date(), True)
        
        return hp



class FraHelperConfig:
    def __init__(
            self, 
            index_class,
            ):
        self.index_class = index_class
        
    
    def build_fra_helper(
            self, 
            rate: float, 
            month_to_start: int, 
            month_to_end:int
            ):
        hp = ql.FraRateHelper(
            ql.QuoteHandle(ql.SimpleQuote(rate)), 
            int(month_to_start), self.index_class(), 
            ql.Pillar.LastRelevantDate, ql.Date(), True)
        
        return hp
    
    

class FutureHelperConfig:
    def __init__(
            self, 
            calendar: ql.Calendar, 
            convention: int, 
            end_of_month: bool, 
            daycount: ql.DayCounter, 
            futures_type: int = ql.Futures.IMM, 
            ):
        self.calendar = calendar
        self.convention = convention
        self.end_of_month = end_of_month
        self.daycount = daycount
        self.futures_type = futures_type

    
    @abstractmethod
    def build_future_helper( 
            self, 
            price: float, 
            ibor_start_date: ql.Date, 
            cvx_adj: float, 
            input_type: str, 
            **args, 
            ):
        if input_type == 'index':
            index = args[input_type]
            hp = ql.FuturesRateHelper(
                price, ibor_start_date, index, cvx_adj, self.futures_type)
        
        elif input_type == 'lenth_in_month':
            lenth_in_months = args[input_type]
            hp = ql.FuturesRateHelper(
                price, ibor_start_date, lenth_in_months, self.calendar, self.convention, 
                self.end_of_month, self.daycount, cvx_adj, self.futures_type)
        
        elif input_type == 'ibor_end_date':
            ibor_end_date = args[input_type]
            hp = ql.FuturesRateHelper(
                price, ibor_start_date, ibor_end_date, self.daycount, 
                cvx_adj, self.futures_type)
        
        return hp
    
    
    # @staticmethod
    # def cvx_adj_cal_bbg(
    #         price: float, 
    #         today: ql.Date, 
    #         settle_date: ql.Date, 
    #         start_date: ql.Date, 
    #         end_date: ql.Date, 
    #         daycount: ql.DayCounter, 
    #         k: float, 
    #         vol: float, 
    #         ):
    #     # t = 0
    #     T = daycount.yearFraction(today, start_date)
    #     tao = daycount.yearFraction(start_date, end_date)
    #     tf = daycount.yearFraction(today, settle_date)
        
    #     sigma_c = vol ** 2 / (2 * k ** 3) * (exp(-k * T) - exp(-k * (T + tao))) * (
    #         exp(k * tf) - 1) * (2 - exp(-k * (T + tao - tf)) - exp(-k * (T + tao)))
    #     future_rate = (100 - price) / 100
    #     act_rate = ((1 + future_rate * tao) * exp(-sigma_c) - 1) / tao
        
    #     return future_rate - act_rate
    
    
    # @staticmethod
    # def cvx_adj_cal_bbg_v2(
    #         price: float, 
    #         analysis_date: ql.Date, 
    #         start_date: ql.Date, 
    #         end_date: ql.Date, 
    #         daycount: ql.DayCounter, 
    #         k: float, 
    #         vol: float, 
    #         ):
    #     T1 = daycount.yearFraction(analysis_date, start_date)
    #     T1_2 = daycount.yearFraction(start_date, end_date)
    #     B1 = (1 - exp(-k * T1)) / k
    #     B1_2 = (1 - exp(-k * T1_2)) / k
    #     X = (vol ** 2 / (2 * k)) * B1_2 * (B1_2 * (1 - exp(-2 * k * T1)) + k * (B1 ** 2))
        
    #     future_rate = (100 - price) / 100
    #     cvx_adj = (1 - exp(-X)) * (future_rate + 1 / T1_2)

    #     return cvx_adj
    
        

class GeneralCurveGenerator: 
    def __init__(
            self, 
            index_config: IndexConfig,
            deposit_config: Union[DepositHelperConfig, None], 
            swap_config: Union[SwapRateHelperConfig, None], 
            fra_config: Union[FraHelperConfig, None],  
            future_config: Union[FutureHelperConfig, None], 
            interpolation_method: str = 'PiecewiseLinearZero', 
            ):  
        self.index_config = index_config
        self.deposit_config = deposit_config
        self.swap_config = swap_config
        self.fra_config = fra_config
        self.future_config = future_config
        self.interpolation_method = interpolation_method
        
    
    def build_deposit_helpers(self, deposit_mkt_data: Union[pd.DataFrame, None]):
        if self.deposit_config == None:
            deposit_helpers = []
        else:
            deposit_helpers = [self.deposit_config.build_deposit_helper( 
                self.index_config.curve_name, self.index_config.currency, 
                deposit_mkt_data.loc[idx, 'Tenor'], deposit_mkt_data.loc[idx, 'Rate']) 
                for idx in deposit_mkt_data.index]
        
        return deposit_helpers    
    
    
    def build_swap_helpers(self, swap_mkt_data: Union[pd.DataFrame, None]):
        if self.swap_config == None:
            swap_helpers = []
        else:
            swap_index = self.index_config.build_index()
            swap_helpers = [self.swap_config.build_swap_helper(
                swap_mkt_data.loc[idx, 'Tenor'], swap_mkt_data.loc[idx, 'Rate'], 
                swap_index) for idx in swap_mkt_data.index]  
        
        return swap_helpers
    
    
    def build_fra_helpers(self, fra_mkt_data: Union[pd.DataFrame, None]):
        if self.fra_config == None:
            fra_helpers = []
        else:
            fra_helpers = [self.fra_config.build_fra_helper( 
                fra_mkt_data.loc[idx, 'Rate'], 
                fra_mkt_data.loc[idx, 'MonthStart'], 
                fra_mkt_data.loc[idx, 'MonthEnd'],) 
                for idx in fra_mkt_data.index]
        
        return fra_helpers
    
    
    def build_future_helpers(self, future_mkt_data: Union[pd.DataFrame, None]):
        if self.future_config == None:
            future_helpers = []
        else:
            future_helpers = []
            for idx in future_mkt_data.index:
                price = future_mkt_data.loc[idx, 'Price']
                # k = future_mkt_data.loc[idx, 'K']
                # vol = future_mkt_data.loc[idx, 'Vol']
                # settle_date = ql_date(future_mkt_data.loc[idx, 'LastTradeDate'])
                start_date = ql_date(future_mkt_data.loc[idx, 'StartDate'])
                end_date = ql_date(future_mkt_data.loc[idx, 'EndDate'])
                future_helpers.append(self.future_config.build_future_helper(
                    price, start_date, 0.0, input_type='ibor_end_date', 
                    ibor_end_date=end_date))
                # end_date = self.future_config.calendar.advance(
                #     start_date, ql.Period(self.index_config.tenor), 
                #     self.index_config.convention, self.index_config.end_of_month)
                # cvx_adj = self.future_config.cvx_adj_cal_bbg(
                #     price, today, settle_date, start_date, end_date, 
                #     self.index_config.daycount, k, vol)
                # analysis_date = self.index_config.calendar.advance(
                #     today, self.index_config.settlement_delay, ql.Days)
                # cvx_adj_2 = self.future_config.cvx_adj_cal_bbg_v2(
                #     price, analysis_date, start_date, end_date, 
                #     self.index_config.daycount, k, vol)
                # contract_code = future_mkt_data.loc[idx, 'Contract']
                # print(f'{contract_code}: {np.round(cvx_adj*100, 5)}')
                # print(f'{contract_code}: {np.round(cvx_adj_2*100, 5)}')
                # future_helpers.append(self.future_config.build_future_helper(
                #     price, start_date, cvx_adj_2, input_type='ibor_end_date', 
                #     ibor_end_date=end_date))
                # future_helpers.append(self.future_config.build_future_helper(
                #     price, start_date, cvx_adj_2, input_type='lenth_in_month', 
                #     ibor_end_date=end_date, lenth_in_month=3))
        
        return future_helpers
    
    
    def build_all_helpers(
            self, 
            deposit_mkt_data: Union[pd.DataFrame, None], 
            swap_mkt_data: Union[pd.DataFrame, None], 
            fra_mkt_data: Union[pd.DataFrame, None], 
            future_mkt_data: Union[pd.DataFrame, None], 
            ):
        deposit_helpers = self.build_deposit_helpers(deposit_mkt_data)
        swap_helpers = self.build_swap_helpers(swap_mkt_data)
        fra_helpers = self.build_fra_helpers(fra_mkt_data)
        future_helpers = self.build_future_helpers(future_mkt_data)                
        helpers = deposit_helpers + swap_helpers + fra_helpers + future_helpers
        
        return helpers
    
    
    def build_curve(
            self, 
            today: ql.Date, 
            deposit_mkt_data: Union[pd.DataFrame, None], 
            swap_mkt_data: Union[pd.DataFrame, None], 
            fra_mkt_data: Union[pd.DataFrame, None],
            future_mkt_data: Union[pd.DataFrame, None], 
            fixing_data: pd.DataFrame, 
            ):
        helpers = self.build_all_helpers(deposit_mkt_data, swap_mkt_data, fra_mkt_data, future_mkt_data)        

        if self.interpolation_method == 'PiecewiseLinearZero':
            curve = ql.PiecewiseLinearZero(today, helpers, ql.Actual360())
        else:
            raise Exception(
                f'unsupported curve interpolation method: {self.interpolation_method}')
            
        curve.enableExtrapolation()
        
        curve_ts = ql.YieldTermStructureHandle(curve)
        index = self.index_config.build_index_with_curve_ts(curve_ts)
        # add fixing
        index = cu.add_fixing(index, self.index_config.calendar, fixing_data, today)

        return curve, index
       


class GeneralCurve:
    def __init__(
            self, 
            today: ql.Date, 
            deposit_mkt_data: Union[pd.DataFrame, None] = None, 
            swap_mkt_data: Union[pd.DataFrame, None] = None, 
            fra_mkt_data: Union[pd.DataFrame, None] = None,
            future_mkt_data: Union[pd.DataFrame, None] = None,
            fixing_data: pd.DataFrame = pd.DataFrame(), 
            interpolation_method: str = 'PiecewiseLinearZero', 
            ):
        self.curve_config_set()
        self.name = self.index_config.curve_name
        self.ccy = self.index_config.currency.code()
        
        self.today = today
        
        self.deposit_mkt_data = copy.copy(deposit_mkt_data)
        self.swap_mkt_data = copy.copy(swap_mkt_data)
        self.fra_mkt_data = copy.copy(fra_mkt_data)
        self.future_mkt_data = copy.copy(future_mkt_data)
        self.fixing_data = copy.copy(fixing_data)
        self.interpolation_method = interpolation_method
        
        self.curve, self.index = self.build_curve()
    
        
    @abstractmethod    
    def curve_config_set(self):
        self.index_config = IndexConfig()
        self.deposit_config = None
        self.swap_config = None
        self.fra_config = None
        self.future_config = None, 
        self.curve_generator_config = GeneralCurveGenerator

        
    def build_curve(self):
        curve_generator = self.curve_generator_config(
            self.index_config, self.deposit_config, self.swap_config, self.fra_config, 
            self.future_config, self.interpolation_method)
        curve, index = curve_generator.build_curve(
            self.today, self.deposit_mkt_data, self.swap_mkt_data, self.fra_mkt_data, 
            self.future_mkt_data, self.fixing_data)
        
        return curve, index
    
    
    def get_all_keytenor(self):
        try:
            deposit_tenors = self.deposit_mkt_data.loc[:, 'Tenor'].values
        except:
            deposit_tenors = []
        
        try:
            swap_tenors = self.swap_mkt_data.loc[:, 'Tenor'].values
        except:
            swap_tenors = []
        
        try:
            fra_tenors = self.fra_mkt_data.loc[:, 'Tenor'].values
        except:
            fra_tenors = []
        
        try:
            future_tenors = self.future_mkt_data.loc[:, 'Contract'].values
        except:
            future_tenors = []
            
        return deposit_tenors, swap_tenors, fra_tenors, future_tenors
    
    
    def mkt_data_tweak(self, data_type: str, tweak: float, tenor: str):
        if data_type == 'deposit':
            if not type(self.deposit_mkt_data) == type(None):
                deposit_mkt_data_tweaked = self.deposit_mkt_data.copy()
                if tenor == 'ALL':
                    deposit_mkt_data_tweaked['Rate'] += tweak
                else:
                    deposit_mkt_data_tweaked.loc[
                        deposit_mkt_data_tweaked.loc[:, 'Tenor'] == tenor, 'Rate'] += tweak
                return deposit_mkt_data_tweaked
            else:
                return None
        
        elif data_type == 'swap':
            if not type(self.swap_mkt_data) == type(None):
                swap_mkt_data_tweaked = self.swap_mkt_data.copy()
                if tenor == 'ALL':
                    swap_mkt_data_tweaked['Rate'] += tweak
                else:
                    swap_mkt_data_tweaked.loc[
                        swap_mkt_data_tweaked.loc[:, 'Tenor'] == tenor, 'Rate'] += tweak
                return swap_mkt_data_tweaked
            else:
                return None
            
        elif data_type == 'fra':
            if not type(self.fra_mkt_data) == type(None):
                fra_mkt_data_tweaked = self.fra_mkt_data.copy()
                if tenor == 'ALL':
                    fra_mkt_data_tweaked['Rate'] += tweak
                else:
                    fra_mkt_data_tweaked.loc[
                        fra_mkt_data_tweaked.loc[:, 'Tenor'] == tenor, 'Rate'] += tweak
                return fra_mkt_data_tweaked
            else:
                return None
        
        elif data_type == 'future':
            if not type(self.future_mkt_data) == type(None):
                future_mkt_data_tweaked = self.future_mkt_data.copy()
                if tenor == 'ALL':
                    future_mkt_data_tweaked['Price'] -= tweak * 100
                else:
                    future_mkt_data_tweaked.loc[
                        future_mkt_data_tweaked.loc[:, 'Contract'] == tenor, 
                        'Price'] -= tweak * 100
                return future_mkt_data_tweaked
            else:
                return None
        
        elif data_type == 'fixing':
            if not type(self.fixing_data) == type(None):
                fixing_data_tweaked = self.fixing_data.copy()
                fixing_data_tweaked['Fixing'] += tweak
                return fixing_data_tweaked
            else:
                return None            
        
        else:
            raise Exception(f'unsupported data type: {data_type}')

    
    def tweak_keytenor(self, tweak, tenor='ALL'):
        deposit_tenors, swap_tenors, fra_tenors, future_tenors = self.get_all_keytenor()
        deposit_mkt_data_ = copy.copy(self.deposit_mkt_data)
        swap_mkt_data_ = copy.copy(self.swap_mkt_data)
        fra_mkt_data_ = copy.copy(self.fra_mkt_data)
        future_mkt_data_ = copy.copy(self.future_mkt_data)
        fixing_data_ = copy.copy(self.fixing_data)
        
        if tenor == 'ALL':
            all_tweaked_curves = dict()
            for tenor in deposit_tenors:
                deposit_mkt_data = self.mkt_data_tweak('deposit', tweak, tenor)
                curve_tweak = self.__class__(
                    self.today, deposit_mkt_data, swap_mkt_data_, 
                    fra_mkt_data_, future_mkt_data_, fixing_data_)
                all_tweaked_curves[tenor] = curve_tweak
            
            for tenor in swap_tenors:
                swap_mkt_data = self.mkt_data_tweak('swap', tweak, tenor)
                curve_tweak = self.__class__(
                    self.today, deposit_mkt_data_, swap_mkt_data, 
                    fra_mkt_data_, future_mkt_data_, fixing_data_)
                all_tweaked_curves[tenor] = curve_tweak
                
            for tenor in fra_tenors:
                fra_mkt_data = self.mkt_data_tweak('fra', tweak, tenor)
                curve_tweak = self.__class__(
                    self.today, deposit_mkt_data_, swap_mkt_data_, 
                    fra_mkt_data, future_mkt_data_, fixing_data_)
                all_tweaked_curves[tenor] = curve_tweak
                
            for tenor in future_tenors:
                future_mkt_data = self.mkt_data_tweak('future', tweak, tenor)
                curve_tweak = self.__class__(
                    self.today, deposit_mkt_data_, swap_mkt_data_, 
                    fra_mkt_data_, future_mkt_data, fixing_data_)
                all_tweaked_curves[tenor] = curve_tweak

            return all_tweaked_curves
            
        elif tenor in deposit_tenors:
            deposit_mkt_data = self.mkt_data_tweak('deposit', tweak, tenor)
            curve_tweak = self.__class__(
                self.today, deposit_mkt_data, swap_mkt_data_, 
                fra_mkt_data_, future_mkt_data_, fixing_data_)
            return curve_tweak
        
        elif tenor in swap_tenors:
            swap_mkt_data = self.mkt_data_tweak('swap', tweak, tenor)
            curve_tweak = self.__class__(
                self.today, deposit_mkt_data_, swap_mkt_data, 
                fra_mkt_data_, future_mkt_data_, fixing_data_)
            return curve_tweak
        
        elif tenor in fra_tenors:
            fra_mkt_data = self.mkt_data_tweak('fra', tweak, tenor)
            curve_tweak = self.__class__(
                self.today, deposit_mkt_data_, swap_mkt_data_, 
                fra_mkt_data, future_mkt_data_, fixing_data_)
            return curve_tweak
        
        elif tenor in future_tenors:
            future_mkt_data = self.mkt_data_tweak('future', tweak, tenor)
            curve_tweak = self.__class__(
                self.today, deposit_mkt_data_, swap_mkt_data_, 
                fra_mkt_data_, future_mkt_data, fixing_data_)
            return curve_tweak
        
        else:
            raise Exception(f'Invalid tenor: {tenor}!') 
    
    
    def tweak_parallel(self, tweak):
        deposit_mkt_data_tweaked = self.mkt_data_tweak('deposit', tweak, 'ALL')
        swap_mkt_data_tweaked = self.mkt_data_tweak('swap', tweak, 'ALL')
        fra_mkt_data_tweaked = self.mkt_data_tweak('fra', tweak, 'ALL')
        future_mkt_data_tweaked = self.mkt_data_tweak('future', tweak, 'ALL')
        
        curve_tweak = self.__class__(
            self.today, deposit_mkt_data_tweaked, swap_mkt_data_tweaked, 
            fra_mkt_data_tweaked, future_mkt_data_tweaked, self.fixing_data)
        
        return curve_tweak
    

    def tweak_discount_curve(self, tweak, tweak_daycount=ql.Actual365Fixed(), tweak_type='zerolinear'):
        curve_tweak = copy.copy(self)
        calendar = self.index_config.calendar
        if tweak_type == 'zerolinear':
            dfs = []
            dates = list(self.curve.dates())
            for date in dates:
                df = self.curve.discount(date)
                dcf = tweak_daycount.yearFraction(self.today, date)
                df *= np.exp(-tweak * dcf)    
                dfs.append(df)

            zeros = [-np.log(df) / tweak_daycount.yearFraction(self.today, date) 
                     for df, date in zip(dfs[1:], dates[1:])]
            zeros = [zeros[0]] + zeros
            curve = ql.ZeroCurve(dates, zeros, tweak_daycount, calendar)
        else:
            raise Exception(f'Unsupported discount curve tweak type: {tweak_type}!')
        
        curve.enableExtrapolation()
        curve_tweak.curve = curve
        curve_ts = ql.YieldTermStructureHandle(curve)
        curve_tweak.index = self.index_config.build_index_with_curve_ts(curve_ts)
        
        return curve_tweak
    
    
    
def curve_tweak_keytenor(curve_type, orig_curve, tweak, tenor='ALL'):
    deposit_tenors, swap_tenors, fra_tenors, future_tenors = orig_curve.get_all_keytenor()
    deposit_mkt_data_ = copy.copy(orig_curve.deposit_mkt_data)
    swap_mkt_data_ = copy.copy(orig_curve.swap_mkt_data)
    fra_mkt_data_ = copy.copy(orig_curve.fra_mkt_data)
    future_mkt_data_ = copy.copy(orig_curve.future_mkt_data)
    fixing_data_ = copy.copy(orig_curve.fixing_data)
    
    if tenor == 'ALL':
        all_tweaked_curves = dict()
        for tenor in deposit_tenors:
            deposit_mkt_data = orig_curve.mkt_data_tweak('deposit', tweak, tenor)
            curve_tweak = curve_type(
                orig_curve.today, deposit_mkt_data, swap_mkt_data_, 
                fra_mkt_data_, future_mkt_data_, fixing_data_)
            all_tweaked_curves[tenor] = curve_tweak
        
        for tenor in swap_tenors:
            swap_mkt_data = orig_curve.mkt_data_tweak('swap', tweak, tenor)
            curve_tweak = curve_type(
                orig_curve.today, deposit_mkt_data_, swap_mkt_data, 
                fra_mkt_data_, future_mkt_data_, fixing_data_)
            all_tweaked_curves[tenor] = curve_tweak
            
        for tenor in fra_tenors:
            fra_mkt_data = orig_curve.mkt_data_tweak('fra', tweak, tenor)
            curve_tweak = curve_type(
                orig_curve.today, deposit_mkt_data_, swap_mkt_data_, 
                fra_mkt_data, future_mkt_data_, fixing_data_)
            all_tweaked_curves[tenor] = curve_tweak
            
        for tenor in future_tenors:
            future_mkt_data = orig_curve.mkt_data_tweak('future', tweak, tenor)
            curve_tweak = curve_type(
                orig_curve.today, deposit_mkt_data_, swap_mkt_data_, 
                fra_mkt_data_, future_mkt_data, fixing_data_)
            all_tweaked_curves[tenor] = curve_tweak

        return all_tweaked_curves
        
    elif tenor in deposit_tenors:
        deposit_mkt_data = orig_curve.mkt_data_tweak('deposit', tweak, tenor)
        curve_tweak = curve_type(
            orig_curve.today, deposit_mkt_data, swap_mkt_data_, 
            fra_mkt_data_, future_mkt_data_, fixing_data_)
        return curve_tweak
    
    elif tenor in swap_tenors:
        swap_mkt_data = orig_curve.mkt_data_tweak('swap', tweak, tenor)
        curve_tweak = curve_type(
            orig_curve.today, deposit_mkt_data_, swap_mkt_data, 
            fra_mkt_data_, future_mkt_data_, fixing_data_)
        return curve_tweak
    
    elif tenor in fra_tenors:
        fra_mkt_data = orig_curve.mkt_data_tweak('fra', tweak, tenor)
        curve_tweak = curve_type(
            orig_curve.today, deposit_mkt_data_, swap_mkt_data_, 
            fra_mkt_data, future_mkt_data_, fixing_data_)
        return curve_tweak
    
    elif tenor in future_tenors:
        future_mkt_data = orig_curve.mkt_data_tweak('future', tweak, tenor)
        curve_tweak = curve_type(
            orig_curve.today, deposit_mkt_data_, swap_mkt_data_, 
            fra_mkt_data_, future_mkt_data, fixing_data_)
        return curve_tweak
    
    else:
        raise Exception(f'Invalid tenor: {tenor}!') 
        
        

def curve_tweak_parallel(curve_type, orig_curve, tweak):
    deposit_mkt_data_tweaked = orig_curve.mkt_data_tweak('deposit', tweak, 'ALL')
    swap_mkt_data_tweaked = orig_curve.mkt_data_tweak('swap', tweak, 'ALL')
    fra_mkt_data_tweaked = orig_curve.mkt_data_tweak('fra', tweak, 'ALL')
    future_mkt_data_tweaked = orig_curve.mkt_data_tweak('future', tweak, 'ALL')
    
    curve_tweak = curve_type(
        orig_curve.today, deposit_mkt_data_tweaked, swap_mkt_data_tweaked, 
        fra_mkt_data_tweaked, future_mkt_data_tweaked, orig_curve.fixing_data)
    
    # fixing_mkt_data_tweaked = orig_curve.mkt_data_tweak('fixing', tweak, 'ALL')
    # curve_tweak = curve_type(
    #     orig_curve.today, deposit_mkt_data_tweaked, swap_mkt_data_tweaked, 
    #     fra_mkt_data_tweaked, future_mkt_data_tweaked, fixing_mkt_data_tweaked)
    
    return curve_tweak
    
    

