import copy
import numpy as np
import pandas as pd

from ...market.curves.forward_curve import ForwardCurve
from ...market.curves.interpolator import Interpolator, InterpTypes
from ...utils.calendar import CalendarTypes
from ...utils.date import Date
from ...utils.day_count import DayCount, DayCountTypes


###############################################################################


class PMForwardCurve(ForwardCurve):
    """
    """

    ###############################################################################

    def __init__(
        self,
        value_dt: Date,
        spot_pm_rate: float,
        pm_fwd_data: pd.DataFrame,
        data_type: str,
        currency_pair: str,
        cal_type: CalendarTypes,
        dc_type: DayCountTypes,
        interp_type: InterpTypes
    ):
        """"""
        super().__init__(
            value_dt, spot_pm_rate, pm_fwd_data, cal_type, dc_type, interp_type
        )

        self.currency_pair = currency_pair
        self.for_name = self.currency_pair[0:3]
        self.dom_name = self.currency_pair[3:6]

        self.data_type = data_type

        self._build_curve()

    ###############################################################################

    def _build_curve(self):
        """"""
        format_date = [Date.from_date(dt) for dt in self.fwd_data["SettleDate"]]
        self.fwd_data["SettleDate"] = format_date

        try:
            spot = self.fwd_data[self.fwd_data["Tenor"]=="SPOT"].to_dict(orient="records")[0]
            self.spot_dt = spot.get("SettleDate")
        except:
            self.spot_dt = None

        pm_fwd_data_after_spot = self.fwd_data[self.fwd_data["SettleDate"] > self.spot_dt].copy()
        pm_fwd_data_after_spot = pm_fwd_data_after_spot.drop_duplicates(subset=["SettleDate"], keep="last")

        pm_fwd_dts = [self.value_dt, self.spot_dt] + pm_fwd_data_after_spot["SettleDate"].tolist()
        if self.data_type == "rate":
            pm_fwd_rates = [0.0, 0.0] + pm_fwd_data_after_spot["Rate"].tolist()
            rate_day_count = DayCount(DayCountTypes.ACT_360)
            pm_fwds = [self.spot_rate * (1 + r * rate_day_count.year_frac(self.spot_dt, dt)[0]) for r, dt in zip(pm_fwd_rates, pm_fwd_dts)]
        else:
            pm_fwd_points = [0.0, 0.0] + pm_fwd_data_after_spot["Spread"].tolist()
            pm_fwds = [self.spot_rate + p / 100 for p in pm_fwd_points]

        self.pm_fwds = pm_fwds
        self.pm_fwd_dts = pm_fwd_dts

        day_count = DayCount(self.dc_type)
        self._times = np.array([day_count.year_frac(self.value_dt, dt)[0] for dt in pm_fwd_dts])

        self.spot_today = self.pm_fwds[0]
        self._dfs = np.array([self.spot_today / pm_fwd for pm_fwd in pm_fwds])

        self._interpolator = Interpolator(self._interp_type)
        self._interpolator.fit(self._times, self._dfs)

    ###############################################################################

    def get_forward(self, dt: Date, dc_type: DayCountTypes):
        return self.spot_today / self.df(dt, day_count=dc_type)

    ###############################################################################

    def get_forward_spot(self, dt, dc_type: DayCountTypes):
        return self.get_forward(dt, dc_type)

    ###############################################################################

    def bump_spot(self, bump):
        bumped_curve = copy.deepcopy(self)
        bumped_curve.spot_today = self.spot_today * (self.spot_rate + bump) / self.spot_rate
        bumped_curve.spot_rate = self.spot_rate + bump
        return bumped_curve

    ###############################################################################

    # rd up or rf down
    def bump_parallel(self, bump):
        bumped_curve = copy.deepcopy(self)
        bumped_curve._dfs *= np.exp(-bump * bumped_curve._times)
        bumped_curve.spot_rate = bumped_curve.get_forward(self.spot_dt, self.dc_type)
        return bumped_curve

    ###############################################################################

    # forward curve after domestic curve bump
    def bump_domestic_curve(self, domestic_curve_pre, domestic_curve_bumped):
        bumped_curve = copy.deepcopy(self)
        dom_df_pre = domestic_curve_pre.df(self.pm_fwd_dts, self.dc_type) / domestic_curve_pre.df(self.value_dt, self.dc_type)
        dom_df_bumped = domestic_curve_bumped.df(self.pm_fwd_dts, self.dc_type) / domestic_curve_bumped.df(self.value_dt, self.dc_type)
        bumped_curve._dfs *= dom_df_bumped / dom_df_pre
        return bumped_curve

    ###############################################################################
