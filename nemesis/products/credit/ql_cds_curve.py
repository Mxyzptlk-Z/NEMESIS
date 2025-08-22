import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from ...utils.error import FinError
from ...utils.date import Date
from ...utils.day_count import DayCountTypes
from ...utils.frequency import FrequencyTypes
from ...utils.helpers import label_to_string
from ...utils.helpers import check_argument_types, _func_name
from ...utils.global_vars import g_days_in_year
from ...utils.ql_helper import ql_date_to_date
from ...market.curves.interpolator import _uinterpolate, InterpTypes, Interpolator
from ...market.curves.discount_curve import DiscountCurve


###############################################################################


class QLCreditCurve(DiscountCurve):

    def __init__(
        self,
        value_dt: Date,
        ql_cds_curve,
        interp_type: InterpTypes = InterpTypes.BACKWARD_FLAT_HAZARD_RATES,
        from_ql: bool = True,
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
        self.ql_cds_curve = ql_cds_curve
        self.interp_type = interp_type

        self._build_ir_curve_from_ql()
        self._build_curve_from_ql()

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

    def _build_curve_from_ql(self):
        """Build Curve from a QuantLib curve."""
        curve = self.ql_cds_curve.curve

        self._times = np.array([0.0])
        self._values = np.array([1.0])

        self._times = np.append(self._times, np.array(curve.interp_xs))
        self._values = np.append(self._values, self._survival_prob_from_hazard())

    ###############################################################################

    def _survival_prob_from_hazard(self):
        curve = self.ql_cds_curve.curve

        self._hazard_rates = np.array([0.0])
        self._hazard_rates = np.append(self._hazard_rates, np.array(curve.interp_ys))

        integration_xs = np.array(curve.interp_xs)
        integration_ys = np.array(curve.interp_ys)

        integration_xs = np.array([integration_xs[0]] + np.diff(integration_xs).tolist())
        integration = np.cumsum(integration_xs * integration_ys)
        
        return np.exp(-integration)

    ###############################################################################

    def _build_ir_curve_from_ql(self):
        from ..rates.ql_curve import QLCurve
        ql_ir_curve = self.ql_cds_curve.discount_curve
        self.libor_curve = QLCurve(self.value_dt, ql_ir_curve, dc_type=DayCountTypes.ACT_360, interp_type=InterpTypes.LINEAR_ZERO_RATES)

    ###############################################################################

    def hazard_rate(self, dt):
        """Extract the hazard rate on date dt. This function
        supports vectorisation."""

        if isinstance(dt, Date):
            t = (dt - self.value_dt) / 360
        elif isinstance(dt, list):
            t = np.array(dt)
        else:
            t = dt

        if np.any(t < 0.0):
            raise FinError("Target Date before curve anchor date")

        if isinstance(t, np.ndarray):
            n = len(t)
            hs = np.zeros(n)
            for i in range(0, n):
                hs[i] = _uinterpolate(
                    t[i], self._times, self._hazard_rates, self.interp_type.value
                )
            return hs
        elif isinstance(t, float):
            h = _uinterpolate(
                t, self._times, self._hazard_rates, self.interp_type.value
            )
            return h
        else:
            raise FinError("Unknown time type")

    ###############################################################################

    def survival_prob(self, dt):
        """Extract the survival probability to date dt. This function
        supports vectorisation."""

        if isinstance(dt, Date):
            t = (dt - self.value_dt) / 360
        elif isinstance(dt, list):
            t = np.array(dt)
        else:
            t = dt

        if np.any(t < 0.0):
            raise FinError("Survival Date before curve anchor date")

        interp_xs = self._times.copy()
        interp_ys = self._hazard_rates.copy()

        index = np.searchsorted(interp_xs, t)
        if index == len(interp_xs):
            index -= 1
        integration_xs = interp_xs[: index + 1]
        integration_xs[index] = t
        integration_xs = [integration_xs[0].tolist()] + np.diff(integration_xs).tolist()
        integration_ys = interp_ys[: index + 1]
        integration = np.dot(integration_xs, integration_ys)

        return np.exp(-integration)

    ###########################################################################

    def __repr__(self):
        """Print out the details of the QuantLib curve."""

        s = label_to_string("OBJECT TYPE", type(self).__name__)
        s += label_to_string("VALUATION DATE", self.value_dt)

        num_points = len(self._times)

        s += label_to_string("INTERP TYPE", self.interp_type)

        s += label_to_string("GRID TIMES", "GRID DFS")
        for i in range(0, num_points):
            s += label_to_string(
                "% 10.6f" % self._times[i], "%12.10f" % self._values[i]
            )

        return s
    
    ###############################################################################

    def _print(self):
        """Simple print function for backward compatibility."""
        print(self)

    ###############################################################################
