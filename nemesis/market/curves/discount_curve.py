###############################################################################
# Copyright (C) 2018, 2019, 2020 Dominic O'Kane
###############################################################################


import numpy as np
from typing import Union

from .interpolator import Interpolator, InterpTypes, interpolate

from ...utils.date import Date
from ...utils.error import FinError
from ...utils.global_vars import g_days_in_year, g_small
from ...utils.frequency import annual_frequency, FrequencyTypes
from ...utils.day_count import DayCount, DayCountTypes
from ...utils.math import test_monotonicity
from ...utils.schedule import Schedule
from ...utils.helpers import check_argument_types
from ...utils.helpers import times_from_dates
from ...utils.helpers import label_to_string


###############################################################################


class DiscountCurve:
    """This is a base discount curve which has an internal representation of
    a vector of times and discount factors and an interpolation scheme for
    interpolating between these fixed points."""

    ###########################################################################

    def __init__(
        self,
        value_dt: Date,
        df_dates: list,
        df_values: np.ndarray,
        interp_type: InterpTypes = InterpTypes.FLAT_FWD_RATES,
    ):
        """Create the discount curve from a vector of times and discount
        factors with an anchor date and specify an interpolation scheme. As we
        are explicitly linking dates and discount factors, we do not need to
        specify any compounding convention or day count calculation since
        discount factors are pure prices. We do however need to specify a
        convention for interpolating the discount factors in time."""
        check_argument_types(self.__init__, locals())

        # Validate curve
        if len(df_dates) < 1:
            raise FinError("Times has zero length")

        if len(df_dates) != len(df_values):
            raise FinError("Times and Values are not the same")

        self._times = [0.0]
        self._dfs = [1.0]
        self._df_dates = df_dates

        num_points = len(df_dates)

        start_index = 0
        if num_points > 0:
            if df_dates[0] == value_dt:
                self._dfs[0] = df_values[0]
                start_index = 1

        for i in range(start_index, num_points):
            t = (df_dates[i] - value_dt) / g_days_in_year
            self._times.append(t)
            self._dfs.append(df_values[i])

        self._times = np.array(self._times)

        if test_monotonicity(self._times) is False:
            print(self._times)
            raise FinError("Times are not sorted in increasing order")

        self.value_dt = value_dt
        self.freq_type = FrequencyTypes.CONTINUOUS
        # This needs to be thought about - I just assign an arbitrary value
        self.dc_type = DayCountTypes.ACT_360

        self._dfs = np.array(self._dfs)
        self._interp_type = interp_type
        self._interpolator = Interpolator(self._interp_type)
        self._interpolator.fit(self._times, self._dfs)

    ###########################################################################

    def _zero_to_df(
        self,
        value_dt: Date,  # TODO: why is value_dt not used ?
        rates: Union[float, np.ndarray],
        times: Union[float, np.ndarray],
        freq_type: FrequencyTypes,
        dc_type: DayCountTypes,
    ):
        """Convert a zero with a specified compounding frequency and day count
        convention to a discount factor for a single maturity date or a list of
        dates. The day count is used to calculate the elapsed year fraction."""

        if isinstance(times, float):
            times = np.array([times])

        t = np.maximum(times, g_small)

        f = annual_frequency(freq_type)

        if freq_type == FrequencyTypes.CONTINUOUS:
            df = np.exp(-rates * t)
        elif freq_type == FrequencyTypes.SIMPLE:
            df = 1.0 / (1.0 + rates * t)
        elif (
            freq_type == FrequencyTypes.ANNUAL
            or freq_type == FrequencyTypes.SEMI_ANNUAL
            or freq_type == FrequencyTypes.QUARTERLY
            or freq_type == FrequencyTypes.MONTHLY
        ):
            df = 1.0 / np.power(1.0 + rates / f, f * t)
        else:
            raise FinError("Unknown Frequency type")

        return df

    ###########################################################################

    def _df_to_zero(
        self,
        dfs: Union[float, np.ndarray],
        maturity_dts: Union[Date, list],
        freq_type: FrequencyTypes,
        dc_type: DayCountTypes,
    ):
        """Given a dates this first generates the discount factors. It then
        converts the discount factors to a zero rate with a chosen compounding
        frequency which may be continuous, simple, or compounded at a specific
        frequency which are all choices of FrequencyTypes. Returns a list of
        discount factor."""

        f = annual_frequency(freq_type)

        if isinstance(maturity_dts, Date):
            date_list = [maturity_dts]
        else:
            date_list = maturity_dts

        if isinstance(dfs, float):
            df_list = [dfs]
        else:
            df_list = dfs

        if len(date_list) != len(df_list):
            raise FinError("Date list and df list do not have same length")

        num_dates = len(date_list)
        zero_rates = []

        times = times_from_dates(date_list, self.value_dt, dc_type)

        for i in range(0, num_dates):

            df = df_list[i]

            t = max(times[i], g_small)

            if freq_type == FrequencyTypes.CONTINUOUS:
                r = -np.log(df) / t
            elif freq_type == FrequencyTypes.SIMPLE:
                r = (1.0 / df - 1.0) / t
            else:
                r = (np.power(df, -1.0 / (t * f)) - 1.0) * f

            zero_rates.append(r)

        return np.array(zero_rates)

    ###########################################################################

    def zero_rate(
        self,
        dts: Union[list, Date],
        freq_type: FrequencyTypes = FrequencyTypes.CONTINUOUS,
        dc_type: DayCountTypes = DayCountTypes.ACT_360,
    ):
        """Calculation of zero rates with specified frequency. This
        function can return a vector of zero rates given a vector of
        dates so must use Numpy functions. Default frequency is a
        continuously compounded rate."""

        if isinstance(freq_type, FrequencyTypes) is False:
            raise FinError("Invalid Frequency type.")

        if isinstance(dc_type, DayCountTypes) is False:
            raise FinError("Invalid Day Count type.")

        dfs = self.df(dts, day_count=dc_type)
        zero_rates = self._df_to_zero(dfs, dts, freq_type, dc_type)

        if isinstance(dts, Date):
            return zero_rates[0]
        else:
            return np.array(zero_rates)

        return zero_rates

    ###########################################################################

    def cc_rate(
        self, dts: Union[list, Date], dc_type: DayCountTypes = DayCountTypes.SIMPLE
    ):
        """Calculation of zero rates with continuous compounding. This
        function can return a vector of cc rates given a vector of
        dates so must use Numpy functions."""

        cc_rates = self.zero_rate(dts, FrequencyTypes.CONTINUOUS, dc_type)
        return cc_rates

    ###########################################################################

    def swap_rate(
        self,
        effective_dt: Date,
        maturity_dt: Union[list, Date],
        freq_type=FrequencyTypes.ANNUAL,
        dc_type: DayCountTypes = DayCountTypes.THIRTY_E_360,
    ):
        """Calculate the swap rate to maturity date. This is the rate paid by
        a swap that has a price of par today. This is the same as a Libor swap
        rate except that we do not do any business day adjustments."""

        # Note that this function does not call the IborSwap class to
        # calculate the swap rate since that will create a circular dependency.
        # I therefore recreate the actual calculation of the swap rate here.

        if effective_dt < self.value_dt:
            raise FinError("Swap starts before the curve valuation date.")

        if isinstance(freq_type, FrequencyTypes) is False:
            raise FinError("Invalid Frequency type.")

        if isinstance(freq_type, FrequencyTypes) is False:
            raise FinError("Invalid Frequency type.")

        if freq_type == FrequencyTypes.SIMPLE:
            raise FinError("Cannot calculate par rate with simple yield freq.")
        elif freq_type == FrequencyTypes.CONTINUOUS:
            raise FinError("Cannot calculate par rate with continuous freq.")

        if isinstance(maturity_dt, Date):
            maturity_dts = [maturity_dt]
        else:
            maturity_dts = maturity_dt

        par_rates = []

        for maturity_dt in maturity_dts:

            if maturity_dt <= effective_dt:
                raise FinError("Maturity date is before the swap start date.")

            schedule = Schedule(effective_dt, maturity_dt, freq_type)

            flow_dts = schedule.generate()
            flow_dts[0] = effective_dt

            day_counter = DayCount(dc_type)
            prev_dt = flow_dts[0]
            pv01 = 0.0
            df = 1.0

            for next_dt in flow_dts[1:]:
                df = self.df(next_dt)
                alpha = day_counter.year_frac(prev_dt, next_dt)[0]
                pv01 += alpha * df
                prev_dt = next_dt

            if abs(pv01) < g_small:
                par_rate = 0.0
            else:
                df_start = self.df(effective_dt)
                par_rate = (df_start - df) / pv01

            par_rates.append(par_rate)

        par_rates = np.array(par_rates)

        if isinstance(maturity_dts, Date):
            return par_rates[0]
        else:
            return par_rates

    ###########################################################################

    def df(self, dt: Union[list, Date], day_count=DayCountTypes.ACT_ACT_ISDA):
        """Function to calculate a discount factor from a date or a
        vector of dates. The day count determines how dates get converted to
        years. I allow this to default to ACT_ACT_ISDA unless specified."""

        times = times_from_dates(dt, self.value_dt, day_count)
        dfs = self.df_t(times)

        if isinstance(dfs, float):
            return dfs

        return np.array(dfs)

    ###########################################################################

    def df_t(self, t: Union[float, np.ndarray]):
        """Function to calculate a discount factor from a time or a
        vector of times. Discourage usage in favour of passing in dates."""

        if (
            self._interp_type is InterpTypes.FLAT_FWD_RATES
            or self._interp_type is InterpTypes.LINEAR_ZERO_RATES
            or self._interp_type is InterpTypes.LINEAR_FWD_RATES
        ):

            df = interpolate(
                t, self._times, self._dfs, self._interp_type.value
            )

        else:

            df = self._interpolator.interpolate(t)

        return df

    ###########################################################################

    def survival_prob(self, dt: Date):
        """This returns a survival probability to a specified date based on
        the assumption that the continuously compounded rate is a default
        hazard rate in which case the survival probability is directly
        analogous to a discount factor."""

        q = self.df(dt)
        return q

    ###########################################################################

    def fwd(self, dts: Date):
        """Calculate the continuously compounded forward rate at the forward
        Date provided. This is done by perturbing the time by one day only
        and measuring the change in the log of the discount factor divided by
        the time increment dt. I am assuming continuous compounding over the
        one date."""

        if isinstance(dts, Date):
            dts_plus_one_days = [dts.add_days(1)]
        else:
            dts_plus_one_days = []
            for dt in dts:
                dts_plus_one_day = dt.add_days(1)
                dts_plus_one_days.append(dts_plus_one_day)

        df1 = self.df(dts)
        df2 = self.df(dts_plus_one_days)
        dt = 1.0 / g_days_in_year
        fwd = np.log(df1 / df2) / (1.0 * dt)

        if isinstance(dts, Date):
            return fwd[0]
        else:
            return np.array(fwd)

    ###########################################################################

    def _fwd(self, times: Union[np.ndarray, float]):
        """Calculate the continuously compounded forward rate at the forward
        time provided. This is done by perturbing the time by a small amount
        and measuring the change in the log of the discount factor divided by
        the time increment dt."""

        dt = 1e-6
        times = np.maximum(times, dt)

        df1 = self.df_t(times - dt)
        df2 = self.df_t(times + dt)
        fwd = np.log(df1 / df2) / (2.0 * dt)
        return fwd

    ###########################################################################

    def bump(self, bump_size: float):
        """Adjust the continuously compounded forward rates by a perturbation
        upward equal to the bump size and return a curve objet with this bumped
        curve. This is used for interest rate risk."""

        times = self._times.copy()
        values = self._dfs.copy()

        n = len(self._times)
        for i in range(0, n):
            t = times[i]
            values[i] = values[i] * np.exp(-bump_size * t)

        disc_curve = DiscountCurve(
            self.value_dt, times, values, self._interp_type
        )

        return disc_curve

    ###########################################################################

    def fwd_rate(
        self,
        start_dt: Union[list, Date],
        date_or_tenor: Union[Date, str],
        dc_type: DayCountTypes = DayCountTypes.ACT_360,
    ):
        """Calculate the forward rate between two forward dates according to
        the specified day count convention. This defaults to Actual 360. The
        first date is specified and the second is given as a date or as a tenor
        which is added to the first date."""

        if isinstance(start_dt, Date):
            start_dts = []
            start_dts.append(start_dt)
        elif isinstance(start_dt, list):
            start_dts = start_dt
        else:
            raise FinError("Start date and end date must be same types.")

        day_count = DayCount(dc_type)

        num_dates = len(start_dts)
        fwd_rates = []
        for i in range(0, num_dates):
            dt1 = start_dts[i]

            if isinstance(date_or_tenor, str):
                dt2 = dt1.add_tenor(date_or_tenor)
            elif isinstance(date_or_tenor, Date):
                dt2 = date_or_tenor
            elif isinstance(date_or_tenor, list):
                dt2 = date_or_tenor[i]

            year_frac = day_count.year_frac(dt1, dt2)[0]
            df1 = self.df(dt1, day_count=DayCountTypes.ACT_365F)
            df2 = self.df(dt2, day_count=DayCountTypes.ACT_365F)
            fwd_rate = (df1 / df2 - 1.0) / year_frac
            fwd_rates.append(fwd_rate)

        if isinstance(start_dt, Date):
            return fwd_rates[0]
        else:
            return np.array(fwd_rates)

    ###########################################################################

    def __repr__(self):

        s = label_to_string("OBJECT TYPE", type(self).__name__)
        num_points = len(self._df_dates)
        s += label_to_string("DATES", "DISCOUNT FACTORS")
        for i in range(0, num_points):
            s += label_to_string(
                "%12s" % self._df_dates[i], "%12.8f" % self._dfs[i]
            )

        return s

    ###########################################################################

    def _print(self):
        """Simple print function for backward compatibility."""
        print(self)


###############################################################################
