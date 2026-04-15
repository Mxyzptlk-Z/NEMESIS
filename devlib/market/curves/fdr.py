from typing import Union

import QuantLib as ql
import pandas as pd
import copy

import devlib.market.curves.curve_generator as cg
from devlib.market.curves.curve_generator import GeneralCurveGenerator



class Fdr007CurveGenerator(GeneralCurveGenerator):
    def build_swap_helpers(self, swap_mkt_data: Union[pd.DataFrame, None]):
        swap_helpers = []
        if self.swap_config == None:
            pass
        else:
            for idx in swap_mkt_data.index:
                settlement_delay = 1
                if swap_mkt_data.loc[idx, 'Tenor'] == '1M':
                    swap_period = ql.Period('1M')
                else:
                    swap_period = ql.Period('3M')
                swap_index = ql.IborIndex(
                    self.index_config.curve_name, swap_period, settlement_delay,
                    self.index_config.currency, self.index_config.calendar,
                    ql.ModifiedFollowing, self.index_config.end_of_month,
                    self.index_config.daycount)
                swap_helper = self.swap_config.build_swap_helper(
                    swap_mkt_data.loc[idx, 'Tenor'], swap_mkt_data.loc[idx, 'Rate'],
                    swap_index)
                swap_helpers.append(swap_helper)

        return swap_helpers



class Fdr001(cg.GeneralCurve):
    def curve_config_set(self):
        self.index_config = cg.GeneralOvernightIndexConfig(
            curve_name='FDR001',
            settlement_delay=0,
            currency=ql.CNYCurrency(),
            calendar=ql.China(ql.China.IB),
            daycount=ql.Actual365Fixed())

        self.deposit_config = cg.DepositHelperConfig(
            settlement_delay=0,
            calendar=ql.China(ql.China.IB),
            convention=ql.Following,
            end_of_month=False,
            daycount=ql.Actual365Fixed())

        self.swap_config = cg.OisRateHelperConfig(
            settlement_delay=0,
            calendar=ql.China(ql.China.IB),
            payment_lag=0,
            payment_freq=ql.Quarterly,
            payment_convention=ql.ModifiedFollowing,
            spread=0,
            forward_start=0)

        self.fra_config = None

        self.future_config = None

        self.curve_generator_config = GeneralCurveGenerator



class Fr001(cg.GeneralCurve):
    def curve_config_set(self):
        self.index_config = cg.GeneralOvernightIndexConfig(
            curve_name='FR001',
            settlement_delay=0,
            currency=ql.CNYCurrency(),
            calendar=ql.China(ql.China.IB),
            daycount=ql.Actual365Fixed())

        self.deposit_config = cg.DepositHelperConfig(
            settlement_delay=0,
            calendar=ql.China(ql.China.IB),
            convention=ql.Following,
            end_of_month=False,
            daycount=ql.Actual365Fixed())

        self.swap_config = cg.OisRateHelperConfig(
            settlement_delay=0,
            calendar=ql.China(ql.China.IB),
            payment_lag=0,
            payment_freq=ql.Quarterly,
            payment_convention=ql.ModifiedFollowing,
            spread=0,
            forward_start=0)

        self.fra_config = None

        self.future_config = None

        self.curve_generator_config = GeneralCurveGenerator



class Fdr007(cg.GeneralCurve):
    def curve_config_set(self):
        self.index_config = cg.IborIndexConfig(
            curve_name='FDR007',
            tenor='1W',
            settlement_delay=0,
            currency=ql.CNYCurrency(),
            calendar=ql.China(ql.China.IB),
            convention=ql.Following,
            end_of_month=False,
            daycount=ql.Actual365Fixed())

        self.deposit_config = cg.DepositHelperConfig(
            settlement_delay=1,
            calendar=ql.China(ql.China.IB),
            convention=ql.Following,
            end_of_month=False,
            daycount=ql.Actual365Fixed())

        self.swap_config = cg.SwapRateHelperConfig(
            calendar=ql.China(ql.China.IB),
            fixed_pay_freq=ql.Quarterly,
            fixed_convention=ql.ModifiedFollowing,
            fixed_daycount=ql.Actual365Fixed(),
            spread=0,
            forward_start=0,
            end_of_month=False)

        self.fra_config = None

        self.future_config = None

        self.curve_generator_config = Fdr007CurveGenerator



class Fr007(cg.GeneralCurve):
    def curve_config_set(self):
        self.index_config = cg.IborIndexConfig(
            curve_name='FR007',
            tenor='1W',
            settlement_delay=0,
            currency=ql.CNYCurrency(),
            calendar=ql.China(ql.China.IB),
            convention=ql.Following,
            end_of_month=False,
            daycount=ql.Actual365Fixed())

        self.deposit_config = cg.DepositHelperConfig(
            settlement_delay=1,
            calendar=ql.China(ql.China.IB),
            convention=ql.Following,
            end_of_month=False,
            daycount=ql.Actual365Fixed())

        self.swap_config = cg.SwapRateHelperConfig(
            calendar=ql.China(ql.China.IB),
            fixed_pay_freq=ql.Quarterly,
            fixed_convention=ql.ModifiedFollowing,
            fixed_daycount=ql.Actual365Fixed(),
            spread=0,
            forward_start=0,
            end_of_month=False)

        self.fra_config = None

        self.future_config = None

        self.curve_generator_config = Fdr007CurveGenerator


class Fr007Nd(cg.GeneralCurve):
    def curve_config_set(self):
        self.index_config = cg.IborIndexConfig(
            curve_name='FR007ND',
            tenor='1W',
            settlement_delay=0,
            currency=ql.CNYCurrency(),
            calendar=ql.China(ql.China.IB),
            convention=ql.Following,
            end_of_month=False,
            daycount=ql.Actual365Fixed())

        self.deposit_config = cg.DepositHelperConfig(
            settlement_delay=1,
            calendar=ql.China(ql.China.IB),
            convention=ql.Following,
            end_of_month=False,
            daycount=ql.Actual365Fixed())

        self.swap_config = cg.SwapRateHelperConfig(
            calendar=ql.China(ql.China.IB),
            fixed_pay_freq=ql.Quarterly,
            fixed_convention=ql.ModifiedFollowing,
            fixed_daycount=ql.Actual365Fixed(),
            spread=0,
            forward_start=0,
            end_of_month=False)

        self.fra_config = None

        self.future_config = None

        self.curve_generator_config = Fdr007CurveGenerator
