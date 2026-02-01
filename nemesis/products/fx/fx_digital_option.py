###############################################################################
# FX Digital/Binary Options
# Implements cash-or-nothing and asset-or-nothing binary options
###############################################################################

import numpy as np

from ...utils.calendar import Calendar, CalendarTypes
from ...utils.date import Date
from ...utils.day_count import DayCount, DayCountTypes
from ...utils.error import FinError
from ...utils.global_types import OptionTypes
from ...utils.helpers import check_argument_types, label_to_string
from ...models.black_analytic import cash_or_nothing, asset_or_nothing
from ...market.curves.discount_curve import DiscountCurve
from ...market.curves.forward_curve import ForwardCurve
from ...market.volatility.vol_surface import VolSurface

from .fx_option import FXOption


###############################################################################


class FXBinaryOption(FXOption):
    """
    FX Binary Option (Cash-or-Nothing or Asset-or-Nothing).
    
    A binary option pays a fixed cash amount (cash-or-nothing) or the 
    underlying asset value (asset-or-nothing) if the option expires 
    in the money.
    """

    def __init__(
        self,
        expiry_dt: Date,
        strike_fx_rate: float,
        currency_pair: str,  # FORDOM
        option_type: OptionTypes,  # BINARY_CALL or BINARY_PUT
        cash: float,  # Cash amount to pay
        cash_currency: str,  # Currency of the cash payment
        pay_on_equal: bool,  # Whether to pay when spot == strike
        cal_type: CalendarTypes,
        spot_days: int = 0,
        cash_settle: bool = True  # Cash settlement mode
    ):
        """
        Create an FX Binary Option.

        Parameters
        ----------
        expiry_dt : Date
            Option expiry date
        strike_fx_rate : float
            Strike FX rate (domestic per foreign)
        currency_pair : str
            Currency pair in FORDOM format (e.g., 'EURUSD')
        option_type : OptionTypes
            BINARY_CALL or BINARY_PUT
        cash : float
            Cash amount to pay if option expires ITM
        cash_currency : str
            Currency of the cash payment (must be FOR or DOM)
        pay_on_equal : bool
            If True, pay when spot == strike
        cal_type : CalendarTypes
            Calendar type for business day calculations
        spot_days : int
            Settlement days after expiry
        cash_settle : bool
            If True, use spot rate at expiry for FX conversion
        """
        check_argument_types(self.__init__, locals())

        super().__init__(currency_pair, cal_type)

        calendar = Calendar(cal_type)
        payment_dt = calendar.add_business_days(expiry_dt, spot_days)

        if payment_dt < expiry_dt:
            raise FinError("Payment date must be on or after expiry date.")

        if len(currency_pair) != 6:
            raise FinError("Currency pair must be 6 characters.")

        if cash_currency != self.dom_name and cash_currency != self.for_name:
            raise FinError("Cash currency must be in currency pair.")

        if (
            option_type != OptionTypes.BINARY_CALL
            and option_type != OptionTypes.BINARY_PUT
        ):
            raise FinError("Option type must be BINARY_CALL or BINARY_PUT")

        if np.any(strike_fx_rate < 0.0):
            raise FinError("Negative strike.")

        self.expiry_dt = expiry_dt
        self.payment_dt = payment_dt
        self.strike_fx_rate = strike_fx_rate
        self.option_type = option_type
        self.cash = cash
        self.cash_currency = cash_currency
        self.pay_on_equal = pay_on_equal
        self.spot_days = spot_days
        self.cash_settle = cash_settle

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
        Calculate the value of the FX Binary Option.

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
            Dictionary containing option value and related metrics
        """
        if not isinstance(value_dt, Date):
            raise FinError("Valuation date is not a Date")

        if value_dt > self.expiry_dt:
            # After expiry, value is 0
            return {"value": 0.0}

        day_count = DayCount(dc_type)
        t_exp = day_count.year_frac(value_dt, self.expiry_dt)[0]

        dom_df = domestic_curve.df(self.payment_dt, dc_type) / domestic_curve.df(value_dt, dc_type)

        # On expiry date, calculate final payment
        if value_dt == self.expiry_dt:
            spot = forward_curve.spot_rate
            if self.option_type == OptionTypes.BINARY_CALL:
                if spot > self.strike_fx_rate:
                    npv = self.cash * dom_df
                elif spot == self.strike_fx_rate and self.pay_on_equal:
                    npv = self.cash * dom_df
                else:
                    npv = 0.0
            else:  # BINARY_PUT
                if spot < self.strike_fx_rate:
                    npv = self.cash * dom_df
                elif spot == self.strike_fx_rate and self.pay_on_equal:
                    npv = self.cash * dom_df
                else:
                    npv = 0.0

            # Convert if cash is in foreign currency
            if self.cash_currency == self.for_name:
                if self.cash_settle:
                    atm_pay = forward_curve.get_forward_spot(self.expiry_dt, dc_type)
                else:
                    atm_pay = forward_curve.get_forward(self.payment_dt, dc_type)
                npv = npv * atm_pay

            return {"value": npv}

        # Before expiry, use Black model
        t_exp = np.maximum(t_exp, 1e-10)
        r_d = -np.log(dom_df) / t_exp

        fwd = forward_curve.get_forward_spot(self.expiry_dt, dc_type)
        volatility = vol_surface.interp_vol(self.expiry_dt, self.strike_fx_rate)

        if np.any(volatility < 0.0):
            raise FinError("Volatility should not be negative.")

        v = np.maximum(volatility, 1e-10)

        if self.cash_currency == self.for_name:
            # Asset-or-nothing
            if self.cash_settle:
                atm_pay = forward_curve.get_forward_spot(self.expiry_dt, dc_type)
            else:
                atm_pay = forward_curve.get_forward(self.payment_dt, dc_type)
            npv = self.cash * asset_or_nothing(
                fwd, t_exp, self.strike_fx_rate, r_d, v, atm_pay, self.option_type
            )
        else:
            # Cash-or-nothing
            npv = cash_or_nothing(
                fwd, t_exp, self.strike_fx_rate, r_d, v, self.cash, self.option_type
            )

        return {"value": npv}

    ###########################################################################

    def __repr__(self):
        s = label_to_string("OBJECT TYPE", type(self).__name__)
        s += label_to_string("EXPIRY DATE", self.expiry_dt)
        s += label_to_string("CURRENCY PAIR", self.currency_pair)
        s += label_to_string("STRIKE FX RATE", self.strike_fx_rate)
        s += label_to_string("OPTION TYPE", self.option_type)
        s += label_to_string("CASH", self.cash)
        s += label_to_string("CASH CURRENCY", self.cash_currency)
        s += label_to_string("PAY ON EQUAL", self.pay_on_equal)
        s += label_to_string("SPOT DAYS", self.spot_days, "")
        return s


###############################################################################


class FXDigitalOption(FXOption):
    """
    FX Digital Option with different payoffs above and below the strike.
    
    This is implemented as a combination of two binary options:
    - A put binary paying coupon_left when spot < strike
    - A call binary paying coupon_right when spot > strike
    """

    def __init__(
        self,
        expiry_dt: Date,
        strike_fx_rate: float,
        currency_pair: str,  # FORDOM
        left_in: bool,  # If True, pay coupon_left when spot <= strike
        coupon_left: float,  # Coupon when spot < strike (or <= if left_in)
        coupon_right: float,  # Coupon when spot > strike (or >= if not left_in)
        cash_currency: str,
        cal_type: CalendarTypes,
        spot_days: int = 0,
        cash_settle: bool = True
    ):
        """
        Create an FX Digital Option.

        Parameters
        ----------
        expiry_dt : Date
            Option expiry date
        strike_fx_rate : float
            Strike FX rate
        currency_pair : str
            Currency pair in FORDOM format
        left_in : bool
            If True, pay coupon_left when spot <= strike
        coupon_left : float
            Payment when spot is below strike
        coupon_right : float
            Payment when spot is above strike
        cash_currency : str
            Currency of the payment
        cal_type : CalendarTypes
            Calendar type
        spot_days : int
            Settlement days
        cash_settle : bool
            Cash settlement mode
        """
        check_argument_types(self.__init__, locals())

        super().__init__(currency_pair, cal_type)

        calendar = Calendar(cal_type)
        payment_dt = calendar.add_business_days(expiry_dt, spot_days)

        if payment_dt < expiry_dt:
            raise FinError("Payment date must be on or after expiry date.")

        if cash_currency != self.dom_name and cash_currency != self.for_name:
            raise FinError("Cash currency must be in currency pair.")

        self.expiry_dt = expiry_dt
        self.payment_dt = payment_dt
        self.strike_fx_rate = strike_fx_rate
        self.left_in = left_in
        self.coupon_left = coupon_left
        self.coupon_right = coupon_right
        self.cash_currency = cash_currency
        self.spot_days = spot_days
        self.cash_settle = cash_settle

        # Create component binary options
        self.binary_left = FXBinaryOption(
            expiry_dt, strike_fx_rate, currency_pair, OptionTypes.BINARY_PUT,
            coupon_left, cash_currency, left_in, cal_type, spot_days, cash_settle
        )
        self.binary_right = FXBinaryOption(
            expiry_dt, strike_fx_rate, currency_pair, OptionTypes.BINARY_CALL,
            coupon_right, cash_currency, (not left_in), cal_type, spot_days, cash_settle
        )

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
        Calculate the value of the FX Digital Option.
        """
        npv_left = self.binary_left.value(
            value_dt, forward_curve, domestic_curve, vol_surface, dc_type
        )
        npv_right = self.binary_right.value(
            value_dt, forward_curve, domestic_curve, vol_surface, dc_type
        )

        return {"value": npv_left["value"] + npv_right["value"]}

    ###########################################################################

    def __repr__(self):
        s = label_to_string("OBJECT TYPE", type(self).__name__)
        s += label_to_string("EXPIRY DATE", self.expiry_dt)
        s += label_to_string("CURRENCY PAIR", self.currency_pair)
        s += label_to_string("STRIKE FX RATE", self.strike_fx_rate)
        s += label_to_string("LEFT IN", self.left_in)
        s += label_to_string("COUPON LEFT", self.coupon_left)
        s += label_to_string("COUPON RIGHT", self.coupon_right)
        s += label_to_string("CASH CURRENCY", self.cash_currency)
        s += label_to_string("SPOT DAYS", self.spot_days, "")
        return s


###############################################################################
