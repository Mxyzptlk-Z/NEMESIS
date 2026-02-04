import numpy as np
import pandas as pd

from ...market.curves.discount_curve import DiscountCurve
from ...market.curves.forward_curve import ForwardCurve
from ...market.volatility.vol_surface import VolSurface
from ...utils.calendar import Calendar, CalendarTypes
from ...utils.date import Date
from ...utils.day_count import DayCount, DayCountTypes
from ...utils.error import FinError
from ...utils.global_types import OptionTypes
from ...utils.helpers import check_argument_types, label_to_string
from .fx_digital_option import FXBinaryOption
from .fx_option import FXOption

###############################################################################


class FXRangeDigitalOption(FXOption):
    """
    FX Range Digital Option.

    Pays a coupon if the spot rate at expiry is within a specified range.
    This is implemented as a combination of binary options.

    Range types:
    - If range_down == -inf: Single upper barrier (pays if spot < range_up)
    - If range_up == inf: Single lower barrier (pays if spot > range_down)
    - Otherwise: Double barrier range (pays if range_down < spot < range_up)
    """

    def __init__(
        self,
        expiry_dt: Date,
        range_down: float,  # Lower bound (-inf for none)
        range_up: float,    # Upper bound (inf for none)
        down_in: bool,      # Include lower bound (>=)
        up_in: bool,        # Include upper bound (<=)
        range_coupon: float,  # Coupon if in range
        currency_pair: str,
        cash_currency: str,
        cal_type: CalendarTypes,
        spot_days: int = 0,
        payment_dt: Date | None = None,
        cash_settle: bool = True
    ):
        """
        Create an FX Range Digital Option.

        Parameters
        ----------
        expiry_dt : Date
            Option expiry date
        range_down : float
            Lower bound of the range (use float('-inf') for no lower bound)
        range_up : float
            Upper bound of the range (use float('inf') for no upper bound)
        down_in : bool
            If True, pay when spot >= range_down
        up_in : bool
            If True, pay when spot <= range_up
        range_coupon : float
            Coupon paid if spot is within range
        currency_pair : str
            Currency pair in FORDOM format
        cash_currency : str
            Currency of the coupon payment
        cal_type : CalendarTypes
            Calendar type
        spot_days : int
            Settlement days
        payment_dt : Date, optional
            Direct payment date (if provided, spot_days is ignored)
        cash_settle : bool
            Cash settlement mode
        """
        check_argument_types(self.__init__, locals())

        super().__init__(currency_pair, cal_type)

        if range_down >= range_up:
            raise FinError("Range up must be greater than range down")

        calendar = Calendar(cal_type)
        if payment_dt is None:
            payment_dt = calendar.add_business_days(expiry_dt, spot_days)

        if payment_dt < expiry_dt:
            raise FinError("Payment date must be on or after expiry date.")

        if cash_currency != self.dom_name and cash_currency != self.for_name:
            raise FinError("Cash currency must be in currency pair.")

        self.expiry_dt = expiry_dt
        self.payment_dt = payment_dt
        self.range_down = range_down
        self.range_up = range_up
        self.down_in = down_in
        self.up_in = up_in
        self.range_coupon = range_coupon
        self.cash_currency = cash_currency
        self.spot_days = spot_days
        self.cash_settle = cash_settle

        # Create component binary options
        self.digs = []

        if range_down == float('-inf'):
            # Only upper barrier: pays if spot < range_up (or <= if up_in)
            dig_put = FXBinaryOption(
                expiry_dt, range_up, currency_pair, OptionTypes.BINARY_PUT,
                range_coupon, cash_currency, up_in, cal_type, spot_days,
                payment_dt, cash_settle
            )
            self.digs = [dig_put]

        elif range_up == float('inf'):
            # Only lower barrier: pays if spot > range_down (or >= if down_in)
            dig_call = FXBinaryOption(
                expiry_dt, range_down, currency_pair, OptionTypes.BINARY_CALL,
                range_coupon, cash_currency, down_in, cal_type, spot_days,
                payment_dt, cash_settle
            )
            self.digs = [dig_call]

        else:
            # Double barrier: pays if range_down < spot < range_up
            # Implemented as: long call at range_down, short call at range_up
            dig_call_1 = FXBinaryOption(
                expiry_dt, range_down, currency_pair, OptionTypes.BINARY_CALL,
                range_coupon, cash_currency, down_in, cal_type, spot_days,
                payment_dt, cash_settle
            )
            dig_call_2 = FXBinaryOption(
                expiry_dt, range_up, currency_pair, OptionTypes.BINARY_CALL,
                range_coupon, cash_currency, (not up_in), cal_type, spot_days,
                payment_dt, cash_settle
            )
            self.digs = [dig_call_1, dig_call_2]
            self._dig_signs = [1, -1]  # Long first, short second

    ###########################################################################

    def value(
        self,
        value_dt: Date,
        forward_curve: ForwardCurve,
        domestic_curve: DiscountCurve,
        vol_surface: VolSurface,
        dc_type: DayCountTypes
    ):
        """
        Calculate the value of the FX Range Digital Option.
        """
        if not isinstance(value_dt, Date):
            raise FinError("Valuation date is not a Date")

        if value_dt > self.expiry_dt:
            return {"value": 0.0}

        npv = 0.0

        if len(self.digs) == 1:
            # Single barrier case
            npv = self.digs[0].value(
                value_dt, forward_curve, domestic_curve, vol_surface, dc_type
            )["value"]
        else:
            # Double barrier case
            for i, dig in enumerate(self.digs):
                sign = self._dig_signs[i]
                npv_dig = dig.value(
                    value_dt, forward_curve, domestic_curve, vol_surface, dc_type
                )["value"]
                npv += sign * npv_dig

        return {"value": npv}

    ###########################################################################

    def __repr__(self):
        s = label_to_string("OBJECT TYPE", type(self).__name__)
        s += label_to_string("EXPIRY DATE", self.expiry_dt)
        s += label_to_string("CURRENCY PAIR", self.currency_pair)
        s += label_to_string("RANGE DOWN", self.range_down)
        s += label_to_string("RANGE UP", self.range_up)
        s += label_to_string("DOWN IN", self.down_in)
        s += label_to_string("UP IN", self.up_in)
        s += label_to_string("RANGE COUPON", self.range_coupon)
        s += label_to_string("CASH CURRENCY", self.cash_currency)
        s += label_to_string("SPOT DAYS", self.spot_days, "")
        return s


###############################################################################


class FXRangeAccrualOption(FXOption):
    """
    FX Range Accrual Option.

    A product that pays based on the number of observation days the spot
    rate is within a specified range. The final payout is:

    Payout = (in_count * range_in_coupon + out_count * range_out_coupon) / total_obs_days

    where in_count is the number of days spot is in range and out_count
    is the number of days spot is out of range.
    """

    def __init__(
        self,
        obs_schedule: list,  # List of observation dates
        payment_dt: Date,
        range_down: float,
        range_up: float,
        down_in: bool,
        up_in: bool,
        range_in_coupon: float,   # Coupon when in range
        range_out_coupon: float,  # Coupon when out of range
        currency_pair: str,
        cash_currency: str,
        fx_fixing: pd.Series,  # Historical FX fixing data
        cal_type: CalendarTypes,
        cash_settle: bool = True
    ):
        """
        Create an FX Range Accrual Option.

        Parameters
        ----------
        obs_schedule : list
            List of observation dates (Date objects)
        payment_dt : Date
            Payment date
        range_down : float
            Lower bound of the range
        range_up : float
            Upper bound of the range
        down_in : bool
            Include lower bound when checking range
        up_in : bool
            Include upper bound when checking range
        range_in_coupon : float
            Total coupon if in range for all days
        range_out_coupon : float
            Total coupon if out of range for all days
        currency_pair : str
            Currency pair in FORDOM format
        cash_currency : str
            Currency of the payment
        fx_fixing : pd.Series
            Historical FX fixing data (index=date, values=fx rate)
        cal_type : CalendarTypes
            Calendar type
        cash_settle : bool
            Cash settlement mode
        """
        check_argument_types(self.__init__, locals())

        super().__init__(currency_pair, cal_type)

        if range_down >= range_up:
            raise FinError("Range up must be greater than range down")

        if len(obs_schedule) == 0:
            raise FinError("Observation schedule cannot be empty")

        # Convert obs_schedule to list if needed
        if isinstance(obs_schedule, np.ndarray):
            obs_schedule = list(obs_schedule)

        if obs_schedule[-1] > payment_dt:
            raise FinError("Last observation date must be on or before payment date")

        if cash_currency != self.dom_name and cash_currency != self.for_name:
            raise FinError("Cash currency must be in currency pair.")

        self.obs_schedule = obs_schedule
        self.payment_dt = payment_dt
        self.range_down = range_down
        self.range_up = range_up
        self.down_in = down_in
        self.up_in = up_in
        self.range_in_coupon = range_in_coupon
        self.range_out_coupon = range_out_coupon
        self.cash_currency = cash_currency
        self.fx_fixing = fx_fixing
        self.cash_settle = cash_settle

    ###########################################################################

    def _check_in_range(self, price: float) -> bool:
        """
        Check if a price is within the range.

        Parameters
        ----------
        price : float
            FX rate to check

        Returns
        -------
        bool
            True if price is in range
        """
        if self.range_down < price < self.range_up:
            return True
        elif price == self.range_down and self.down_in:
            return True
        elif price == self.range_up and self.up_in:
            return True
        else:
            return False

    ###########################################################################

    def value(
        self,
        value_dt: Date,
        forward_curve: ForwardCurve,
        domestic_curve: DiscountCurve,
        vol_surface: VolSurface,
        dc_type: DayCountTypes
    ):
        """
        Calculate the value of the FX Range Accrual Option.

        Parameters
        ----------
        value_dt : Date
            Valuation date
        forward_curve : ForwardCurve
            FX forward curve
        domestic_curve : DiscountCurve
            Domestic currency discount curve
        vol_surface : VolSurface
            FX volatility surface
        dc_type : DayCountTypes
            Day count type

        Returns
        -------
        dict
            Dictionary containing option value
        """
        if not isinstance(value_dt, Date):
            raise FinError("Valuation date is not a Date")

        if value_dt > self.obs_schedule[-1]:
            # After last observation, value is 0
            return {"value": 0.0}

        # Handle case where observation has started but no fixing data
        fx_fixing = self.fx_fixing
        if value_dt >= self.obs_schedule[0] and len(self.fx_fixing) == 0:
            fx_fixing = pd.Series(
                data=[forward_curve.spot_rate],
                index=[value_dt]
            )

        total_obs_count = len(self.obs_schedule)

        # Discount factor from payment date
        dom_df = domestic_curve.df(self.payment_dt, dc_type) / domestic_curve.df(value_dt, dc_type)

        # Determine the forward price date for asset-or-nothing valuation
        if self.cash_settle:
            atm_pay_dt = self.obs_schedule[-1]
        else:
            atm_pay_dt = self.payment_dt
        atm_pay = forward_curve.get_forward(atm_pay_dt, dc_type)

        in_count = 0.0
        out_count = 0.0

        for obs_dt in self.obs_schedule:
            if obs_dt <= value_dt:
                # Past observation: use historical fixing
                try:
                    # Find the most recent fixing on or before obs_dt
                    valid_fixings = fx_fixing[fx_fixing.index <= obs_dt]
                    if len(valid_fixings) == 0:
                        raise FinError(f'Missing FX fixing data for {obs_dt}')
                    price_observed = valid_fixings.iloc[-1]
                except Exception as e:
                    raise FinError(f'Missing FX fixing data for {obs_dt}')

                if self._check_in_range(price_observed):
                    in_count += 1
                else:
                    out_count += 1
            else:
                # Future observation: use range digital probability
                unit_range_dig = FXRangeDigitalOption(
                    obs_dt, self.range_down, self.range_up,
                    self.down_in, self.up_in, 1.0,
                    self.currency_pair, self.cash_currency,
                    self.cal_type, 0, atm_pay_dt, False
                )

                unit_pv = unit_range_dig.value(
                    value_dt, forward_curve, domestic_curve, vol_surface, dc_type
                )["value"]

                # Calculate unit discount factor
                unit_df = domestic_curve.df(atm_pay_dt, dc_type) / domestic_curve.df(value_dt, dc_type)

                # Convert to probability
                if self.cash_currency == self.for_name:
                    # Asset-or-nothing: divide by forward and df
                    unit_prob = unit_pv / unit_df / atm_pay
                else:
                    # Cash-or-nothing: just divide by df
                    unit_prob = unit_pv / unit_df

                in_count += unit_prob
                out_count += (1 - unit_prob)

        # Calculate final payout
        npv = (self.range_in_coupon * in_count + self.range_out_coupon * out_count) / total_obs_count * dom_df

        # Convert to foreign currency if needed
        if self.cash_currency == self.for_name:
            npv = npv * atm_pay

        return {"value": npv}

    ###########################################################################

    def get_accrual_counts(
        self,
        value_dt: Date,
        forward_curve: ForwardCurve
    ):
        """
        Get the current in/out counts for reporting.

        Parameters
        ----------
        value_dt : Date
            Valuation date
        forward_curve : ForwardCurve
            FX forward curve (for current spot if needed)

        Returns
        -------
        dict
            Dictionary with in_count and out_count
        """
        fx_fixing = self.fx_fixing
        if value_dt >= self.obs_schedule[0] and len(self.fx_fixing) == 0:
            fx_fixing = pd.Series(
                data=[forward_curve.spot_rate],
                index=[value_dt]
            )

        in_count = 0
        out_count = 0

        for obs_dt in self.obs_schedule:
            if obs_dt <= value_dt:
                try:
                    valid_fixings = fx_fixing[fx_fixing.index <= obs_dt]
                    if len(valid_fixings) == 0:
                        continue
                    price_observed = valid_fixings.iloc[-1]
                except:
                    continue

                if self._check_in_range(price_observed):
                    in_count += 1
                else:
                    out_count += 1

        return {"in_count": in_count, "out_count": out_count}

    ###########################################################################

    def __repr__(self):
        s = label_to_string("OBJECT TYPE", type(self).__name__)
        s += label_to_string("CURRENCY PAIR", self.currency_pair)
        s += label_to_string("PAYMENT DATE", self.payment_dt)
        s += label_to_string("RANGE DOWN", self.range_down)
        s += label_to_string("RANGE UP", self.range_up)
        s += label_to_string("DOWN IN", self.down_in)
        s += label_to_string("UP IN", self.up_in)
        s += label_to_string("RANGE IN COUPON", self.range_in_coupon)
        s += label_to_string("RANGE OUT COUPON", self.range_out_coupon)
        s += label_to_string("CASH CURRENCY", self.cash_currency)
        s += label_to_string("OBS COUNT", len(self.obs_schedule), "")
        return s


###############################################################################
