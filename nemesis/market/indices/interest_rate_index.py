from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd

from ...market.curves.discount_curve import DiscountCurve
from ...utils.calendar import BusDayAdjustTypes, Calendar, CalendarTypes
from ...utils.date import Date
from ...utils.day_count import DayCount, DayCountTypes
from ...utils.error import FinError


class FixingSource(ABC):
    """Abstract source for historical index fixing data."""

    @abstractmethod
    def get_fixing(self, fixing_dt: Date, value_dt: Date) -> float | None:
        """Return fixing for fixing_dt, or None if unavailable."""


class DataFrameFixingSource(FixingSource):
    """Fixing source backed by a pandas DataFrame.

    Supported index formats:
    - YYYYMMDD strings
    - datetime-like values

    Args:
        fallback_to_last: If True, return the most recent available fixing
            on or before fixing_dt when an exact match is not found.
            Useful when the fixing DataFrame lags value_dt by one or more
            days (e.g. curve built on Friday, pricing on Monday).
    """

    def __init__(
        self,
        fixing_df: pd.DataFrame,
        fixing_col: str = "Fixing",
        fallback_to_last: bool = False,
    ):
        self.fixing_df = fixing_df
        self.fixing_col = fixing_col
        self.fallback_to_last = fallback_to_last

    def get_fixing(self, fixing_dt: Date, value_dt: Date) -> float | None:
        if fixing_dt > value_dt:
            return None

        key_str = fixing_dt.datetime().strftime("%Y%m%d")
        if key_str in self.fixing_df.index:
            return float(self.fixing_df.loc[key_str][self.fixing_col])

        key_ts = pd.Timestamp(fixing_dt.datetime())
        if key_ts in self.fixing_df.index:
            return float(self.fixing_df.loc[key_ts][self.fixing_col])

        if self.fallback_to_last:
            if pd.api.types.is_string_dtype(self.fixing_df.index):
                idx_dt = pd.to_datetime(self.fixing_df.index, format="%Y%m%d")
            else:
                idx_dt = pd.DatetimeIndex(self.fixing_df.index)
            mask = idx_dt <= key_ts
            if mask.any():
                last_pos = mask.nonzero()[0][-1]
                return float(self.fixing_df.iloc[last_pos][self.fixing_col])

        return None


@dataclass
class InterestRateIndex:
    """
    Definition of an interest rate index.

    Stores index conventions.
    """

    name: str | None = None
    currency: str | None = None
    cal_type: CalendarTypes = CalendarTypes.WEEKEND
    fixing_lag: int = 0
    spot_lag: int = 0
    tenor: str | None = None
    bd_type: BusDayAdjustTypes = BusDayAdjustTypes.MODIFIED_FOLLOWING
    dc_type: DayCountTypes = DayCountTypes.ACT_365F
    end_of_month: bool = False

    def __post_init__(self):
        if self.tenor is None:
            raise FinError("Index tenor must be provided")
        self.calendar = Calendar(self.cal_type)
        self.day_count = DayCount(self.dc_type)

    def period_rate(
        self,
        value_dt: Date,
        reset_dt: Date,
        start_dt: Date,
        end_dt: Date,
        projection_curve: DiscountCurve,
        multiplier: float,
        fixing_source: FixingSource | None = None,
    ) -> float:
        fixing_dt = self.calendar.add_business_days(reset_dt, -self.fixing_lag)

        if fixing_dt <= value_dt:
            if fixing_source is None:
                raise FinError("Require fixing data source")
            fixing = fixing_source.get_fixing(fixing_dt, value_dt)
            return fixing * multiplier

        return projection_curve.fwd_rate(start_dt, end_dt, self.dc_type) * multiplier


@dataclass
class OvernightIndex(InterestRateIndex):
    """Overnight (daily-compounded) rate index.

    Compounds daily fixings within each accrual period. Historical fixings
    are consumed from *fixing_source*; future business days use the
    projection curve's daily forward rate.
    """

    def _iter_business_days(self, from_dt: Date, to_dt: Date):
        """Yield each business day in [from_dt, to_dt)."""
        dt = from_dt
        while dt < to_dt:
            if self.calendar.is_business_day(dt):
                yield dt
            dt = dt.add_days(1)

    def _compound_fixings(
        self,
        reset_dts: list,
        next_start_dt: Date,
        value_dt: Date,
        multiplier: float,
        fixing_source: FixingSource | None,
    ) -> float:
        """Compound historical fixings; return growth factor."""
        compound = 1.0
        for i, rdt in enumerate(reset_dts):
            nxt = reset_dts[i + 1] if i + 1 < len(reset_dts) else next_start_dt
            dcf = self.day_count.year_frac(rdt, nxt)[0]
            fixing_dt = self.calendar.add_business_days(rdt, -self.fixing_lag)
            if fixing_source is not None:
                fixing = fixing_source.get_fixing(fixing_dt, value_dt)
                if fixing is not None:
                    compound *= 1.0 + fixing * multiplier * dcf
                    continue
        return compound

    def period_rate(
        self,
        value_dt: Date,
        reset_dt: Date,
        start_dt: Date,
        end_dt: Date,
        projection_curve: DiscountCurve | None,
        multiplier: float = 1.0,
        fixing_source: FixingSource | None = None,
    ) -> float:
        """Return the daily-compounded OIS rate for [start_dt, end_dt]."""
        if projection_curve is None and start_dt > value_dt:
            raise FinError("Projection curve is required for future OIS period rates.")

        # Fully future: df-ratio shortcut
        if start_dt > value_dt:
            return projection_curve.fwd_rate(start_dt, end_dt, dc_type=self.dc_type) * multiplier

        total_dcf = self.day_count.year_frac(start_dt, end_dt)[0]
        last_reset_dt = self.calendar.add_business_days(end_dt, -1)
        last_fixing_dt = self.calendar.add_business_days(last_reset_dt, -self.fixing_lag)

        # Fully fixed: compound all historical fixings
        if last_fixing_dt <= value_dt:
            reset_dts = list(self._iter_business_days(start_dt, end_dt))
            compound = self._compound_fixings(reset_dts, end_dt, value_dt, multiplier, fixing_source)
            return (compound - 1.0) / total_dcf

        # Partial: historical fixings up to value_dt + one forward for remainder
        if fixing_source is None:
            raise FinError("Require fixing data source for in-progress OIS period")

        fixed_reset_dts = list(self._iter_business_days(start_dt, value_dt.add_days(1)))
        next_reset_dt = self.calendar.adjust(value_dt.add_days(1), BusDayAdjustTypes.FOLLOWING)
        compound = self._compound_fixings(fixed_reset_dts, next_reset_dt, value_dt, multiplier, fixing_source)
        if projection_curve is None:
            raise FinError("Projection curve is required for future OIS period rates.")
        future_rate = projection_curve.fwd_rate(next_reset_dt, end_dt, dc_type=self.dc_type) * multiplier
        future_dcf = self.day_count.year_frac(next_reset_dt, end_dt)[0]
        compound *= 1.0 + future_rate * future_dcf

        return (compound - 1.0) / total_dcf
