import numpy as np

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
from .fx_vanilla_option import FXVanillaOption

###############################################################################


class BarrierTypes:
    """Barrier type definitions for knock options."""
    UP_OUT = "upout"
    UP_IN = "upin"
    DOWN_OUT = "downout"
    DOWN_IN = "downin"


###############################################################################


class FXKnockOption(FXOption):
    """
    FX Knock-In/Knock-Out Option (European Barrier Option at Expiry).

    Implements European-style barrier options that are observed only at
    expiry. The option uses static replication with vanilla and binary
    options.

    Barrier Types:
    - UP_OUT: Option knocked out if spot >= barrier at expiry (Call)
    - DOWN_OUT: Option knocked out if spot <= barrier at expiry (Put)
    - UP_IN: Option knocked in if spot >= barrier at expiry (Put)
    - DOWN_IN: Option knocked in if spot <= barrier at expiry (Call)

    Note: This is for European barriers observed at expiry only, not
    continuous monitoring barriers.
    """

    def __init__(
        self,
        expiry_dt: Date,
        strike_fx_rate: float,
        barrier_fx_rate: float,
        barrier_type: str,  # 'upout', 'upin', 'downout', 'downin'
        barrier_at_coupon: bool,  # Whether barrier includes equality
        currency_pair: str,  # FORDOM
        option_flavor: str,  # 'call' or 'put'
        notional: float,
        notional_currency: str,
        cal_type: CalendarTypes,
        spot_days: int = 0,
        coupon: float = 0.0,  # Rebate coupon if knocked out/in
        coupon_cash_settle: bool = True
    ):
        """
        Create an FX Knock Option.

        Parameters
        ----------
        expiry_dt : Date
            Option expiry date
        strike_fx_rate : float
            Strike FX rate
        barrier_fx_rate : float
            Barrier FX rate
        barrier_type : str
            Type of barrier: 'upout', 'upin', 'downout', 'downin'
        barrier_at_coupon : bool
            If True, barrier trigger includes equality (>=, <=)
        currency_pair : str
            Currency pair in FORDOM format
        option_flavor : str
            'call' or 'put'
        notional : float
            Notional amount
        notional_currency : str
            Currency of the notional
        cal_type : CalendarTypes
            Calendar type
        spot_days : int
            Settlement days
        coupon : float
            Rebate coupon amount (paid in domestic currency)
        coupon_cash_settle : bool
            If True, use spot for coupon FX conversion
        """
        check_argument_types(self.__init__, locals())

        super().__init__(currency_pair, cal_type)

        payment_dt = self.calendar.add_business_days(expiry_dt, spot_days)

        if payment_dt < expiry_dt:
            raise FinError("Payment date must be on or after expiry date.")

        if notional_currency != self.dom_name and notional_currency != self.for_name:
            raise FinError("Notional currency must be in currency pair.")

        barrier_type = barrier_type.lower()
        option_flavor = option_flavor.lower()

        if barrier_type not in [BarrierTypes.UP_OUT, BarrierTypes.UP_IN,
                                 BarrierTypes.DOWN_OUT, BarrierTypes.DOWN_IN]:
            raise FinError(f"Invalid barrier type: {barrier_type}")

        if option_flavor not in ['call', 'put']:
            raise FinError("Option flavor must be 'call' or 'put'")

        # Validate barrier vs strike relationship
        if option_flavor == 'call':
            if barrier_fx_rate <= strike_fx_rate:
                raise FinError("For call options, barrier must be > strike")
        else:  # put
            if barrier_fx_rate >= strike_fx_rate:
                raise FinError("For put options, barrier must be < strike")

        self.expiry_dt = expiry_dt
        self.payment_dt = payment_dt
        self.strike_fx_rate = strike_fx_rate
        self.barrier_fx_rate = barrier_fx_rate
        self.barrier_type = barrier_type
        self.barrier_at_coupon = barrier_at_coupon
        self.option_flavor = option_flavor
        self.notional = notional
        self.notional_currency = notional_currency
        self.spot_days = spot_days
        self.coupon = coupon
        self.coupon_cash_settle = coupon_cash_settle

        # Convert notional to foreign currency units
        if notional_currency == self.dom_name:
            notional_for = notional / strike_fx_rate
        else:
            notional_for = notional

        # Determine option type for components
        if option_flavor == 'call':
            option_type = OptionTypes.EUROPEAN_CALL
        else:
            option_type = OptionTypes.EUROPEAN_PUT

        # Calculate the barrier-strike difference for the binary
        diff = abs(barrier_fx_rate - strike_fx_rate)

        # Determine the equivalent barrier type for replication logic
        if barrier_type in [BarrierTypes.UP_OUT, BarrierTypes.DOWN_IN]:
            barrier_type_equal = BarrierTypes.UP_OUT
            if coupon != 0:
                self.digital_coupon = FXBinaryOption(
                    expiry_dt, barrier_fx_rate, currency_pair,
                    OptionTypes.BINARY_CALL, coupon, self.dom_name,
                    barrier_at_coupon, cal_type, spot_days,
                    cash_settle=coupon_cash_settle
                )
        else:  # UP_IN, DOWN_OUT
            barrier_type_equal = BarrierTypes.UP_IN
            if coupon != 0:
                self.digital_coupon = FXBinaryOption(
                    expiry_dt, barrier_fx_rate, currency_pair,
                    OptionTypes.BINARY_PUT, coupon, self.dom_name,
                    barrier_at_coupon, cal_type, spot_days,
                    cash_settle=coupon_cash_settle
                )

        # Static replication setup
        # Option type 1: barrier_type_equal matches option_flavor direction
        # (upout call, upin put) -> replicate with vanilla_strike - vanilla_barrier - digital_diff
        # Option type 0: barrier_type_equal opposite to option_flavor direction
        # (upout put, upin call, etc) -> replicate with vanilla_barrier + digital_diff

        if ((barrier_type_equal == BarrierTypes.UP_OUT and option_flavor == 'call') or
            (barrier_type_equal == BarrierTypes.UP_IN and option_flavor == 'put')):
            self.option_type_flag = 1

            # Digital for the barrier-strike difference
            if option_flavor == 'call':
                digital_type = OptionTypes.BINARY_CALL
            else:
                digital_type = OptionTypes.BINARY_PUT

            self.digital_diff = FXBinaryOption(
                expiry_dt, barrier_fx_rate, currency_pair, digital_type,
                diff * notional_for, self.dom_name, barrier_at_coupon,
                cal_type, spot_days, cash_settle=True
            )

            # Vanilla at barrier
            self.vanilla_barrier = FXVanillaOption(
                expiry_dt, barrier_fx_rate, currency_pair, option_type,
                notional_for, self.for_name, cal_type, spot_days,
                get_fwd_method='spot'
            )

            # Vanilla at strike
            self.vanilla_strike = FXVanillaOption(
                expiry_dt, strike_fx_rate, currency_pair, option_type,
                notional_for, self.for_name, cal_type, spot_days,
                get_fwd_method='spot'
            )
        else:
            self.option_type_flag = 0

            # Digital for the barrier-strike difference
            if option_flavor == 'call':
                digital_type = OptionTypes.BINARY_CALL
            else:
                digital_type = OptionTypes.BINARY_PUT

            self.digital_diff = FXBinaryOption(
                expiry_dt, barrier_fx_rate, currency_pair, digital_type,
                diff * notional_for, self.dom_name, (not barrier_at_coupon),
                cal_type, spot_days, cash_settle=True
            )

            # Vanilla at barrier
            self.vanilla_barrier = FXVanillaOption(
                expiry_dt, barrier_fx_rate, currency_pair, option_type,
                notional_for, self.for_name, cal_type, spot_days,
                get_fwd_method='spot'
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
        Calculate the value of the FX Knock Option using static replication.

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

        if value_dt > self.expiry_dt:
            return {"value": 0.0}

        qty = self.vanilla_barrier.notional

        if self.option_type_flag == 1:
            # vanilla_strike - vanilla_barrier - digital_diff
            npv_strike = self.vanilla_strike.value(
                value_dt, forward_curve, domestic_curve, vol_surface, dc_type
            )
            npv_barrier = self.vanilla_barrier.value(
                value_dt, forward_curve, domestic_curve, vol_surface, dc_type
            )
            npv_digital = self.digital_diff.value(
                value_dt, forward_curve, domestic_curve, vol_surface, dc_type
            )
            npv = (npv_strike["value"] - npv_barrier["value"]) * qty - npv_digital["value"]
        else:
            # vanilla_barrier + digital_diff
            npv_barrier = self.vanilla_barrier.value(
                value_dt, forward_curve, domestic_curve, vol_surface, dc_type
            )
            npv_digital = self.digital_diff.value(
                value_dt, forward_curve, domestic_curve, vol_surface, dc_type
            )
            # Vanilla value needs to be multiplied by qty
            npv = npv_barrier["value"] * qty + npv_digital["value"]

        # Add rebate coupon if any
        if self.coupon != 0:
            npv_coupon = self.digital_coupon.value(
                value_dt, forward_curve, domestic_curve, vol_surface, dc_type
            )
            npv += npv_coupon["value"]

        return {"value": npv}

    ###########################################################################

    def __repr__(self):
        s = label_to_string("OBJECT TYPE", type(self).__name__)
        s += label_to_string("EXPIRY DATE", self.expiry_dt)
        s += label_to_string("CURRENCY PAIR", self.currency_pair)
        s += label_to_string("STRIKE FX RATE", self.strike_fx_rate)
        s += label_to_string("BARRIER FX RATE", self.barrier_fx_rate)
        s += label_to_string("BARRIER TYPE", self.barrier_type)
        s += label_to_string("OPTION FLAVOR", self.option_flavor)
        s += label_to_string("NOTIONAL", self.notional)
        s += label_to_string("NOTIONAL CURRENCY", self.notional_currency)
        s += label_to_string("COUPON", self.coupon)
        s += label_to_string("SPOT DAYS", self.spot_days, "")
        return s


###############################################################################
