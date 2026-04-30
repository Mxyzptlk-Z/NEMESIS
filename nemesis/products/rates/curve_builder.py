from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ...market.curves.interpolator import InterpTypes
from ...market.indices.interest_rate_index import InterestRateIndex, OvernightIndex
from ...utils.calendar import (
    BusDayAdjustTypes,
    Calendar,
    CalendarTypes,
    DateGenRuleTypes,
)
from ...utils.date import Date
from ...utils.day_count import DayCountTypes
from ...utils.frequency import FrequencyTypes
from ...utils.global_types import CompoundingTypes, SwapTypes
from ...utils.math import ONE_MILLION
from .deposit import InterestRateDeposit
from .ir_curve import InterestRateCurve
from .ir_swap import InterestRateSwap
from .swap_float_leg import FloatRateConvention, ResetCompoundedFloatRateConvention


###############################################################################


@dataclass(kw_only=True)
class DepositConvention:
    """Static conventions shared by all deposits on a curve."""

    dc_type: DayCountTypes
    cal_type: CalendarTypes
    bd_type: BusDayAdjustTypes = BusDayAdjustTypes.MODIFIED_FOLLOWING
    notional: float = ONE_MILLION


###############################################################################


@dataclass(kw_only=True)
class SwapConvention:
    """Static conventions for a group of swaps that share the same parameters.

    ``row_range`` is a :class:`slice` that selects which rows of the market-data
    DataFrame belong to this group.  Use ``slice(None)`` (the default) for all
    rows, or e.g. ``slice(0, 15)`` / ``slice(15, None)`` to split the sheet
    when two groups differ only in ``payment_lag`` or ``fixed_freq_type``.
    """

    rate_index: InterestRateIndex
    fixed_leg_type: SwapTypes
    fixed_freq_type: FrequencyTypes
    fixed_dc_type: DayCountTypes
    float_freq_type: FrequencyTypes
    float_dc_type: DayCountTypes
    cal_type: CalendarTypes
    bd_type: BusDayAdjustTypes
    dg_type: DateGenRuleTypes
    payment_lag: int = 0
    float_convention: FloatRateConvention | None = None
    notional: float = ONE_MILLION
    end_of_month: bool = False
    row_range: slice = field(default_factory=lambda: slice(None))


###############################################################################


@dataclass(kw_only=True)
class CurveBuildConfig:
    """Full configuration for building an :class:`InterestRateCurve`.

    Call :meth:`build` with a valuation date and an Excel file path to read
    market data and bootstrap the curve in one step.

    Parameters
    ----------
    settle_lag:
        Number of business days from ``value_dt`` to the swap settlement date.
    cal_type:
        Calendar used to compute the settlement date.
    swap_conventions:
        Ordered list of :class:`SwapConvention` groups.  Each group selects a
        slice of the swap market-data sheet and constructs instruments with its
        own parameters.
    deposit_convention:
        Convention for deposit instruments.  Set to ``None`` if the curve has
        no deposit pillar.
    interp_type:
        Interpolation method passed to :class:`InterestRateCurve`.
    dc_type:
        Day-count convention passed to :class:`InterestRateCurve`.
    is_index:
        Whether the curve is an index curve (requires ``currency``).
    currency:
        ISO currency code.
    """

    settle_lag: int
    cal_type: CalendarTypes
    swap_conventions: list[SwapConvention]
    deposit_convention: DepositConvention | None = None
    interp_type: InterpTypes = InterpTypes.LINEAR_ZERO_RATES
    dc_type: DayCountTypes = DayCountTypes.ACT_365F
    currency: str | None = None

    # ------------------------------------------------------------------

    def build(
        self,
        value_dt: Date,
        data_path: str | None = None,
        *,
        deposit_df: pd.DataFrame | None = None,
        swap_df: pd.DataFrame | None = None,
    ) -> InterestRateCurve:
        """Bootstrap an :class:`InterestRateCurve` from market data.

        Either supply ``data_path`` pointing to an Excel workbook with a
        ``"swap"`` sheet (and optionally a ``"deposit"`` sheet), or pass
        DataFrames directly via ``deposit_df`` / ``swap_df``.

        Both DataFrames must have ``"Tenor"`` and ``"Rate"`` columns.
        """
        if data_path is not None:
            swap_df = pd.read_excel(data_path, sheet_name="swap")
            if self.deposit_convention is not None:
                deposit_df = pd.read_excel(data_path, sheet_name="deposit")

        if swap_df is None:
            raise ValueError("swap_df must be provided if data_path is None")

        cal = Calendar(self.cal_type)
        settle_dt = cal.add_business_days(value_dt, self.settle_lag)

        # ----- deposits -------------------------------------------------------
        deposits: list[InterestRateDeposit] = []
        if self.deposit_convention is not None and deposit_df is not None:
            dc = self.deposit_convention
            deposits = [
                InterestRateDeposit(
                    effective_dt=settle_dt,
                    maturity_dt_or_tenor=row["Tenor"],
                    deposit_rate=row["Rate"],
                    dc_type=dc.dc_type,
                    notional=dc.notional,
                    cal_type=dc.cal_type,
                    bd_type=dc.bd_type,
                )
                for _, row in deposit_df.iterrows()
            ]

        # ----- swaps ----------------------------------------------------------
        swaps: list[InterestRateSwap] = []
        for conv in self.swap_conventions:
            group_df = swap_df.iloc[conv.row_range]
            for _, row in group_df.iterrows():
                swaps.append(
                    InterestRateSwap(
                        effective_dt=settle_dt,
                        term_dt_or_tenor=row["Tenor"],
                        fixed_leg_type=conv.fixed_leg_type,
                        fixed_cpn=row["Rate"],
                        fixed_freq_type=conv.fixed_freq_type,
                        fixed_dc_type=conv.fixed_dc_type,
                        float_freq_type=conv.float_freq_type,
                        float_dc_type=conv.float_dc_type,
                        rate_index=conv.rate_index,
                        float_convention=conv.float_convention,
                        notional=conv.notional,
                        payment_lag=conv.payment_lag,
                        cal_type=conv.cal_type,
                        bd_type=conv.bd_type,
                        dg_type=conv.dg_type,
                        end_of_month=conv.end_of_month,
                    )
                )

        return InterestRateCurve(
            value_dt,
            deposits,
            [],
            swaps,
            interp_type=self.interp_type,
            dc_type=self.dc_type,
            currency=self.currency,
        )


class FR007Config(CurveBuildConfig):
    """CurveBuildConfig for the CNY FR007 swap curve.

    Conventions
    -----------
    - Calendar: CHINA_IB
    - Float rate: weekly reset sub-period compounding (Bloomberg convention)
    - Fixed/float schedule: quarterly ACT/365F
    - Deposit: 1W ACT/365F FOLLOWING
    - Settlement: T+1 business day
    """

    def __init__(self, notional: float = ONE_MILLION):
        index = InterestRateIndex(
            cal_type=CalendarTypes.CHINA_IB,
            fixing_lag=1,
            spot_lag=1,
            tenor="1W",
        )
        float_convention = ResetCompoundedFloatRateConvention(
            multiplier=1.0,
            spread=0.0,
            compounding_type=CompoundingTypes.EXCLUDE_SPREAD,
            reset_freq_type=FrequencyTypes.WEEKLY,
            reset_bd_type=BusDayAdjustTypes.NONE,
            reset_dg_type=DateGenRuleTypes.FORWARD_OVERSHOOT,
        )
        swap_conv = SwapConvention(
            rate_index=index,
            fixed_leg_type=SwapTypes.PAY,
            fixed_freq_type=FrequencyTypes.QUARTERLY,
            fixed_dc_type=DayCountTypes.ACT_365F,
            float_freq_type=FrequencyTypes.QUARTERLY,
            float_dc_type=DayCountTypes.ACT_365F,
            cal_type=CalendarTypes.CHINA_IB,
            bd_type=BusDayAdjustTypes.MODIFIED_FOLLOWING,
            dg_type=DateGenRuleTypes.FORWARD,
            float_convention=float_convention,
            notional=notional,
        )
        deposit_conv = DepositConvention(
            dc_type=DayCountTypes.ACT_365F,
            cal_type=CalendarTypes.CHINA_IB,
            bd_type=BusDayAdjustTypes.FOLLOWING,
            notional=notional,
        )
        super().__init__(
            settle_lag=1,
            cal_type=CalendarTypes.CHINA_IB,
            deposit_convention=deposit_conv,
            swap_conventions=[swap_conv],
            interp_type=InterpTypes.LINEAR_ZERO_RATES,
            dc_type=DayCountTypes.ACT_365F,
            currency="CNY",
        )


class SOFRConfig(CurveBuildConfig):
    """CurveBuildConfig for the USD SOFR OIS curve.

    Conventions
    -----------
    - Calendar: UNITED_STATES
    - Float rate: plain overnight (OvernightIndex, 1D, ACT/360)
    - Fixed/float schedule: annual ACT/360 FOLLOWING BACKWARD
    - Payment lag: 0 for the first 15 tenors, 2 for the remainder
    - No deposit pillar
    - Settlement: T+2 business days
    """

    def __init__(self, notional: float = ONE_MILLION):
        index = OvernightIndex(
            cal_type=CalendarTypes.UNITED_STATES,
            fixing_lag=0,
            spot_lag=2,
            tenor="1D",
            dc_type=DayCountTypes.ACT_360,
        )
        float_convention = FloatRateConvention(multiplier=1.0, spread=0.0)
        _shared = dict(
            rate_index=index,
            fixed_leg_type=SwapTypes.PAY,
            fixed_freq_type=FrequencyTypes.ANNUAL,
            fixed_dc_type=DayCountTypes.ACT_360,
            float_freq_type=FrequencyTypes.ANNUAL,
            float_dc_type=DayCountTypes.ACT_360,
            cal_type=CalendarTypes.UNITED_STATES,
            bd_type=BusDayAdjustTypes.FOLLOWING,
            dg_type=DateGenRuleTypes.BACKWARD,
            float_convention=float_convention,
            notional=notional,
        )
        super().__init__(
            settle_lag=2,
            cal_type=CalendarTypes.UNITED_STATES,
            swap_conventions=[
                SwapConvention(**_shared, payment_lag=0, row_range=slice(0, 15)),
                SwapConvention(**_shared, payment_lag=2, row_range=slice(15, None)),
            ],
            interp_type=InterpTypes.LINEAR_ZERO_RATES,
            dc_type=DayCountTypes.ACT_360,
            currency="USD",
        )


class BBSW3MConfig(CurveBuildConfig):
    """CurveBuildConfig for the AUD BBSW 3M swap curve.

    Conventions
    -----------
    - Calendar: AUSTRALIA
    - Float rate: plain IBOR 3M (InterestRateIndex, fixing_lag=1, spot_lag=1)
    - Fixed schedule: quarterly ACT/365F for first 6 tenors, then semi-annual
    - Float schedule: quarterly ACT/365F throughout
    - Deposit: 1 deposit ACT/365F MODIFIED_FOLLOWING
    - Settlement: T+1 business day
    - End-of-month: True
    """

    def __init__(self, notional: float = ONE_MILLION):
        index = InterestRateIndex(
            cal_type=CalendarTypes.AUSTRALIA,
            fixing_lag=1,
            spot_lag=1,
            tenor="3M",
        )
        float_convention = FloatRateConvention(multiplier=1.0, spread=0.0)
        _shared = dict(
            rate_index=index,
            fixed_leg_type=SwapTypes.PAY,
            fixed_dc_type=DayCountTypes.ACT_365F,
            float_freq_type=FrequencyTypes.QUARTERLY,
            float_dc_type=DayCountTypes.ACT_365F,
            cal_type=CalendarTypes.AUSTRALIA,
            bd_type=BusDayAdjustTypes.MODIFIED_FOLLOWING,
            dg_type=DateGenRuleTypes.BACKWARD,
            float_convention=float_convention,
            notional=notional,
            end_of_month=True,
        )
        deposit_conv = DepositConvention(
            dc_type=DayCountTypes.ACT_365F,
            cal_type=CalendarTypes.AUSTRALIA,
            bd_type=BusDayAdjustTypes.MODIFIED_FOLLOWING,
            notional=notional,
        )
        super().__init__(
            settle_lag=1,
            cal_type=CalendarTypes.AUSTRALIA,
            deposit_convention=deposit_conv,
            swap_conventions=[
                SwapConvention(
                    **_shared,
                    fixed_freq_type=FrequencyTypes.QUARTERLY,
                    row_range=slice(0, 6),
                ),
                SwapConvention(
                    **_shared,
                    fixed_freq_type=FrequencyTypes.SEMI_ANNUAL,
                    row_range=slice(6, None),
                ),
            ],
            interp_type=InterpTypes.LINEAR_ZERO_RATES,
            dc_type=DayCountTypes.ACT_365F,
            currency="AUD",
        )
