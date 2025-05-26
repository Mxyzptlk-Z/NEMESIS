##############################################################################
# Copyright (C) 2018, 2019, 2020 Dominic O'Kane
##############################################################################

from typing import Union

from ...utils.error import FinError
from ...utils.date import Date
from ...utils.global_vars import g_small
from ...utils.day_count import DayCountTypes
from ...utils.frequency import FrequencyTypes
from ...utils.calendar import CalendarTypes, DateGenRuleTypes
from ...utils.calendar import Calendar, BusDayAdjustTypes
from ...utils.helpers import label_to_string, check_argument_types
from ...utils.global_types import SwapTypes
from ...utils.fx_helper import fx_ccy_trans
from ...market.curves.discount_curve import DiscountCurve
from .ql_curve import QLCurve

from .xccy_fixed_leg import XccySwapFixedLeg

##########################################################################


class FixedFixedXCcySwap:
    """Class for managing a cross currency swap contract. This is a contract
    in which a fixed or floating payment leg in one currency is exchanged for a
    series of fixed or floating rates in a second currency. There is an
    exchange of par. The contract is entered into at zero initial cost and it
    lasts from a start date to a specified maturity date.

    The value of the contract is the NPV of the two cpn streams. Discounting
    is done on a supplied discount discount (one for each leg)  is separate
    from the curve from which the implied index rates are extracted."""

    def __init__(
        self,
        effective_dt: Date,  # Date interest starts to accrue
        term_dt_or_tenor: Union[Date, str],  # Date contract ends
        fixed_ccy_1: str,
        fixed_ccy_2: str,
        settle_ccy: str,
        fx_pair: str,
        fixed_leg_type_1: SwapTypes,
        fixed_leg_type_2: SwapTypes,
        fixed_cpn_1: float,  # Fixed cpn (annualised)
        fixed_cpn_2: float,
        fixed_freq_type_1: FrequencyTypes,
        fixed_freq_type_2: FrequencyTypes,
        fixed_dc_type_1: DayCountTypes,
        fixed_dc_type_2: DayCountTypes,
        notional_1: float,
        notional_2: float,
        payment_lag: int,
        cal_type: CalendarTypes = CalendarTypes.WEEKEND,
        bd_type: BusDayAdjustTypes = BusDayAdjustTypes.FOLLOWING,
        dg_type: DateGenRuleTypes = DateGenRuleTypes.BACKWARD,
        end_of_month: bool = False,
        is_init_notional_ex: bool = False,
        is_final_notional_ex: bool = False,
    ):
        """Create an interest rate swap contract giving the contract start
        date, its maturity, fixed cpn, fixed leg frequency, fixed leg day
        count convention and notional. The floating leg parameters have default
        values that can be overwritten if needed. The start date is contractual
        and is the same as the settlement date for a new swap. It is the date
        on which interest starts to accrue. The end of the contract is the
        termination date. This is not adjusted for business days. The adjusted
        termination date is called the maturity date. This is calculated."""

        check_argument_types(self.__init__, locals())

        if isinstance(term_dt_or_tenor, Date) is True:
            self.termination_dt = term_dt_or_tenor
        else:
            self.termination_dt = effective_dt.add_tenor(term_dt_or_tenor)

        calendar = Calendar(cal_type)
        self.maturity_dt = calendar.adjust(self.termination_dt, bd_type)

        if effective_dt > self.maturity_dt:
            raise FinError("Start date after maturity date")
        
        self.effective_dt = effective_dt
        self.settle_ccy = settle_ccy
        self.fx_pair = fx_pair

        fixed_leg_type_1 = SwapTypes.PAY
        if fixed_leg_type_2 == SwapTypes.PAY:
            fixed_leg_type_1 = SwapTypes.RECEIVE

        principal = 1.0

        self.fixed_leg_1 = XccySwapFixedLeg(
            fixed_ccy_1,
            effective_dt,
            self.termination_dt,
            fixed_leg_type_1,
            fixed_cpn_1,
            fixed_freq_type_1,
            fixed_dc_type_1,
            notional_1,
            principal,
            payment_lag,
            cal_type,
            bd_type,
            dg_type,
            end_of_month,
            is_init_notional_ex,
            is_final_notional_ex
        )

        self.fixed_leg_2 = XccySwapFixedLeg(
            fixed_ccy_2,
            effective_dt,
            self.termination_dt,
            fixed_leg_type_2,
            fixed_cpn_2,
            fixed_freq_type_2,
            fixed_dc_type_2,
            notional_2,
            principal,
            payment_lag,
            cal_type,
            bd_type,
            dg_type,
            end_of_month,
            is_init_notional_ex,
            is_final_notional_ex
        )

    ##########################################################################

    def value(
        self,
        value_dt: Date,
        discount_curve_1: DiscountCurve,
        discount_curve_2: DiscountCurve,
        fx_spot: float
    ):
        """Value the interest rate swap on a value date given a single Ibor
        discount curve."""

        fixed_leg_1_value = self.fixed_leg_1.value(value_dt, discount_curve_1)
        fixed_leg_2_value = self.fixed_leg_2.value(value_dt, discount_curve_2)

        if self.fixed_leg_1.ccy == self.settle_ccy:
            fx_spot_adj = fx_ccy_trans(1, self.fixed_leg_2.ccy, fx_spot, self.fx_pair)
            return fixed_leg_1_value + fx_spot_adj * fixed_leg_2_value
        else:
            fx_spot_adj = fx_ccy_trans(1, self.fixed_leg_1.ccy, fx_spot, self.fx_pair)
            return fixed_leg_1_value * fx_spot_adj + fixed_leg_2_value

    ##########################################################################

    def dv01_settle_ccy(
        self,
        value_dt: Date,
        discount_curve_1: DiscountCurve,
        discount_curve_2: DiscountCurve,
        tweak
    ):
        """Calculate the value of 1 basis point cpn on the fixed leg."""

        if discount_curve_1._from_ql:
            ql_discount_curve_1_up = discount_curve_1.ql_curve.tweak_parallel(tweak)
            discount_curve_1_up = QLCurve(value_dt, ql_discount_curve_1_up, discount_curve_1.dc_type, discount_curve_1._interp_type, is_index=discount_curve_1._is_index)
            ql_discount_curve_1_down = discount_curve_1.ql_curve.tweak_parallel(-tweak)
            discount_curve_1_down = QLCurve(value_dt, ql_discount_curve_1_down, discount_curve_1.dc_type, discount_curve_1._interp_type, is_index=discount_curve_1._is_index)
        
        if discount_curve_2._from_ql:
            ql_discount_curve_2_up = discount_curve_2.ql_curve.tweak_parallel(tweak)
            discount_curve_2_up = QLCurve(value_dt, ql_discount_curve_2_up, discount_curve_2.dc_type, discount_curve_2._interp_type, is_index=discount_curve_2._is_index)
            ql_discount_curve_2_down = discount_curve_2.ql_curve.tweak_parallel(-tweak)
            discount_curve_2_down = QLCurve(value_dt, ql_discount_curve_2_down, discount_curve_2.dc_type, discount_curve_2._interp_type, is_index=discount_curve_2._is_index)
        
        
        dv01_discount_1 = (self.fixed_leg_1.value(value_dt, discount_curve_1_up) - self.fixed_leg_1.value(value_dt, discount_curve_1_down)) / (2 * tweak) * 1e-4
        dv01_discount_2 = (self.fixed_leg_2.value(value_dt, discount_curve_2_up) - self.fixed_leg_2.value(value_dt, discount_curve_2_down)) / (2 * tweak) * 1e-4

        dv01s = {}
        dv01s['DV01_DISCOUNT_1'] = dv01_discount_1
        dv01s['DV01_DISCOUNT_2'] = dv01_discount_2

        return dv01s

    ##########################################################################

    def swap_rate(self, value_dt, discount_curve):
        """Calculate the fixed leg cpn that makes the swap worth zero.
        If the valuation date is before the swap payments start then this
        is the forward swap rate as it starts in the future. The swap rate
        is then a forward swap rate and so we use a forward discount
        factor. If the swap fixed leg has begun then we have a spot
        starting swap."""

        pv01 = self.pv01(value_dt, discount_curve)

        if value_dt < self.effective_dt:
            df_0 = discount_curve.df(self.effective_dt)
        else:
            df_0 = discount_curve.df(value_dt)

        df_T = discount_curve.df(self.maturity_dt)

        if abs(pv01) < g_small:
            raise FinError("PV01 is zero. Cannot compute swap rate.")

        cpn = (df_0 - df_T) / pv01
        return cpn

    ##########################################################################

    def print_fixed_leg_1_pv(self):
        """Prints the fixed leg amounts without any valuation details. Shows
        the dates and sizes of the promised fixed leg flows."""

        self.fixed_leg_1.print_valuation()

    ###########################################################################

    def print_fixed_leg_2_pv(self):
        """Prints the fixed leg amounts without any valuation details. Shows
        the dates and sizes of the promised fixed leg flows."""

        self.fixed_leg_2.print_valuation()

    ###########################################################################

    def print_payments(self):
        """Prints the fixed leg amounts without any valuation details. Shows
        the dates and sizes of the promised fixed leg flows."""

        self.fixed_leg_1.print_payments()
        self.fixed_leg_2.print_payments()

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
