from ...utils.date import Date
from ...utils.error import FinError
from ...utils.helpers import check_argument_types, label_to_string
from .fx_forward import FXForward

###############################################################################
# ALL CCY RATES MUST BE IN NUM UNITS OF DOMESTIC PER UNIT OF FOREIGN CURRENCY
# SO EUR USD = 1.30 MEANS 1.30 DOLLARS PER EURO SO DOLLAR IS THE DOMESTIC AND
# EUR IS THE FOREIGN CURRENCY
###############################################################################


class FXSwap:
    """Contract to buy or sell currency at a forward rate decided today."""

    def __init__(
        self,
        near_expiry_dt: Date,
        far_expiry_dt: Date,
        spot_fx_rate: float,  # 1 unit of foreign in domestic
        forward_point: float,
        currency_pair: str,  # FOR DOM
        notional: float,
        notional_currency: str,  # must be FOR or DOM
        spot_days: int = 0,
    ):
        """Creates a FinFXForward which allows the owner to buy the FOR
        against the DOM currency at the strike_fx_rate and to pay it in the
        notional currency."""

        check_argument_types(self.__init__, locals())

        """ The FX rate is the price in domestic currency ccy2 of a single unit
        of the foreign currency which is ccy1. For example EURUSD of 1.3 is the
        price in USD (CCY2) of 1 unit of EUR (CCY1) """

        if len(currency_pair) != 6:
            raise FinError("Currency pair must be 6 characters.")

        self.near_expiry_dt = near_expiry_dt
        self.far_expiry_dt = far_expiry_dt
        self.spot_fx_rate = spot_fx_rate
        self.forward_point = forward_point
        self.forward_fx_rate = spot_fx_rate + forward_point / 10000

        self.currency_pair = currency_pair
        self.for_name = self.currency_pair[0:3]
        self.dom_name = self.currency_pair[3:6]

        if (
            notional_currency != self.dom_name
            and notional_currency != self.for_name
        ):
            raise FinError("Notional currency not in currency pair.")

        self.notional = notional
        self.notional_currency = notional_currency
        self.spot_days = spot_days
        self.notional_dom = None
        self.notional_for = None
        self.cash_dom = None
        self.cash_for = None

        self.near_leg = FXForward(
            near_expiry_dt,
            spot_fx_rate,
            spot_fx_rate,
            currency_pair,
            notional,
            self.for_name,
            spot_days
        )

        self.far_leg = FXForward(
            far_expiry_dt,
            spot_fx_rate,
            self.forward_fx_rate,
            currency_pair,
            notional,
            self.for_name,
            spot_days
        )

    ###########################################################################

    def value(
        self,
        value_dt,
        domestic_curve,
        foreign_curve,
    ):
        """Calculate the value of an FX swap contract where the current
        FX rate is the spot_fx_rate."""

        near_leg_value = self.near_leg.value(
            value_dt, domestic_curve, foreign_curve
        )

        far_leg_value = self.far_leg.value(
            value_dt, domestic_curve, foreign_curve
        )

        result = {}
        result["value"] = near_leg_value["value"] - far_leg_value["value"]
        result["cash_dom"] = near_leg_value["cash_dom"] - far_leg_value["cash_dom"]
        result["cash_for"] = near_leg_value["cash_for"] - far_leg_value["cash_for"]
        result["not_dom"] = near_leg_value["not_dom"]
        result["not_for"] = near_leg_value["not_for"]
        result["ccy_dom"] = near_leg_value["ccy_dom"]
        result["ccy_for"] = near_leg_value["ccy_for"]

        return result

    ###########################################################################

    def __repr__(self):
        s = label_to_string("OBJECT TYPE", type(self).__name__)
        # s += label_to_string("EXPIRY DATE", self.expiry_dt)
        # s += label_to_string("STRIKE FX RATE", self.strike_fx_rate)
        s += label_to_string("CURRENCY PAIR", self.currency_pair)
        s += label_to_string("NOTIONAL", self.notional)
        s += label_to_string("NOTIONAL CCY", self.notional_currency)
        s += label_to_string("SPOT DAYS", self.spot_days, "")
        return s

    ###########################################################################

    def _print(self):
        """Simple print function for backward compatibility."""
        print(self)

    ###############################################################################
