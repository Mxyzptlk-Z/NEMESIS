from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from ...market.curves.discount_curve import DiscountCurve
from ...market.indices.interest_rate_index import FixingSource
from ...utils.calendar import DateGenRuleTypes
from ...utils.date import Date
from ...utils.day_count import DayCount
from ...utils.error import FinError
from ...utils.global_types import CompoundingTypes
from ...utils.schedule import Schedule


if TYPE_CHECKING:
    from .swap_float_leg import (
        FloatRateConvention,
        ResetCompoundedFloatRateConvention,
        SwapFloatLeg,
    )


class FloatRateRule:
    def __init__(self, convention: FloatRateConvention):
        self.convention = convention

    def bootstrap_pillar_dt(self, leg: SwapFloatLeg) -> Date:
        return leg.payment_dts[-1]

    def period_rate(
        self,
        leg: SwapFloatLeg,
        value_dt: Date,
        reset_dt: Date,
        start_dt: Date,
        end_dt: Date,
        projection_curve: DiscountCurve | None = None,
        fixing_source: FixingSource | None = None,
    ) -> float:
        return leg.rate_index.period_rate(
            value_dt,
            reset_dt,
            start_dt,
            end_dt,
            projection_curve,
            self.convention.multiplier,
            fixing_source,
        ) + self.convention.spread


class ResetCompoundedFloatRateRule(FloatRateRule):
    def __init__(self, convention: ResetCompoundedFloatRateConvention):
        super().__init__(convention)

    @property
    def reset_convention(self) -> ResetCompoundedFloatRateConvention:
        return self.convention

    def bootstrap_pillar_dt(self, leg: SwapFloatLeg) -> Date:
        if self.reset_convention.reset_dg_type != DateGenRuleTypes.FORWARD_OVERSHOOT:
            return super().bootstrap_pillar_dt(leg)

        last_start = leg.start_accrued_dts[-1]
        last_end = leg.end_accrued_dts[-1]
        sub_dts = self._build_sub_period_schedule(leg, last_start, last_end)
        return sub_dts[-1]

    def period_rate(
        self,
        leg: SwapFloatLeg,
        value_dt: Date,
        reset_dt: Date,
        start_dt: Date,
        end_dt: Date,
        projection_curve: DiscountCurve | None = None,
        fixing_source: FixingSource | None = None,
    ) -> float:
        sub_rates, sub_dcfs = self._compute_sub_period_rates(
            leg,
            value_dt,
            start_dt,
            end_dt,
            projection_curve=projection_curve,
            fixing_source=fixing_source,
        )

        if len(sub_rates) == 1:
            return sub_rates[0] + self.convention.spread

        return self._compound(sub_rates, sub_dcfs)

    def _build_sub_period_schedule(
        self,
        leg: SwapFloatLeg,
        start_dt: Date,
        end_dt: Date,
    ) -> list[Date]:
        """Build sub-period schedule dates used for reset compounding."""

        sch = Schedule(
            start_dt,
            end_dt,
            self.reset_convention.reset_freq_type,
            leg.rate_index.cal_type,
            bd_type=self.reset_convention.reset_bd_type,
            dg_type=self.reset_convention.reset_dg_type,
        )
        return sch.adjusted_dts

    def _compute_sub_period_rates(
        self,
        leg: SwapFloatLeg,
        value_dt: Date,
        start_dt: Date,
        end_dt: Date,
        projection_curve: DiscountCurve | None = None,
        fixing_source: FixingSource | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Compute index-driven rates and dcfs for each sub-period."""

        sub_dts = self._build_sub_period_schedule(leg, start_dt, end_dt)
        day_counter = DayCount(leg.dc_type)
        sub_rates = []
        sub_dcfs = []

        for j in range(len(sub_dts) - 1):
            reset_dt = sub_dts[j]
            fixing_dt = leg.rate_index.calendar.add_business_days(
                reset_dt, -leg.rate_index.fixing_lag
            )
            rate_start_dt = fixing_dt.add_days(leg.rate_index.spot_lag)
            rate_end_dt = rate_start_dt.add_tenor(leg.rate_index.tenor)
            weight_end_dt = min(sub_dts[j + 1], end_dt)
            dcf = day_counter.year_frac(reset_dt, weight_end_dt)[0]
            sub_rates.append(
                leg.rate_index.period_rate(
                    value_dt,
                    reset_dt,
                    rate_start_dt,
                    rate_end_dt,
                    projection_curve,
                    self.convention.multiplier,
                    fixing_source,
                )
            )
            sub_dcfs.append(dcf)

        return np.array(sub_rates), np.array(sub_dcfs)

    def _compound(self, sub_rates: np.ndarray, sub_dcfs: np.ndarray) -> float:
        """Apply compounding to sub-period rates and return full coupon rate."""

        compounding_type = self.reset_convention.compounding_type
        spread = self.convention.spread
        total_dcf = np.sum(sub_dcfs)

        if compounding_type == CompoundingTypes.EXCLUDE_SPREAD:
            # Compound index rates, then add spread once
            compounded = (np.prod(sub_rates * sub_dcfs + 1.0) - 1.0) / total_dcf
            return compounded + spread

        if compounding_type == CompoundingTypes.INCLUDE_SPREAD:
            # Compound (index + spread) together — spread is already embedded
            sub_rates_s = sub_rates + spread
            return (np.prod(sub_rates_s * sub_dcfs + 1.0) - 1.0) / total_dcf

        if compounding_type == CompoundingTypes.SIMPLE:
            # Weighted average of index rates, then add spread
            return np.sum(sub_rates * sub_dcfs) / total_dcf + spread

        if compounding_type == CompoundingTypes.AVERAGE:
            # Arithmetic average of index rates, then add spread
            return np.mean(sub_rates) + spread

        raise FinError(f"Unsupported compounding type: {compounding_type}")
