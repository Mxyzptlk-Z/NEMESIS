import copy

import numpy as np

from ...market.curves.discount_curve import DiscountCurve
from ...market.curves.interpolator import Interpolator, InterpTypes
from ...market.curves.forward_curve import ForwardCurve
from ...utils.calendar import CalendarTypes
from ...utils.date import Date
from ...utils.day_count import DayCount, DayCountTypes
from ...utils.error import FinError
from ...utils.fx_helper import get_fx_pair_base_size
from ...utils.global_vars import g_days_in_year

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

    # forward curve after domestic curve bump
    def bump_domestic_curve(self, bump):
        bumped_curve = copy.deepcopy(self)
        bumped_domestic_curve = self.domestic_curve.bump_parallel(bump)
        bumped_curve.domestic_curve = bumped_domestic_curve
        return bumped_curve

    ###############################################################################

    # forward curve after foreign curve bump
    def bump_foreign_curve(self, bump):
        bumped_curve = copy.deepcopy(self)
        bumped_foreign_curve = self.foreign_curve.bump_parallel(bump)
        bumped_curve.foreign_curve = bumped_foreign_curve
        return bumped_curve

    ###############################################################################

    def bump_spot(self, bump):
        bumped_curve = copy.deepcopy(self)
        bumped_curve.spot_fx_rate = self.spot_fx_rate + bump
        return bumped_curve


###############################################################################


class FXImpliedAssetCurve(DiscountCurve):
    def __init__(
        self,
        value_dt: Date,
        base_curve: DiscountCurve,
        forward_curve: ForwardCurve,
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

    def _build_curve(self):
        """"""
        asset_dts = self.base_curve.pillar_dts

        if not asset_dts[0] == self.value_dt:
            raise FinError("The first date does not match")

        if self.base_curve.ccy == self.forward_curve.dom_name:
            asset_dfs = [1] + [
                self.base_curve.df(dt, day_count=DayCountTypes.ACT_365F) /
                self.forward_curve.df(dt, day_count=DayCountTypes.ACT_365F)
                for dt in asset_dts[1:]
            ]
        else:
            asset_dfs = [1] + [
                self.base_curve.df(dt, day_count=DayCountTypes.ACT_365F) *
                self.forward_curve.df(dt, day_count=DayCountTypes.ACT_365F)
                for dt in asset_dts[1:]
            ]

        day_count = DayCount(self.dc_type)

        self._times = np.array([day_count.year_frac(self.value_dt, dt)[0] for dt in asset_dts])
        # self._times = np.array([(dt - self.value_dt) / g_days_in_year for dt in asset_dts])
        self._dfs = np.array(asset_dfs)

        self._interpolator = Interpolator(self._interp_type)
        self._interpolator.fit(self._times, self._dfs)

    ###############################################################################

    def bump_parallel(self, bump, inplace=False):
        if inplace:
            self._dfs *= np.exp(-bump * self._times)
            self._interpolator.fit(self._times, self._dfs)
            return self
        else:
            # bumped_curve = FXImpliedAssetCurve(
            #     value_dt=self.value_dt,
            #     base_curve=self.base_curve,
            #     forward_curve=self.forward_curve,
            #     cal_type=self.cal_type,
            #     dc_type=self.dc_type,
            #     interp_type=self._interp_type
            # )
            bumped_curve = copy.copy(self)
            bumped_curve._dfs *= np.exp(-bump * bumped_curve._times)
            bumped_curve._interpolator.fit(bumped_curve._times, bumped_curve._dfs)
            return bumped_curve

    ###############################################################################
