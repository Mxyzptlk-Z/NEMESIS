import copy

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import optimize

from ...market.curves.discount_curve import DiscountCurve
from ...market.curves.interpolator import Interpolator, InterpTypes
from ...utils.date import Date
from ...utils.day_count import DayCountTypes
from ...utils.error import FinError
from ...utils.frequency import FrequencyTypes
from ...utils.global_vars import g_days_in_year
from ...utils.helpers import _func_name, check_argument_types, label_to_string
from ...utils.ql_helper import ql_date_to_date

###############################################################################


class QLCurve(DiscountCurve):
    """Constructs a discount curve as implied by the prices of Overnight
    Index Rate swaps. The curve date is the date on which we are
    performing the valuation based on the information available on the
    curve date. Typically it is the date on which an amount of 1 unit paid
    has a present value of 1. This class inherits from FinDiscountCurve
    and so it has all of the methods that that class has.

    The construction of the curve is assumed to depend on just the OIS curve,
    i.e. it does not include information from Ibor-OIS basis swaps. For this
    reason I call it a one-curve.
    """

    ###############################################################################

    def __init__(
        self,
        value_dt: Date,
        ql_curve,
        dc_type: DayCountTypes = DayCountTypes.ACT_360,
        interp_type: InterpTypes = InterpTypes.LINEAR_ZERO_RATES,
        from_ql: bool = True,
        is_index: bool = True,
    ):
        """Create an instance of an overnight index rate swap curve given a
        valuation date and a set of OIS rates. Some of these may
        be left None and the algorithm will just use what is provided. An
        interpolation method has also to be provided. The default is to use a
        linear interpolation for swap rates on cpn dates and to then assume
        flat forwards between these cpn dates.

        The curve will assign a discount factor of 1.0 to the valuation date.
        """

        self.value_dt = value_dt
        self._interp_type = interp_type
        self.ql_curve = ql_curve
        self._is_index = is_index

        self._build_curve_from_ql(value_dt, ql_curve, dc_type, interp_type)

        if is_index:
            self.ccy = ql_curve.index_config.currency.code()
        self._from_ql = from_ql

    ###############################################################################

    def print_table(self, payment_dt: list):
        """Print a table of zero rate and discount factor on pivot dates."""

        zr = self.zero_rate(
            payment_dt,
            freq_type = FrequencyTypes.CONTINUOUS,
            dc_type = DayCountTypes.ACT_365F
        )

        df = self.df(payment_dt, day_count = DayCountTypes.ACT_365F)

        payment_dt_datetime = [dt.datetime() for dt in payment_dt]
        curve_result = pd.DataFrame({"Date": payment_dt_datetime, "ZR": (zr*100).round(5), "DF": df.round(6)})

        return curve_result

    ###############################################################################

    def print_figure(self, pivot_points):
        """Plot a figure of zero rate curve."""

        datetime_list = pd.date_range(
            start=self.value_dt.add_days(1).datetime(),
            end=pivot_points[-1].datetime()
        )
        date_list = [Date.from_date(dt) for dt in datetime_list]
        pivot_points_datetime = [dt.datetime() for dt in pivot_points]

        zr = self.zero_rate(
            date_list,
            freq_type = FrequencyTypes.CONTINUOUS,
            dc_type = DayCountTypes.ACT_365L
        )

        zr_pivot = self.zero_rate(
            pivot_points,
            freq_type = FrequencyTypes.CONTINUOUS,
            dc_type = DayCountTypes.ACT_365L
        )

        plt.figure(figsize=(10, 6))
        plt.plot(datetime_list, zr)
        plt.scatter(pivot_points_datetime, zr_pivot)

    ###############################################################################

    def _build_curve_from_ql(self, value_dt, ql_curve, dc_type, interp_type):
        """Build Curve from a QuantLib curve."""
        times = []
        dfs = []

        # Extract dates and discount factors from the QuantLib curve
        curve = ql_curve.curve
        ql_pillar_dts = ql_curve.curve.dates()
        self.pillar_dts = ql_date_to_date(ql_pillar_dts)

        for ql_dt, dt in zip(ql_pillar_dts, self.pillar_dts):
            t = (dt - value_dt) / g_days_in_year
            df = curve.discount(ql_dt)
            times.append(t)
            dfs.append(df)

        self._times = np.array(times)
        self._dfs = dfs

        # Fit the interpolator with the extracted times and discount factors
        self._interpolator = Interpolator(interp_type)
        self._interpolator.fit(self._times, self._dfs)

        self.dc_type = dc_type

        if self._is_index:
            index = ql_curve.index
            if not ql_curve.fixing_data.empty:
                self.fixing = ql_curve.fixing_data.set_index("Date")
            self.spot_days = index.fixingDays()
            self.tenor = str(index.tenor())

    ###############################################################################

    def bump_parallel(self, bump, inplace=False):
        """Bump all market quotes in parallel and rebuild curve."""
        bumped_ql_curve = self.ql_curve.tweak_parallel(bump)

        if inplace:
            self.ql_curve = bumped_ql_curve
            self._build_curve_from_ql(self.value_dt, bumped_ql_curve, self.dc_type, self._interp_type)
            return self
        else:
            return QLCurve(
                value_dt=self.value_dt,
                ql_curve=bumped_ql_curve,
                dc_type=self.dc_type,
                interp_type=self._interp_type,
                from_ql=self._from_ql,
                is_index=self._is_index
            )
            # return self.from_bump(self, bump)

    ###############################################################################

    def bump_curve(self, bump, inplace=False):
        bumped_ql_curve = self.ql_curve.tweak_discount_curve(bump)

        if inplace:
            self.ql_curve = bumped_ql_curve
            self._build_curve_from_ql(self.value_dt, bumped_ql_curve, self.dc_type, self._interp_type)
            return self
        else:
            return QLCurve(
                value_dt=self.value_dt,
                ql_curve=bumped_ql_curve,
                dc_type=self.dc_type,
                interp_type=self._interp_type,
                from_ql=self._from_ql,
                is_index=self._is_index
            )
            # return self.from_bump(self, bump)

    ###############################################################################

    @classmethod
    def from_bump(cls, curve, bump):
        """Create a curve by applying a bump to an existing curve."""
        bumped_ql_curve = curve.ql_curve.tweak_parallel(bump)
        return cls(
            value_dt=curve.value_dt,
            ql_curve=bumped_ql_curve,
            dc_type=curve.dc_type,
            interp_type=curve._interp_type,
            from_ql=curve._from_ql,
            is_index=curve._is_index
        )

    ###############################################################################

    def __repr__(self):
        """Print out the details of the QuantLib curve."""

        s = label_to_string("OBJECT TYPE", type(self).__name__)
        s += label_to_string("VALUATION DATE", self.value_dt)

        num_points = len(self._times)

        s += label_to_string("INTERP TYPE", self._interp_type)

        s += label_to_string("GRID TIMES", "GRID DFS")
        for i in range(0, num_points):
            s += label_to_string(
                "% 10.6f" % self._times[i], "%12.10f" % self._dfs[i]
            )

        return s

    ###############################################################################

    def _print(self):
        """Simple print function for backward compatibility."""
        print(self)

    ###############################################################################
