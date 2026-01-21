import copy
import numpy as np
import pandas as pd

from ...utils.date import Date
from ...utils.error import FinError
from ...utils.calendar import CalendarTypes
from ...utils.day_count import DayCountTypes
from ...utils.fx_helper import get_fx_pair_base_size
from ...utils.global_vars import g_days_in_year
from ...market.curves.discount_curve import DiscountCurve
from ...market.curves.interpolator import InterpTypes, Interpolator

###############################################################################


class FXImpliedForwardCurve:
    """"""

    ###############################################################################

    def __init__(
        self,
        value_dt: Date,
        spot_fx_rate: str,
        foreign_curve: DiscountCurve,
        domestic_curve: DiscountCurve,
        curency_pair: str,
        spot_dt: Date = None
    ):
        self.value_dt = value_dt
        self.spot_fx_rate = spot_fx_rate
        self.foreign_curve = copy.copy(foreign_curve)
        self.domestic_curve = copy.copy(domestic_curve)
        self.currency_pair = curency_pair

        self.for_name = self.currency_pair[0:3]
        self.dom_name = self.currency_pair[3:6]

        if spot_dt is None:
            self.spot_dt = value_dt
        else:
            self.spot_dt = spot_dt

    ###############################################################################

    def get_forward(self, dt: Date, dc_type):
        """"""
        forward = self.spot_fx_rate * (
            self.foreign_curve.df(dt, dc_type) / self.domestic_curve.df(dt, dc_type) *
            self.domestic_curve.df(self.spot_dt, dc_type) / self.foreign_curve.df(self.spot_dt, dc_type)
        )
        return forward

    ###############################################################################

    def get_forward_spot(self, dt: Date):
        return self.get_forward(dt)

    ###############################################################################

    # # forward curve after dccy curve tweak
    # def tweak_dccy_curve(self, tweak):
    #     tweaked_curve = copy.copy(self)
    #     tweaked_d_dis_curve = self.d_dis_curve.tweak_parallel(tweak)
    #     tweaked_curve.d_dis_curve = tweaked_d_dis_curve

    #     return tweaked_curve


    # # forward curve after fccy curve tweak
    # def tweak_fccy_curve(self, tweak):
    #     tweaked_curve = copy.copy(self)
    #     tweaked_f_dis_curve = self.f_dis_curve.tweak_parallel(tweak)
    #     tweaked_curve.f_dis_curve = tweaked_f_dis_curve

    #     return tweaked_curve
    
    
    # def tweak_spot(self, tweak):
    #     tweaked_curve = copy.copy(self)
    #     tweaked_curve.spot = self.spot + tweak

    #     return tweaked_curve


###############################################################################


class FXImpliedAssetCurve:
    def __init__(
        self,
        value_dt: Date,
        base_curve: DiscountCurve,
        forward_curve: DiscountCurve,
        cal_type: CalendarTypes,
        dc_type: DayCountTypes,
        interp_type: InterpTypes,
    ):
        self.value_dt = value_dt
        self.base_curve = base_curve
        self.forward_curve = forward_curve
        self.cal_type = cal_type
        self.dc_type = dc_type

        self._interp_type = interp_type
        self._interpolator = None

        if base_curve.ccy == forward_curve.dom_name:
            self.ccy = forward_curve.for_name
        else:
            self.ccy = forward_curve.dom_name

        self._build_curve()

    ###############################################################################

    # def _build_curve(self):
    #     """"""
    #     asset_dts = self.base_curve.pillar_dts

    #     if not asset_dts[0] == self.value_dt:
    #         raise FinError("The first date does not match")

    #     if self.base_curve.ccy == self.forward_curve.dom_name:
    #         asset_dfs = [1] + [base_curve.curve.discount(d) / fx_fwd_crv.curve.discount(d) 
    #                            for d in asset_dts[1:]]
    #     else:
    #         asset_dfs = [1] + [base_curve.curve.discount(d) * fx_fwd_crv.curve.discount(d)
    #                            for d in asset_dts[1:]]

    #     if interpolation_method == "zerolinear":
    #         asset_zeros = [-np.log(df) / daycount.yearFraction(today, date) 
    #                        for df, date in zip(asset_dfs[1:], asset_dates[1:])]
    #         asset_zeros = [asset_zeros[0]] + asset_zeros
    #         asset_crv = ql.ZeroCurve(asset_dates, asset_zeros, daycount, calendar)      
    #     elif interpolation_method == "dfloglinear":
    #         asset_crv = ql.DiscountCurve(asset_dates, asset_dfs, daycount, calendar)
    #     else:
    #         raise Exception(f'Unsupported interpolation method: {interpolation_method}')     

    #     asset_crv.enableExtrapolation()

    #     return asset_crv

    ###############################################################################
