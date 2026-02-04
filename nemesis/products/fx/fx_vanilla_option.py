import numpy as np

from ...utils.calendar import Calendar, CalendarTypes
from ...utils.date import Date
from ...utils.day_count import DayCount, DayCountTypes
from ...utils.error import FinError
from ...utils.global_types import OptionTypes
from ...utils.helpers import check_argument_types, label_to_string
from ...models.black_analytic import black_value
from ...market.curves.discount_curve import DiscountCurve
from ...market.curves.forward_curve import ForwardCurve
from ...market.volatility.vol_surface import VolSurface

from .fx_option import FXOption


###############################################################################
# ALL CCY RATES MUST BE IN NUM UNITS OF DOMESTIC PER UNIT OF FOREIGN CURRENCY
# SO EURUSD = 1.30 MEANS 1.30 DOLLARS PER EURO SO DOLLAR IS THE DOMESTIC AND
# EUR IS THE FOREIGN CURRENCY
###############################################################################


class FXVanillaOption(FXOption):
    """This is a class for an FX Option trade. It permits the user to
    calculate the price of an FX Option trade which can be expressed in a
    number of ways depending on the investor or hedger's currency. It aslo
    allows the calculation of the option's delta in a number of forms as
    well as the various Greek risk sensitivies."""

    def __init__(
        self,
        expiry_dt: Date,
        strike_fx_rate: float, # 1 unit of foreign in domestic
        currency_pair: str,  # FORDOM
        option_type: OptionTypes,
        notional: float,
        prem_currency: str,
        cal_type: CalendarTypes,
        spot_days: int = 0
    ):
        """Create the FX Vanilla Option object. Inputs include expiry date,
        strike, currency pair, option type (call or put), notional and the
        currency of the notional. And adjustment for spot days is enabled. All
        currency rates must be entered in the price in domestic currency of
        one unit of foreign. And the currency pair should be in the form FORDOM
        where FOR is the foreign currency pair currency code and DOM is the
        same for the domestic currency."""

        check_argument_types(self.__init__, locals())

        super().__init__(currency_pair, cal_type)

        delivery_dt = self.calendar.add_business_days(expiry_dt, spot_days)

        """ The FX rate the price in domestic currency ccy2 of a single unit
        of the foreign currency which is ccy1. For example EURUSD of 1.3 is the
        price in USD (CCY2) of 1 unit of EUR (CCY1)"""

        if delivery_dt < expiry_dt:
            raise FinError("Delivery date must be on or after expiry date.")

        self.expiry_dt = expiry_dt
        self.delivery_dt = delivery_dt

        if np.any(strike_fx_rate < 0.0):
            raise FinError("Negative strike.")

        self.strike_fx_rate = strike_fx_rate

        if prem_currency != self.dom_name and prem_currency != self.for_name:
            raise FinError("Premium currency not in currency pair.")

        self.prem_currency = prem_currency

        self.notional = notional

        if (
            option_type != OptionTypes.EUROPEAN_CALL
            and option_type != OptionTypes.EUROPEAN_PUT
        ):
            raise FinError("Unknown Option Type:" + option_type)

        self.option_type = option_type
        self.spot_days = spot_days

    ###########################################################################

    def value(
        self,
        value_dt: Date,
        forward_curve: ForwardCurve,
        domestic_curve: DiscountCurve,
        vol_surface: VolSurface,
        dc_type: DayCountTypes
    ):
        """This function calculates the value of the option using a specified
        model with the resulting value being in domestic i.e. ccy2 terms.
        Recall that Domestic = CCY2 and Foreign = CCY1 and FX rate is in
        price in domestic of one unit of foreign currency."""

        if not isinstance(value_dt, Date):
            raise FinError("Valuation date is not a Date")

        if value_dt > self.expiry_dt:
            raise FinError("Valuation date after expiry date.")

        # if domestic_curve.value_dt != value_dt:
        #     raise FinError(
        #         "Domestic Curve valuation date not same as valuation date"
        #     )

        day_count = DayCount(dc_type)
        t_exp = day_count.year_frac(value_dt, self.expiry_dt)[0]

        if t_exp < 0.0:
            raise FinError("Time to expiry must be positive.")

        t_exp = np.maximum(t_exp, 1e-10)

        dom_df = domestic_curve.df(self.delivery_dt, dc_type) / domestic_curve.df(value_dt, dc_type)
        r_d = -np.log(dom_df) / t_exp

        k = self.strike_fx_rate
        fwd = forward_curve.get_forward(self.delivery_dt, dc_type)

        volatility = vol_surface.interp_vol(self.expiry_dt, self.strike_fx_rate)

        if np.any(volatility < 0.0):
            raise FinError("Volatility should not be negative.")

        v = np.maximum(volatility, 1e-10)

        vdf = black_value(
            fwd, t_exp, k, r_d, v, self.option_type
        )

        # The option value v is in domestic currency terms but the value of
        # the option may be quoted in either currency terms and so we calculate
        # these

        if self.prem_currency == self.dom_name:
            notional_dom = self.notional
            notional_for = self.notional / self.strike_fx_rate
        elif self.prem_currency == self.for_name:
            notional_dom = self.notional * self.strike_fx_rate
            notional_for = self.notional
        else:
            raise FinError("Invalid notional currency.")

        vdf = vdf
        spot_fx_rate = forward_curve.spot_rate

        pips_dom = vdf
        pips_for = vdf / (spot_fx_rate * self.strike_fx_rate)

        cash_dom = vdf * notional_dom / self.strike_fx_rate
        cash_for = vdf * notional_for / spot_fx_rate

        pct_dom = vdf / self.strike_fx_rate
        pct_for = vdf / spot_fx_rate

        return {
            "value": vdf,
            "cash_dom": cash_dom,
            "cash_for": cash_for,
            "pips_dom": pips_dom,
            "pips_for": pips_for,
            "pct_dom": pct_dom,
            "pct_for": pct_for,
            "not_dom": notional_dom,
            "not_for": notional_for,
            "ccy_dom": self.dom_name,
            "ccy_for": self.for_name,
        }

    ###########################################################################

    def __repr__(self):
        s = label_to_string("OBJECT TYPE", type(self).__name__)
        s += label_to_string("EXPIRY DATE", self.expiry_dt)
        s += label_to_string("CURRENCY PAIR", self.currency_pair)
        s += label_to_string("PREMIUM CCY", self.prem_currency)
        s += label_to_string("STRIKE FX RATE", self.strike_fx_rate)
        s += label_to_string("OPTION TYPE", self.option_type)
        s += label_to_string("SPOT DAYS", self.spot_days)
        s += label_to_string("NOTIONAL", self.notional, "")
        return s

    ###########################################################################

    def _print(self):
        """Simple print function for backward compatibility."""
        print(self)


###############################################################################
