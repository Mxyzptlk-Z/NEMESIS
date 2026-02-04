import numpy as np
from scipy.stats import norm
from numba import njit, float64

from ..utils.math import n_vect, n_prime_vect
from ..utils.global_vars import g_small
from ..utils.helpers import label_to_string
from ..utils.global_types import OptionTypes
from ..utils.error import FinError


# class Black:
#     """
#     Black's Model which prices call and put options in the forward
#     measure according to the Black-Scholes equation.
#     """

#     APPLICABLE_TYPES = [OptionTypes.EUROPEAN_CALL, OptionTypes.EUROPEAN_PUT,
#                         OptionTypes.BINARY_CALL, OptionTypes.BINARY_PUT]

#     def __init__(
#         self,
#         forward_rate,   # Forward Rate F
#         strike_rate,    # Strike Rate K
#         time_to_expiry,  # Time to Expiry (years)
#         volatility,  # Volatility σ
#         df,  # df RFR to expiry date
#         option_type: OptionTypes
#     ):
#         """Create FinModel black using parameters."""
#         if option_type in self.APPLICABLE_TYPES:
#             raise FinError(f"Option type must be one of {self.APPLICABLE_TYPES}")

#         self.f = forward_rate
#         self.t = time_to_expiry
#         self.k = strike_rate
#         self.v = volatility
#         self.r = -np.log(df) / time_to_expiry
#         self.option_type = option_type

#     ###############################################################################

#     def value_vanilla(self):
#         """
#         Price a vanilla option using Black's model which values in the forward
#         measure following a change of measure.
#         """
#         return vanilla(self.f, self.t, self.k, self.r, self.v, self.option_type)

#     ###############################################################################

#     def value_cash_or_nothing(self, cash):
#         """
#         Price a cash-or-nothing binary option using Black's model which values
#         in the forward measure following a change of measure.
#         """
#         return cash_or_nothing(cash, self.f, self.t, self.k, self.r, self.v, self.option_type)

#     ###############################################################################

#     def value_asset_or_nothing(self, f_pay):
#         """
#         Price a asset-or-nothing binary option using Black's model which values
#         in the forward measure following a change of measure.
#         """
#         return asset_or_nothing(f_pay, self.f, self.t, self.k, self.r, self.v, self.option_type)

#     ###############################################################################

#     def __repr__(self):
#         s = label_to_string("OBJECT TYPE", type(self).__name__)
#         return s

#     ###############################################################################


def black_value(fwd, t, k, r, v, option_type):
    """Price a vanilla option using Black model."""
    d1, d2 = calculate_d1_d2(fwd, t, k, v)
    if option_type == OptionTypes.EUROPEAN_CALL:
        # return np.exp(-r*t) * (fwd * n_vect(d1) - k * n_vect(d2))
        return np.exp(-r*t) * (fwd * norm.cdf(d1) - k * norm.cdf(d2))
    elif option_type == OptionTypes.EUROPEAN_PUT:
        # return np.exp(-r*t) * (k * n_vect(-d2) - fwd * n_vect(-d1))
        return np.exp(-r*t) * (k * norm.cdf(-d2) - fwd * norm.cdf(-d1))
    else:
        raise FinError("Option type must be a European Call or Put")


def cash_or_nothing(cash, fwd, t, k, r, v, option_type):
    """Price a binary cash-or-nothing option using Black model."""
    _, d2 = calculate_d1_d2(fwd, t, k, v)
    if option_type == OptionTypes.BINARY_CALL:
        # return cash * np.exp(-r*t) * n_vect(d2)
        return cash * np.exp(-r*t) * norm.cdf(d2)
    elif option_type == OptionTypes.BINARY_PUT:
        # return cash * np.exp(-r*t) * n_vect(-d2)
        return cash * np.exp(-r*t) * norm.cdf(-d2)
    else:
        raise FinError("Option type must be a Binary Call or Put")


def asset_or_nothing(f_pay, fwd, t, k, r, v, option_type):
    """Price a binary asset-or-nothing option using Black model."""
    d1, _ = calculate_d1_d2(fwd, t, k, v)
    if option_type == OptionTypes.BINARY_CALL:
        # return f_pay * np.exp(-r*t) * n_vect(d1)
        return f_pay * np.exp(-r*t) * norm.cdf(d1)
    elif option_type == OptionTypes.BINARY_PUT:
        # return f_pay * np.exp(-r*t) * n_vect(-d1)
        return f_pay * np.exp(-r*t) * norm.cdf(-d1)
    else:
        raise FinError("Option type must be a Binary Call or Put")


@njit(float64[:](float64, float64, float64, float64), fastmath=True,
      cache=True)
def calculate_d1_d2(f, t, k, v):

    t = np.maximum(t, g_small)
    vol = np.maximum(v, g_small)
    k = np.maximum(k, g_small)
    sqrt_t = np.sqrt(t)

    if f <= 0.0:
        raise FinError("Forward is zero.")

    if k <= 0.0:
        raise FinError("Strike is zero.")

    d1 = (np.log(f/k) + vol * vol * t / 2.0) / (vol * sqrt_t)
    d2 = d1 - vol * sqrt_t

    return np.array([d1, d2])
