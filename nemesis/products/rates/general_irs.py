import numpy as np
from typing import Union

from ...utils.error import FinError
from ...utils.date import Date
from ...utils.day_count import DayCountTypes
from ...utils.frequency import FrequencyTypes
from ...utils.calendar import CalendarTypes, DateGenRuleTypes
from ...utils.calendar import Calendar, BusDayAdjustTypes
from ...utils.helpers import check_argument_types, label_to_string
from ...utils.math import ONE_MILLION
from ...utils.global_types import SwapTypes
from ...market.curves.discount_curve import DiscountCurve
from .ql_curve import QLCurve

from .swap_fixed_leg import SwapFixedLeg
from .swap_float_leg import SwapFloatLeg

###############################################################################

from enum import Enum


class FinCompoundingTypes(Enum):
    COMPOUNDED = 1
    OVERNIGHT_COMPOUNDED_ANNUAL_RATE = 2
    AVERAGED = 3
    AVERAGED_DAILY = 4


###############################################################################


class GeneralSwap:
    """Class for managing overnight index rate swaps (OIS) and Fed Fund swaps.
    This is a contract in which a fixed payment leg is exchanged for a payment
    which pays the rolled-up overnight index rate (OIR). There is no exchange
    of par. The contract is entered into at zero initial cost.

    NOTE: This class is almost identical to IborSwap but will possibly
    deviate as distinctions between the two become clear to me. If not they
    will be converged (or inherited) to avoid duplication.

    The contract lasts from a start date to a specified maturity date.
    The fixed cpn is the OIS fixed rate for the corresponding tenor which is
    set at contract initiation.

    The floating rate is not known fully until the end of each payment period.
    It's calculated at the contract maturity and is based on daily observations
    of the overnight index rate which are compounded according to a specific
    convention. Hence the OIS floating rate is determined by the history of the
    OIS rates.

    In its simplest form, there is just one fixed rate payment and one floating
    rate payment at contract maturity. However when the contract becomes longer
    than one year the floating and fixed payments become periodic, usually with
    annual exchanges of cash.

    The value of the contract is the NPV of the two cpn streams. Discounting
    is done on the OIS curve which is itself implied by the term structure of
    market OIS rates."""

    def __init__(
        self,
        effective_dt: Date,  # Date interest starts to accrue
        term_dt_or_tenor: Union[Date, str],  # Date contract ends
        fixed_leg_type: SwapTypes,
        fixed_cpn: float,  # Fixed cpn (annualised)
        fixed_freq_type: FrequencyTypes,
        fixed_dc_type: DayCountTypes,
        notional: float = ONE_MILLION,
        payment_lag: int = 0,  # Number of days after period payment occurs
        float_multiplier: float = 1.0,
        float_spread: float = 0.0,
        float_compounding_type: str = 'ExcludeSprd',
        float_freq_type: FrequencyTypes = FrequencyTypes.ANNUAL,
        float_dc_type: DayCountTypes = DayCountTypes.THIRTY_E_360,
        cal_type: CalendarTypes = CalendarTypes.WEEKEND,
        bd_type: BusDayAdjustTypes = BusDayAdjustTypes.FOLLOWING,
        dg_type: DateGenRuleTypes = DateGenRuleTypes.BACKWARD,
        reset_freq: str = 'None',
        fixing_days: int = 0,
        end_of_month: bool = False,
        is_ois_leg: bool = False,
    ):
        """Create an overnight index swap contract giving the contract start
        date, its maturity, fixed cpn, fixed leg frequency, fixed leg day
        count convention and notional. The floating leg parameters have default
        values that can be overwritten if needed. The start date is contractual
        and is the same as the settlement date for a new swap. It is the date
        on which interest starts to accrue. The end of the contract is the
        termination date. This is not adjusted for business days. The adjusted
        termination date is called the maturity date. This is calculated."""

        check_argument_types(self.__init__, locals())

        if isinstance(term_dt_or_tenor, Date):
            self.termination_dt = term_dt_or_tenor
        else:
            self.termination_dt = effective_dt.add_tenor(term_dt_or_tenor)

        calendar = Calendar(cal_type)
        self.maturity_dt = calendar.adjust(self.termination_dt, bd_type)

        if effective_dt > self.maturity_dt:
            raise FinError("Start date after maturity date")

        self.effective_dt = effective_dt

        float_leg_type = SwapTypes.PAY
        if fixed_leg_type == SwapTypes.PAY:
            float_leg_type = SwapTypes.RECEIVE

        principal = 0.0

        self.fixed_leg = SwapFixedLeg(
            effective_dt,
            self.termination_dt,
            fixed_leg_type,
            fixed_cpn,
            fixed_freq_type,
            fixed_dc_type,
            notional,
            principal,
            payment_lag,
            cal_type,
            bd_type,
            dg_type,
            end_of_month
        )

        self.float_leg = SwapFloatLeg(
            effective_dt,
            self.termination_dt,
            float_leg_type,
            float_multiplier,
            float_spread,
            float_compounding_type,
            float_freq_type,
            float_dc_type,
            notional,
            principal,
            payment_lag,
            cal_type,
            bd_type,
            dg_type,
            reset_freq,
            fixing_days,
            end_of_month,
            is_ois_leg,
        )

    ###########################################################################

    def value(
        self, value_dt: Date, index_curve: DiscountCurve, discount_curve: DiscountCurve
    ):
        """Value the interest rate swap on a value date given an index
        curve and a disocunt curve."""

        fixed_leg_value = self.fixed_leg.value(value_dt, discount_curve)

        float_leg_value = self.float_leg.value(
            value_dt, index_curve, discount_curve
        )

        value = fixed_leg_value + float_leg_value
        return value

    ###########################################################################

    def pv01(self, value_dt, discount_curve):
        """Calculate the value of 1 basis point cpn on the fixed leg."""

        pv = self.fixed_leg.value(value_dt, discount_curve)
        pv01 = pv / self.fixed_leg.cpn / self.fixed_leg.notional

        # Needs to be positive even if it is a payer leg and/or cpn < 0
        pv01 = np.abs(pv01)
        return pv01

    ###########################################################################

    def swap_rate(self, value_dt, index_curve, discount_curve):
        """Calculate the fixed leg cpn that makes the swap worth zero.
        If the valuation date is before the swap payments start then this
        is the forward swap rate as it starts in the future. The swap rate
        is then a forward swap rate and so we use a forward discount
        factor. If the swap fixed leg has begun then we have a spot
        starting swap."""

        pv01 = self.pv01(value_dt, discount_curve)

        float_leg_value = self.float_leg.value(
            value_dt, index_curve, discount_curve
        )

        cpn = float_leg_value / pv01 / self.fixed_leg.notional
        return cpn

    ###########################################################################

    def dv01(self, value_dt, index_curve, discount_curve, tweak=1e-4):
        """Calculate the value of swap with 1 basis point up/down the swap market rate."""

        if index_curve._from_ql:
        
            ql_index_curve_up = index_curve.ql_curve.tweak_parallel(tweak)
            index_curve_up = QLCurve(value_dt, ql_index_curve_up, index_curve.dc_type, index_curve._interp_type)
            ql_index_curve_down = index_curve.ql_curve.tweak_parallel(-tweak)
            index_curve_down = QLCurve(value_dt, ql_index_curve_down, index_curve.dc_type, index_curve._interp_type)

        if discount_curve._from_ql:

            ql_discount_curve_up = discount_curve.ql_curve.tweak_parallel(tweak)
            discount_curve_up = QLCurve(value_dt, ql_discount_curve_up, discount_curve.dc_type, discount_curve._interp_type)
            ql_discount_curve_down = discount_curve.ql_curve.tweak_parallel(-tweak)
            discount_curve_down = QLCurve(value_dt, ql_discount_curve_down, discount_curve.dc_type, discount_curve._interp_type)

        npv_up = self.value(value_dt, index_curve_up, discount_curve_up)
        npv_down = self.value(value_dt, index_curve_down, discount_curve_down)
        
        dv01 = (npv_up - npv_down) / (2 * tweak) * 1e-4
        
        return dv01

    ###########################################################################

    def print_fixed_leg_pv(self):
        """Prints the fixed leg amounts without any valuation details. Shows
        the dates and sizes of the promised fixed leg flows."""

        self.fixed_leg.print_valuation()

    ###########################################################################

    def print_float_leg_pv(self):
        """Prints the fixed leg amounts without any valuation details. Shows
        the dates and sizes of the promised fixed leg flows."""

        self.float_leg.print_valuation()

    ###########################################################################

    def print_payments(self):
        """Prints the fixed leg amounts without any valuation details. Shows
        the dates and sizes of the promised fixed leg flows."""

        self.fixed_leg.print_payments()
        self.float_leg.print_payments()

    ###########################################################################

    def __repr__(self):
        s = label_to_string("OBJECT TYPE", type(self).__name__)
        s += self.fixed_leg.__repr__()
        s += "\n"
        s += self.float_leg.__repr__()
        return s

    ###########################################################################

    def _print(self):
        """Print a list of the unadjusted cpn payment dates used in
        analytic calculations for the bond."""
        print(self)


###############################################################################
