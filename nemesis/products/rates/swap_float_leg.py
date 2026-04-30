from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

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
from ...utils.day_count import DayCount, DayCountTypes
from ...utils.error import FinError
from ...utils.frequency import FrequencyTypes
from ...utils.global_types import CompoundingTypes, SwapTypes
from ...utils.helpers import (
    format_table,
    label_to_string,
)
from ...utils.math import ONE_MILLION
from ...utils.schedule import Schedule
from .float_rate_rule import FloatRateRule, ResetCompoundedFloatRateRule


###############################################################################


@dataclass(kw_only=True)
class FloatRateConvention:
    """Plain floating-rate convention without reset compounding."""

    multiplier: float = 1.0
    spread: float = 0.0

    @property
    def spread_bps(self) -> float:
        """Spread expressed in basis points."""
        return self.spread * 10000.0

    @spread_bps.setter
    def spread_bps(self, bps: float):
        self.spread = bps / 10000.0


@dataclass(kw_only=True)
class ResetCompoundedFloatRateConvention(FloatRateConvention):
    """Floating-rate convention driven by reset sub-period compounding."""

    compounding_type: CompoundingTypes
    reset_freq_type: FrequencyTypes
    reset_bd_type: BusDayAdjustTypes
    reset_dg_type: DateGenRuleTypes


def _create_float_rate_rule(convention: FloatRateConvention) -> FloatRateRule:
    if isinstance(convention, ResetCompoundedFloatRateConvention):
        return ResetCompoundedFloatRateRule(convention)
    return FloatRateRule(convention)


###############################################################################


class SwapFloatLeg:
    """Class for managing the floating leg of a swap. A float leg consists of
    a sequence of flows calculated according to an ISDA schedule and with a
    coupon determined by an index curve which changes over life of the swap."""

    def __init__(
        self,
        effective_dt: Date,
        end_dt: Date | str,
        leg_type: SwapTypes,
        freq_type: FrequencyTypes,
        dc_type: DayCountTypes,
        rate_index: InterestRateIndex,
        float_convention: FloatRateConvention | None = None,
        notional: float = ONE_MILLION,
        principal: float = 0.0,
        payment_lag: int = 0,
        cal_type: CalendarTypes = CalendarTypes.WEEKEND,
        bd_type: BusDayAdjustTypes = BusDayAdjustTypes.FOLLOWING,
        dg_type: DateGenRuleTypes = DateGenRuleTypes.BACKWARD,
        end_of_month: bool = False,
    ):
        """Create the floating leg of a swap contract."""

        # check_argument_types(self.__init__, locals())

        if rate_index is None:
            raise FinError("rate_index is required")

        if float_convention is None:
            float_convention = FloatRateConvention()

        if type(end_dt) is Date:
            self.termination_dt = end_dt
        else:
            self.termination_dt = effective_dt.add_tenor(end_dt)

        calendar = Calendar(cal_type)
        self.maturity_dt = calendar.adjust(self.termination_dt, bd_type)

        if effective_dt > self.maturity_dt:
            raise FinError("Start date after maturity date")

        self.effective_dt = effective_dt
        self.end_dt = end_dt
        self.leg_type = leg_type
        self.freq_type = freq_type
        self.payment_lag = payment_lag
        self.principal = principal
        self.notional = notional

        self.float_convention = float_convention
        self.rate_rule: FloatRateRule = _create_float_rate_rule(float_convention)
        self.rate_index = rate_index

        self.dc_type = dc_type
        self.cal_type = cal_type
        self.bd_type = bd_type
        self.dg_type = dg_type
        self.end_of_month = end_of_month

        self.start_accrued_dts: list[Date] = []
        self.end_accrued_dts: list[Date] = []
        self.reset_dts: list[Date] = []
        self.payment_dts: list[Date] = []
        self.year_fracs: list[float] = []
        self.accrued_days: list[int] = []

        self.generate_payment_dts()

    ###########################################################################

    def generate_payment_dts(self):
        """Generate the floating leg payment dates and accrual factors. The
        coupons cannot be generated yet as we do not have the index curve."""

        schedule = Schedule(
            self.effective_dt,
            self.termination_dt,
            self.freq_type,
            self.cal_type,
            self.bd_type,
            self.dg_type,
            end_of_month=self.end_of_month,
        )

        schedule_dts = schedule.adjusted_dts

        if len(schedule_dts) < 2:
            raise FinError("Schedule has none or only one date")

        self.start_accrued_dts = []
        self.end_accrued_dts = []
        self.reset_dts = []
        self.payment_dts = []
        self.year_fracs = []
        self.accrued_days = []

        prev_dt = schedule_dts[0]

        day_counter = DayCount(self.dc_type)
        calendar = Calendar(self.cal_type)

        for next_dt in schedule_dts[1:]:
            self.start_accrued_dts.append(prev_dt)
            self.end_accrued_dts.append(next_dt)

            reset_dt = prev_dt
            self.reset_dts.append(reset_dt)

            if self.payment_lag == 0:
                payment_dt = next_dt
            else:
                payment_dt = calendar.add_business_days(next_dt, self.payment_lag)

            self.payment_dts.append(payment_dt)

            (year_frac, num, _) = day_counter.year_frac(prev_dt, next_dt)

            self.year_fracs.append(year_frac)
            self.accrued_days.append(num)

            prev_dt = next_dt

    ###########################################################################

    @property
    def bootstrap_pillar_dt(self) -> Date:
        return self.rate_rule.bootstrap_pillar_dt(self)

    ###########################################################################

    def _compute_period_rate(
        self,
        value_dt: Date,
        reset_dt: Date,
        start_dt: Date,
        end_dt: Date,
        projection_curve: DiscountCurve | None = None,
        fixing_source: FixingSource | None = None,
    ) -> float:
        """Compute the full coupon rate for one accrual period."""

        if self.rate_index is None:
            raise FinError("rate_index is required for float leg valuation")

        return self.rate_rule.period_rate(
            self,
            value_dt,
            reset_dt,
            start_dt,
            end_dt,
            projection_curve=projection_curve,
            fixing_source=fixing_source,
        )

    ###########################################################################

    def value(
        self,
        value_dt: Date,
        discount_curve: DiscountCurve,
        projection_curve: DiscountCurve | None = None,
        fixing_source=None,
        pv_only=True,
    ) -> float | tuple[float, pd.DataFrame]:
        """Value the floating leg."""

        if discount_curve is None:
            raise FinError("Discount curve is None")

        df_value = discount_curve.df(value_dt)
        leg_pv = 0.0
        num_payments = len(self.payment_dts)

        rates: list[float] = []
        payments: list[float] = []
        payment_dfs: list[float] = []
        payment_pvs: list[float] = []
        cumulative_pvs: list[float] = []

        for i_pmnt in range(num_payments):
            payment_dt = self.payment_dts[i_pmnt]

            if payment_dt > value_dt:
                start_accrued_dt = self.start_accrued_dts[i_pmnt]
                end_accrued_dt = self.end_accrued_dts[i_pmnt]
                reset_dt = self.reset_dts[i_pmnt]
                pay_alpha = self.year_fracs[i_pmnt]

                # Returns full coupon rate (index + spread)
                coupon_rate = self._compute_period_rate(
                    value_dt,
                    reset_dt,
                    start_accrued_dt,
                    end_accrued_dt,
                    projection_curve=projection_curve,
                    fixing_source=fixing_source,
                )

                payment_amount = (
                    coupon_rate * pay_alpha * self.notional
                )

                df_payment = (
                    discount_curve.df(payment_dt) / df_value
                )
                payment_pv = payment_amount * df_payment
                leg_pv += payment_pv

                rates.append(coupon_rate)
                payments.append(payment_amount)
                payment_dfs.append(df_payment)
                payment_pvs.append(payment_pv)
                cumulative_pvs.append(leg_pv)

            else:
                rates.append(0.0)
                payments.append(0.0)
                payment_dfs.append(0.0)
                payment_pvs.append(0.0)
                cumulative_pvs.append(leg_pv)

        if payment_dt > value_dt:
            principal_pv = self.principal * df_payment * self.notional
            payment_pvs[-1] += principal_pv
            leg_pv += principal_pv
            cumulative_pvs[-1] = leg_pv

        if self.leg_type == SwapTypes.PAY:
            leg_pv = leg_pv * (-1.0)

        if pv_only:
            return leg_pv

        # Build cashflow report
        leg_type_sign = -1 if self.leg_type == SwapTypes.PAY else 1
        df = pd.DataFrame()
        df["payment_date"] = self.payment_dts
        df["start_accrual_date"] = self.start_accrued_dts
        df["end_accrual_date"] = self.end_accrued_dts
        df["reset_date"] = self.reset_dts
        df["year_frac"] = self.year_fracs
        df["rate"] = rates
        df["payment"] = np.array(payments) * leg_type_sign
        df["payment_df"] = payment_dfs
        df["payment_pv"] = np.array(payment_pvs) * leg_type_sign
        df["leg"] = "FLOAT"

        return leg_pv, df

    ###########################################################################

    def accrued_amount(
        self,
        value_dt: Date,
        projection_curve: DiscountCurve | None = None,
        fixing_source=None,
    ) -> float:
        """Compute accrued interest for the period containing value_dt.

        Returns the accrued amount (positive for RECEIVE, negative for PAY).
        If value_dt is not within any accrual period, returns 0.
        """

        day_counter = DayCount(self.dc_type)

        for i in range(len(self.payment_dts)):
            start_dt = self.start_accrued_dts[i]
            end_dt = self.end_accrued_dts[i]

            if start_dt <= value_dt < end_dt:
                reset_dt = self.reset_dts[i]
                coupon_rate = self._compute_period_rate(
                    value_dt,
                    reset_dt,
                    start_dt,
                    end_dt,
                    projection_curve=projection_curve,
                    fixing_source=fixing_source,
                )
                accrued_dcf = day_counter.year_frac(start_dt, value_dt)[0]
                accrued = coupon_rate * accrued_dcf * self.notional

                if self.leg_type == SwapTypes.PAY:
                    return -accrued
                return accrued

        return 0.0

    ###########################################################################

    def print_payments(self):
        """Print the floating leg payment schedule."""

        print("START DATE:", self.effective_dt)
        print("MATURITY DATE:", self.maturity_dt)
        print("SPREAD (bp):", self.float_convention.spread * 10000)
        print("FREQUENCY:", str(self.freq_type))
        print("DAY COUNT:", str(self.dc_type))

        if len(self.payment_dts) == 0:
            print("Payments Dates not calculated.")
            return

        header = [
            "PAY_NUM",
            "PAY_dt",
            "ACCR_START",
            "ACCR_END",
            "DAYS",
            "YEARFRAC",
        ]

        rows = []
        num_flows = len(self.payment_dts)
        for i_flow in range(0, num_flows):
            rows.append(
                [
                    i_flow + 1,
                    self.payment_dts[i_flow],
                    self.start_accrued_dts[i_flow],
                    self.end_accrued_dts[i_flow],
                    self.accrued_days[i_flow],
                    round(self.year_fracs[i_flow], 4),
                ]
            )

        table = format_table(header, rows)
        print("\nPAYMENTS SCHEDULE:")
        print(table)

    ###########################################################################

    def print_valuation(self, cashflow_df: pd.DataFrame | None = None):
        """Print valuation details."""

        print("START DATE:", self.effective_dt)
        print("MATURITY DATE:", self.maturity_dt)
        print("SPREAD (BPS):", self.float_convention.spread * 10000)
        print("FREQUENCY:", str(self.freq_type))
        print("DAY COUNT:", str(self.dc_type))

        if cashflow_df is None or len(cashflow_df) == 0:
            print("Valuation data not provided. Call value(pv_only=False) first.")
            return

        header = [
            "PAY_NUM",
            "PAY_dt",
            "NOTIONAL",
            "RATE",
            "PMNT",
            "DF",
            "PV",
        ]

        rows = []
        for i_flow in range(len(cashflow_df)):
            row = cashflow_df.iloc[i_flow]
            rows.append(
                [
                    i_flow + 1,
                    row["payment_date"],
                    round(self.notional, 0),
                    round(row["rate"] * 100.0, 4),
                    round(row["payment"], 2),
                    round(row["payment_df"], 4),
                    round(row["payment_pv"], 2),
                ]
            )

        table = format_table(header, rows)
        print("\nPAYMENTS VALUATION:")
        print(table)

    ###########################################################################

    def __repr__(self):
        s = label_to_string("OBJECT TYPE", type(self).__name__)
        s += label_to_string("START DATE", self.effective_dt)
        s += label_to_string("TERMINATION DATE", self.termination_dt)
        s += label_to_string("MATURITY DATE", self.maturity_dt)
        s += label_to_string("NOTIONAL", self.notional)
        s += label_to_string("SWAP TYPE", self.leg_type)
        s += label_to_string("SPREAD (BPS)", self.float_convention.spread * 10000)
        s += label_to_string("FREQUENCY", self.freq_type)
        s += label_to_string("DAY COUNT", self.dc_type)
        s += label_to_string("CALENDAR", self.cal_type)
        s += label_to_string("BUS DAY ADJUST", self.bd_type)
        s += label_to_string("DATE GEN TYPE", self.dg_type)
        return s


###############################################################################
