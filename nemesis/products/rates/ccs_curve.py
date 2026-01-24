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
from ...utils.helpers import check_argument_types, label_to_string, times_from_dates

SWAP_TOL = 1e-10
MAX_ITER = 50

###############################################################################


def _f(df, *args):
    """Root search objective function for OIS"""

    curve = args[0]
    value_dt = args[1]
    swap = args[2]
    num_points = len(curve._times)
    curve._dfs[num_points - 1] = df

    # For discount that need a fit function, we fit it now
    curve._interpolator.fit(curve._times, curve._dfs)
    v_swap = swap.value(value_dt, curve, None)
    notional = swap.fixed_leg.notional
    v_swap /= notional
    return v_swap


###############################################################################


def _g(df, *args):
    """Root search objective function for FX Swap"""

    d_curve = args[0]
    f_curve = args[1]
    value_dt = args[2]
    swap = args[3]
    num_points = len(d_curve._times)
    d_curve._dfs[num_points - 1] = df

    # For discount that need a fit function, we fit it now
    d_curve._interpolator.fit(d_curve._times, d_curve._dfs)
    v_swap = swap.value(value_dt, d_curve, f_curve)
    notional = swap.notional
    v_swap["value"] /= notional
    return v_swap["value"]


###############################################################################


class CCSCurve(DiscountCurve):
    """
    """

    ###############################################################################

    def __init__(
        self,
        value_dt: Date,
        fx_swaps: list,
        ois_swaps: list,
        foreign_curve: DiscountCurve,
        interp_type: InterpTypes = InterpTypes.FLAT_FWD_RATES,
    ):
        """
        """
        check_argument_types(self.__init__, locals())

        self.value_dt = value_dt
        self.foreign_curve = foreign_curve
        self._interp_type = interp_type
        self._interpolator = None

        self._validate_inputs(fx_swaps, ois_swaps)
        self._from_ql = False
        self._build_curve()

    ###############################################################################

    def _validate_inputs(self, fx_swaps, ois_swaps):
        """Validate the inputs for each of the Libor products."""

        # Now determine which instruments are used
        self.used_fx_swaps = fx_swaps
        self.used_ois_swaps = ois_swaps

        # Need the floating leg basis for the curve
        if len(self.used_ois_swaps) > 0:
            self.dc_type = ois_swaps[0].float_leg.dc_type
        else:
            self.dc_type = None

    ###############################################################################

    def _build_curve(self):

        self._build_curve_using_1d_solver()

    ###############################################################################

    def _build_curve_using_1d_solver(self):
        """"""

        self._interpolator = Interpolator(self._interp_type)
        self._times = np.array([])
        self._dfs = np.array([])

        # time zero is now.
        t_mat = 0.0
        df_mat = 1.0
        self._times = np.append(self._times, 0.0)
        self._dfs = np.append(self._dfs, df_mat)
        self._interpolator.fit(self._times, self._dfs)

        for swap in self.used_fx_swaps:
            maturity_dt = swap.far_leg.delivery_dt
            t_mat = (maturity_dt - self.value_dt) / g_days_in_year

            self._times = np.append(self._times, t_mat)
            self._dfs = np.append(self._dfs, df_mat)

            argtuple = (self, self.foreign_curve, self.value_dt, swap)

            df_mat = optimize.newton(
                _g,
                x0=df_mat,
                fprime=None,
                args=argtuple,
                tol=SWAP_TOL,
                maxiter=MAX_ITER,
                fprime2=None,
                full_output=False,
            )

        for swap in self.used_ois_swaps:
            maturity_dt = swap.fixed_leg.payment_dts[-1]
            t_mat = (maturity_dt - self.value_dt) / g_days_in_year

            self._times = np.append(self._times, t_mat)
            self._dfs = np.append(self._dfs, df_mat)

            argtuple = (self, self.value_dt, swap)

            df_mat = optimize.newton(
                _f,
                x0=df_mat,
                fprime=None,
                args=argtuple,
                tol=SWAP_TOL,
                maxiter=MAX_ITER,
                fprime2=None,
                full_output=False,
            )

        self._interpolator.fit(self._times, self._dfs)

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
