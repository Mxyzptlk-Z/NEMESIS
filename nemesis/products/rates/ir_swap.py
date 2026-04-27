import numpy as np

from ...market.curves.discount_curve import DiscountCurve
from ...market.indices.interest_rate_index import (
    FixingSource,
    InterestRateIndex,
)
from ...utils.calendar import (
    BusDayAdjustTypes,
    Calendar,
    CalendarTypes,
    DateGenRuleTypes,
)
from ...utils.date import Date
from ...utils.day_count import DayCountTypes
from ...utils.error import FinError
from ...utils.frequency import FrequencyTypes
from ...utils.global_types import SwapTypes
from ...utils.helpers import label_to_string
from ...utils.math import ONE_MILLION
from .swap_fixed_leg import SwapFixedLeg
from .swap_float_leg import FloatRateSpec, SwapFloatLeg


###############################################################################


class InterestRateSwap:
    """Class for managing fixed-vs-floating interest rate swaps.

    Covers all vanilla IRS types (OIS, IBOR, Term Rate) — the floating rate
    behaviour is fully controlled by the FloatLegSpec passed to the float leg.

    The contract lasts from an effective date to a termination date. The fixed
    coupon is set at inception. The floating rate is determined from an index
    curve (and optionally a separate discount curve for dual-curve pricing).

    value() accepts a single discount curve for single-curve pricing,
    or an explicit discount curve for dual-curve pricing while projection is
    provided explicitly at valuation time."""

    def __init__(
        self,
        effective_dt: Date,
        term_dt_or_tenor: Date | str,
        fixed_leg_type: SwapTypes,
        fixed_cpn: float,
        fixed_freq_type: FrequencyTypes,
        fixed_dc_type: DayCountTypes,
        float_freq_type: FrequencyTypes = FrequencyTypes.ANNUAL,
        float_dc_type: DayCountTypes = DayCountTypes.THIRTY_E_360,
        rate_index: InterestRateIndex | None = None,
        rate_spec: FloatRateSpec | None = None,
        notional: float = ONE_MILLION,
        payment_lag: int = 0,
        cal_type: CalendarTypes = CalendarTypes.WEEKEND,
        bd_type: BusDayAdjustTypes = BusDayAdjustTypes.FOLLOWING,
        dg_type: DateGenRuleTypes = DateGenRuleTypes.BACKWARD,
        end_of_month: bool = False,
    ):
        """Create a fixed-vs-floating interest rate swap."""

        if rate_index is None:
            raise FinError("rate_index is required")

        if rate_spec is None:
            rate_spec = FloatRateSpec()

        if isinstance(term_dt_or_tenor, Date):
            self.termination_dt = term_dt_or_tenor
        else:
            self.termination_dt = effective_dt.add_tenor(term_dt_or_tenor)

        calendar = Calendar(cal_type)
        self.maturity_dt = calendar.adjust(self.termination_dt, bd_type)

        if effective_dt > self.maturity_dt:
            raise FinError("Effective date after maturity date")

        self.effective_dt = effective_dt
        self.notional = notional
        self.rate_index = rate_index

        if fixed_leg_type == SwapTypes.PAY:
            float_leg_type = SwapTypes.RECEIVE
        else:
            float_leg_type = SwapTypes.PAY

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
            end_of_month,
        )

        self.float_leg = SwapFloatLeg(
            effective_dt,
            self.termination_dt,
            float_leg_type,
            float_freq_type,
            float_dc_type,
            rate_index,
            rate_spec,
            notional,
            principal,
            payment_lag,
            cal_type,
            bd_type,
            dg_type,
            end_of_month,
        )

    ###########################################################################

    def value(
        self,
        value_dt: Date,
        discount_curve: DiscountCurve = None,
        projection_curve: DiscountCurve | None = None,
        fixing_source: FixingSource | None = None,
        pv_only: bool = True,
    ):
        """Value the interest rate swap.

        Args:
            discount_curve: Curve for discounting cash flows.
            projection_curve: Curve for projecting forward rates. Falls back
                to discount_curve for single-curve pricing.
            fixing_source: Source for historical fixings.
        """

        if discount_curve is None and projection_curve is None:
            raise FinError("At least one of discount_curve or projection_curve is required")
        if discount_curve is None:
            discount_curve = projection_curve
        if projection_curve is None:
            projection_curve = discount_curve

        fixed_leg_value = self.fixed_leg.value(
            value_dt, discount_curve, pv_only=pv_only
        )

        float_leg_value = self.float_leg.value(
            value_dt,
            discount_curve,
            projection_curve=projection_curve,
            fixing_source=fixing_source,
            pv_only=pv_only,
        )

        if pv_only:
            return fixed_leg_value + float_leg_value
        else:
            import pandas as pd
            value = fixed_leg_value[0] + float_leg_value[0]
            cashflow_report = pd.concat(
                [fixed_leg_value[1], float_leg_value[1]], ignore_index=True
            )
            return value, cashflow_report

    ###########################################################################

    def pv01(self, value_dt, discount_curve):
        """Calculate the value of 1 basis point cpn on the fixed leg."""

        pv = self.fixed_leg.value(value_dt, discount_curve)
        pv01 = pv / self.fixed_leg.cpn / self.fixed_leg.notional

        # Needs to be positive even if it is a payer leg and/or cpn < 0
        pv01 = np.abs(pv01)
        return pv01

    ###########################################################################

    def swap_rate(
        self,
        value_dt,
        discount_curve: DiscountCurve = None,
        projection_curve: DiscountCurve | None = None,
        fixing_source: FixingSource | None = None,
    ):
        """Calculate the fixed leg cpn that makes the swap worth zero.

        If discount_curve is None, projection curve is used for discounting
        (single-curve pricing)."""

        if discount_curve is None and projection_curve is None:
            raise FinError("At least one of discount_curve or projection_curve is required")
        if discount_curve is None:
            discount_curve = projection_curve
        if projection_curve is None:
            projection_curve = discount_curve

        pv01 = self.pv01(value_dt, discount_curve)

        float_leg_value = self.float_leg.value(
            value_dt,
            discount_curve,
            projection_curve=projection_curve,
            fixing_source=fixing_source,
        )

        cpn = float_leg_value / pv01 / self.fixed_leg.notional
        return cpn

    ###########################################################################

    def get_fixed_rate(self):
        """Read access to the coupon (fixed rate)."""
        return self.fixed_leg.cpn

    ###########################################################################

    def set_fixed_rate(self, new_rate: float):
        """Update the fixed rate and regenerate payments."""
        self.fixed_leg.cpn = new_rate
        self.fixed_leg.generate_payments()

    ###########################################################################

    def dv01(
        self,
        value_dt,
        discount_curve: DiscountCurve = None,
        projection_curve: DiscountCurve | None = None,
        fixing_source: FixingSource | None = None,
        tweak=1e-4,
    ):
        """Calculate DV01 via parallel bump-and-reprice.

        Requires QL-backed curves for both projection and discount."""

        from .ql_curve import QLCurve

        if projection_curve is None:
            projection_curve = discount_curve
        if discount_curve is None:
            discount_curve = projection_curve

        if projection_curve is None:
            raise FinError("projection_curve is required for dv01")

        if not getattr(projection_curve, "_from_ql", False):
            raise FinError("Projection curve must be QL-backed for dv01")
        if not getattr(discount_curve, "_from_ql", False):
            raise FinError("Discount curve must be QL-backed for dv01")

        ql_proj_curve_up = projection_curve.ql_curve.tweak_parallel(tweak)
        proj_curve_up = QLCurve(
            value_dt,
            ql_proj_curve_up,
            projection_curve.dc_type,
            projection_curve._interp_type,
        )
        ql_proj_curve_down = projection_curve.ql_curve.tweak_parallel(-tweak)
        proj_curve_down = QLCurve(
            value_dt,
            ql_proj_curve_down,
            projection_curve.dc_type,
            projection_curve._interp_type,
        )

        ql_discount_curve_up = discount_curve.ql_curve.tweak_parallel(tweak)
        discount_curve_up = QLCurve(
            value_dt,
            ql_discount_curve_up,
            discount_curve.dc_type,
            discount_curve._interp_type,
        )
        ql_discount_curve_down = discount_curve.ql_curve.tweak_parallel(-tweak)
        discount_curve_down = QLCurve(
            value_dt,
            ql_discount_curve_down,
            discount_curve.dc_type,
            discount_curve._interp_type,
        )

        npv_up = self.value(
            value_dt,
            discount_curve_up,
            projection_curve=proj_curve_up,
            fixing_source=fixing_source,
        )

        npv_down = self.value(
            value_dt,
            discount_curve_down,
            projection_curve=proj_curve_down,
            fixing_source=fixing_source,
        )

        dv01 = (npv_up - npv_down) / (2 * tweak) * 1e-4

        return dv01

    ###########################################################################

    def print_fixed_leg_pv(self):
        self.fixed_leg.print_valuation()

    ###########################################################################

    def print_float_leg_pv(self, cashflow_df=None):
        self.float_leg.print_valuation(cashflow_df)

    ###########################################################################

    def print_payments(self):
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
        print(self)


###############################################################################
