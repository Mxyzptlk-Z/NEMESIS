import copy
import numpy as np
import pandas as pd

from ...market.curves.discount_curve import DiscountCurve
from ...market.curves.forward_curve import ForwardCurve
from ...market.curves.interpolator import Interpolator, InterpTypes
from ...utils.calendar import CalendarTypes
from ...utils.date import Date
from ...utils.day_count import DayCount, DayCountTypes
from ...utils.error import FinError
from ...utils.fx_helper import get_fx_pair_base_size
from ...utils.global_vars import g_days_in_year

T1_SETTLE_FX_PAIRS = ["USDCAD", "CADUSD", "USDPHP", "PHPUSD", "USDMNT", "MNTUSD", "USDRUB", "RUBUSD"]

###############################################################################


class FXForwardCurve(ForwardCurve):
    """
    """

    ###############################################################################

    def __init__(
        self,
        value_dt: Date,
        spot_fx_rate: float,
        fx_fwd_data: pd.DataFrame,
        currency_pair: str,
        cal_type: CalendarTypes,
        dc_type: DayCountTypes,
        interp_type: InterpTypes
    ):
        """"""
        super().__init__(
            value_dt, spot_fx_rate, fx_fwd_data, cal_type, dc_type, interp_type
        )

        self.currency_pair = currency_pair
        self.for_name = self.currency_pair[0:3]
        self.dom_name = self.currency_pair[3:6]

        self._build_curve()

    ###############################################################################

    def _build_curve(self):
        """"""
        format_date = [Date.from_string(dt, format_string="%Y-%m-%d") for dt in self.fwd_data["SettleDate"]]
        self.fwd_data["SettleDate"] = format_date

        try:
            on = self.fwd_data[self.fwd_data["Tenor"]=="ON"].to_dict(orient="records")[0]
            on_spread = on.get("Spread")
            on_settle_dt = on.get("SettleDate")
        except:
            raise FinError("ON spread data missing")

        try:
            tn = self.fwd_data[self.fwd_data["Tenor"]=="TN"].to_dict(orient="records")[0]
            tn_spread = tn.get("Spread")
            tn_settle_dt = tn.get("SettleDate")
        except:
            exist_tn = False
        else:
            exist_tn = True

        try:
            spot = self.fwd_data[self.fwd_data["Tenor"]=="SPOT"].to_dict(orient="records")[0]
            self.spot_dt = spot.get("SettleDate")
        except:
            if self.currency_pair in T1_SETTLE_FX_PAIRS:
                self.spot_dt = on_settle_dt
            else:
                self.spot_dt = None

        fwd_point_base = get_fx_pair_base_size(self.currency_pair)

        fx_fwd_data_after_spot = self.fwd_data[self.fwd_data["SettleDate"] > self.spot_dt].copy()
        fx_fwd_data_after_spot = fx_fwd_data_after_spot.drop_duplicates(subset=["SettleDate"], keep="last")
        fx_fwd_points = fx_fwd_data_after_spot["Spread"].tolist()
        fx_fwd_dts = fx_fwd_data_after_spot["SettleDate"].tolist()

        if self.currency_pair in T1_SETTLE_FX_PAIRS:
            fx_fwd_points = [-on_spread, 0.0] + fx_fwd_points
            fx_fwd_dts = [self.value_dt, self.spot_dt] + fx_fwd_dts

        else:
            if exist_tn and (not on_settle_dt == tn_settle_dt):
                fx_fwd_points = [-(on_spread + tn_spread), -tn_spread, 0.0] + fx_fwd_points
                fx_fwd_dts = [self.value_dt, on_settle_dt, self.spot_dt] + fx_fwd_dts
            else:
                fx_fwd_points = [-on_spread, 0.0] + fx_fwd_points
                fx_fwd_dts = [self.value_dt, self.spot_dt] + fx_fwd_dts

        self.fx_fwds = [self.spot_rate + s / fwd_point_base for s in fx_fwd_points]
        self.fx_fwd_dts = fx_fwd_dts

        day_count = DayCount(self.dc_type)
        self._times = np.array([day_count.year_frac(self.value_dt, dt)[0] for dt in fx_fwd_dts])
        # self._times = np.array([(dt - self.value_dt) / g_days_in_year for dt in fx_fwd_dts])

        self.spot_today = self.fx_fwds[0]
        self._dfs = np.array([self.spot_today / fx_fwd for fx_fwd in self.fx_fwds])

        self._interpolator = Interpolator(self._interp_type)
        self._interpolator.fit(self._times, self._dfs)

    ###############################################################################

    def get_forward(self, dt: Date, dc_type: DayCountTypes):
        return self.spot_today / self.df(dt, day_count=dc_type)

    ###############################################################################

    def get_forward_spot(self, dt):
        return self.get_forward(dt)

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
        dom_df_pre = domestic_curve_pre.df(self.fx_fwd_dts, self.dc_type) / domestic_curve_pre.df(self.value_dt, self.dc_type)
        dom_df_bumped = domestic_curve_bumped.df(self.fx_fwd_dts, self.dc_type) / domestic_curve_bumped.df(self.value_dt, self.dc_type)
        bumped_curve._dfs *= dom_df_bumped / dom_df_pre
        return bumped_curve

    ###############################################################################
