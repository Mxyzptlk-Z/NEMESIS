import numpy as np
import pandas as pd

from ...utils.date import Date
from ...utils.calendar import CalendarTypes
from ...utils.day_count import DayCountTypes
from ...utils.fx_helper import get_fx_pair_base_size
from ...utils.global_vars import g_days_in_year
from ...market.curves.discount_curve import DiscountCurve
from ...market.curves.interpolator import InterpTypes, Interpolator

T1_SETTLE_FX_PAIRS = ["USDCAD", "CADUSD", "USDPHP", "PHPUSD", "USDMNT", "MNTUSD", "USDRUB", "RUBUSD"]

###############################################################################


class FXForwardCurve(DiscountCurve):
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
        self.value_dt = value_dt
        self.spot_fx_rate = spot_fx_rate
        self.fx_fwd_data = fx_fwd_data.copy()
        self.currency_pair = currency_pair

        self.for_name = self.currency_pair[0:3]
        self.dom_name = self.currency_pair[3:6]

        self.cal_type = cal_type
        self.dc_type = dc_type

        self._interp_type = interp_type
        self._interpolator = None

        self._build_curve()

    def _build_curve(self):
        """"""
        format_date = [Date.from_string(dt, format_string="%Y-%m-%d") for dt in self.fx_fwd_data["SettleDate"]]
        self.fx_fwd_data["SettleDate"] = format_date

        try:
            on = self.fx_fwd_data[self.fx_fwd_data["Tenor"]=="ON"].to_dict(orient="records")[0]
            on_spread = on.get("Spread")
            on_settle_dt = on.get("SettleDate")
        except:
            raise Exception('Missing ON spread data!')

        try:
            tn = self.fx_fwd_data[self.fx_fwd_data["Tenor"]=="TN"].to_dict(orient="records")[0]
            tn_spread = tn.get("Spread")
            tn_settle_dt = tn.get("SettleDate")
        except:
            exist_tn = False
        else:
            exist_tn = True

        try:
            spot = self.fx_fwd_data[self.fx_fwd_data["Tenor"]=="SPOT"].to_dict(orient="records")[0]
            self.spot_dt = spot.get("SettleDate")
        except:
            if self.currency_pair in T1_SETTLE_FX_PAIRS:
                self.spot_dt = on_settle_dt
            else:
                self.spot_dt = None
            
        fwd_point_base = get_fx_pair_base_size(self.currency_pair)

        fx_fwd_data_after_spot = self.fx_fwd_data[self.fx_fwd_data["SettleDate"] > self.spot_dt].copy()
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

        self.fx_fwds = [self.spot_fx_rate + s / fwd_point_base for s in fx_fwd_points]
        self._times = np.array([(dt - self.value_dt) / g_days_in_year for dt in fx_fwd_dts])

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

    # def tweak_spot(self, tweak):
    #     tweaked_curve = copy.copy(self)
    #     tweaked_curve.spot_today = self.spot_today * (self.spot + tweak) / self.spot
    #     tweaked_curve.spot = self.spot + tweak

    #     return tweaked_curve


    # # rd up or rf down
    # def tweak_parallel(self, tweak):
    #     tweaked_curve = copy.copy(self)
    #     tweaked_curve.fx_fwd_dfs = copy.deepcopy(self.fx_fwd_dfs)
    #     today = self.today
    #     fx_fwd_dates = self.fx_fwd_dates
    #     calendar = self.calendar
    #     daycount = self.daycount
    #     for i in range(len(tweaked_curve.fx_fwd_dfs)):
    #         tweaked_curve.fx_fwd_dfs[i] *= np.exp(-tweak * daycount.yearFraction(today, fx_fwd_dates[i]))

    #     curve = ql.DiscountCurve(fx_fwd_dates, tweaked_curve.fx_fwd_dfs, daycount, calendar)
    #     curve.enableExtrapolation()
    #     tweaked_curve.curve = curve
    #     tweaked_curve.spot = tweaked_curve.get_forward(self.spot_date)

    #     return tweaked_curve


    # # forward curve after dccy curve tweak
    # def tweak_dccy_curve(self, dccy_curve_orig, dccy_curve_tweaked):
    #     tweaked_curve = copy.copy(self)
    #     tweaked_curve.fx_fwd_dfs = copy.deepcopy(self.fx_fwd_dfs)
    #     today = self.today
    #     fx_fwd_dates = self.fx_fwd_dates
    #     calendar = self.calendar
    #     daycount = self.daycount
    #     for i in range(len(tweaked_curve.fx_fwd_dfs)):
    #         dccy_df_orig = (dccy_curve_orig.curve.discount(fx_fwd_dates[i]) / 
    #                         dccy_curve_orig.curve.discount(today))
    #         dccy_df_tweaked = (dccy_curve_tweaked.curve.discount(fx_fwd_dates[i]) / 
    #                            dccy_curve_tweaked.curve.discount(today))
    #         tweaked_curve.fx_fwd_dfs[i] *= dccy_df_tweaked / dccy_df_orig

    #     curve = ql.DiscountCurve(fx_fwd_dates, tweaked_curve.fx_fwd_dfs, daycount, calendar)
    #     curve.enableExtrapolation()
    #     tweaked_curve.curve = curve

    #     return tweaked_curve
