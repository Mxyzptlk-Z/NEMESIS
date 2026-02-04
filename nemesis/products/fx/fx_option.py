from abc import ABC, abstractmethod

from ...utils.calendar import Calendar, CalendarTypes
from ...utils.date import Date
from ...utils.day_count import DayCountTypes
from ...utils.error import FinError
from ...utils.fx_helper import get_fx_pair_base_size

from ...market.curves import DiscountCurve, ForwardCurve
from ...market.volatility import VolSurface

##########################################################################

bump = 1e-4

##########################################################################


class FXOption(ABC):
    """Class that is used to perform perturbation risk for FX options."""

    def __init__(
        self,
        currency_pair: str,
        cal_type: CalendarTypes
    ):
        if len(currency_pair) != 6:
            raise FinError("Currency pair must be 6 characters.")

        self.currency_pair = currency_pair
        self.for_name = self.currency_pair[0:3]
        self.dom_name = self.currency_pair[3:6]
        self.cal_type = cal_type
        self.calendar = Calendar(cal_type)

        self.base_size = get_fx_pair_base_size(self.currency_pair)

    ###########################################################################

    @abstractmethod
    def value(
        self,
        value_dt: Date,
        forward_curve: ForwardCurve,
        domestic_curve: DiscountCurve,
        vol_surface: VolSurface,
        dc_type: DayCountTypes
    ):
        raise NotImplementedError("Should implememnt `value` method")

    ###########################################################################

    def delta(
        self, value_dt, forward_curve, domestic_curve, vol_surface, dc_type, bump=1
    ):
        """Calculate the option delta (FX rate sensitivity) by adding on a
        small bump and calculating the change in the option price."""

        forward_curve_up = forward_curve.bump_spot(bump / self.base_size)
        forward_curve_down = forward_curve.bump_spot(-bump / self.base_size)

        v_up = self.value(
            value_dt, forward_curve_up, domestic_curve, vol_surface, dc_type
        )

        v_down = self.value(
            value_dt, forward_curve_down, domestic_curve, vol_surface, dc_type
        )

        if isinstance(v_up, dict):
            delta = (v_up["value"] - v_down["value"]) / (2 * bump / self.base_size)
        else:
            delta = (v_up - v_down) / (2 * bump / self.base_size)

        return delta

    ###########################################################################

    def gamma(
        self, value_dt, forward_curve, domestic_curve, vol_surface, dc_type, bump=1
    ):
        """Calculate the option gamma (delta sensitivity) by adding on a
        small bump and calculating the change in the option delta."""

        forward_curve_up = forward_curve.bump_spot(bump / self.base_size)
        forward_curve_down = forward_curve.bump_spot(-bump / self.base_size)

        v = self.value(
            value_dt, forward_curve, domestic_curve, vol_surface, dc_type
        )

        v_down = self.value(
            value_dt, forward_curve_down, domestic_curve, vol_surface, dc_type
        )

        v_up = self.value(
            value_dt, forward_curve_up, domestic_curve, vol_surface, dc_type
        )

        if isinstance(v, dict):
            num = (
                v_up["value"] - 2.0 * v["value"] + v_down["value"]
            )
            gamma = num / ((bump / self.base_size) ** 2.0)
        else:
            gamma = (v_up - 2.0 * v + v_down) / ((bump / self.base_size) ** 2.0)

        return gamma

    ###########################################################################

    def vega(
        self, value_dt, forward_curve, domestic_curve, vol_surface, dc_type, bump=1
    ):
        """Calculate the option vega (volatility sensitivity) by adding on a
        small bump and calculating the change in the option price."""

        surface_up = vol_surface.bump_volatility(bump / 100)
        surface_down = vol_surface.bump_volatility(-bump / 100)

        v_up = self.value(
            value_dt, forward_curve, domestic_curve, surface_up, dc_type
        )

        v_down = self.value(
            value_dt, forward_curve, domestic_curve, surface_down, dc_type
        )

        if isinstance(v_up, dict):
            vega = (v_up["value"] - v_down["value"])  / (2.0 * bump)
        else:
            vega = (v_up - v_down) / (2.0 * bump)

        return vega

    ###########################################################################

    def theta(
        self, value_dt, forward_curve, domestic_curve, vol_surface, dc_type, bump=1
    ):
        """Calculate the option theta (calendar time sensitivity) by moving
        forward one day and calculating the change in the option price."""

        v = self.value(
            value_dt, forward_curve, domestic_curve, vol_surface, dc_type
        )

        next_dt = self.calendar.add_business_days(value_dt, bump)

        v_bumped = self.value(
            next_dt, forward_curve, domestic_curve, vol_surface, dc_type
        )

        if isinstance(v, dict):
            theta = (v_bumped["value"] - v["value"]) / bump
        else:
            theta = (v_bumped - v) / bump

        return theta

    ###########################################################################

    def rho(
        self, value_dt, forward_curve, domestic_curve, vol_surface, dc_type, bump=1, bump_type="pillar"
    ):
        """Calculate the option rho (domestic interest rate sensitivity) by perturbing
        the discount curve and revaluing."""

        if bump_type == "pillar":
            domestic_curve_up = domestic_curve.bump_curve(bump / 10000)
            domestic_curve_down = domestic_curve.bump_curve(-bump / 10000)
            forward_curve_up = forward_curve.bump_parallel(bump / 10000)
            forward_curve_down = forward_curve.bump_parallel(-bump / 10000)
        elif bump_type == "market":
            domestic_curve_up = domestic_curve.bump_parallel(bump / 10000)
            domestic_curve_down = domestic_curve.bump_parallel(-bump / 10000)
            forward_curve_up = forward_curve.bump_domestic_curve(domestic_curve, domestic_curve_up)
            forward_curve_down = forward_curve.bump_domestic_curve(domestic_curve, domestic_curve_down)
        else:
            raise FinError(f"Unsupported bump type: {bump_type}")

        v_up = self.value(
            value_dt, forward_curve_up, domestic_curve_up, vol_surface, dc_type
        )
        v_down = self.value(
            value_dt, forward_curve_down, domestic_curve_down, vol_surface, dc_type
        )

        if isinstance(v_up, dict):
            rho = (v_up["value"] - v_down["value"]) / (2.0 * bump)
        else:
            rho = (v_up - v_down) / (2.0 * bump)

        return rho

    ###########################################################################

    def phi(
        self, value_dt, forward_curve, domestic_curve, vol_surface, dc_type, bump=1, bump_type="pillar"
    ):
        """Calculate the option phi (foreign interest rate sensitivity) by perturbing
        the discount curve and revaluing."""

        if bump_type == "pillar":
            forward_curve_up = forward_curve.bump_parallel(bump / 10000)
            forward_curve_down = forward_curve.bump_parallel(-bump / 10000)
        elif bump_type == "market":
            domestic_curve_up = domestic_curve.bump_parallel(bump / 10000)
            domestic_curve_down = domestic_curve.bump_parallel(-bump / 10000)
            forward_curve_up = forward_curve.bump_domestic_curve(domestic_curve, domestic_curve_up)
            forward_curve_down = forward_curve.bump_domestic_curve(domestic_curve, domestic_curve_down)
        else:
            raise FinError(f"Unsupported bump type: {bump_type}")

        v_up = self.value(
            value_dt, forward_curve_down, domestic_curve, vol_surface, dc_type
        )
        v_down = self.value(
            value_dt, forward_curve_up, domestic_curve, vol_surface, dc_type
        )

        if isinstance(v_up, dict):
            rho = (v_up["value"] - v_down["value"]) / (2.0 * bump)
        else:
            rho = (v_up - v_down) / (2.0 * bump)

        return rho


##########################################################################
