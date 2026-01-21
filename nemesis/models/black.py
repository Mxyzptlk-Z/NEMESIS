from enum import Enum

import numpy as np
from numba import njit, float64

from ..utils.math import n_vect, n_prime_vect
from ..utils.global_vars import g_small
from ..utils.helpers import label_to_string
from ..utils.global_types import OptionTypes
from ..utils.error import FinError


class BlackTypes(Enum):
    ANALYTICAL = 1
    CRR_TREE = 2


class Black():
    """ Black's Model which prices call and put options in the forward
    measure according to the Black-Scholes equation. """

    def __init__(self, volatility, implementation_type=BlackTypes.ANALYTICAL,
                 num_steps=0):
        """ Create FinModel black using parameters. """
        self.volatility = volatility
        self.implementation_type = implementation_type
        self.num_steps = num_steps
        self.seed = 0
        self.param1 = 0
        self.param2 = 0

###############################################################################

    def value(self,
              forward_rate,   # Forward rate F
              strike_rate,    # Strike Rate K
              time_to_expiry,  # Time to Expiry (years)
              df,  # df RFR to expiry date
              option_type):    # Call or put
        """ Price a derivative using Black's model which values in the forward
        measure following a change of measure. """

        f = forward_rate
        t = time_to_expiry
        k = strike_rate
        v = self.volatility
        r = -np.log(df)/t
        if option_type in (OptionTypes.EUROPEAN_CALL,
                           OptionTypes.EUROPEAN_PUT):
            if self.implementation_type == BlackTypes.ANALYTICAL:
                value = black_value(f, t, k, r, v, option_type)
            else:
                raise FinError("Implementation not available for this product")

        else:
            raise FinError(
                "Option type must be a European Call or Put")
        return value

###############################################################################

    def __repr__(self):
        s = label_to_string("OBJECT TYPE", type(self).__name__)
        s += label_to_string("VOLATILITY", self.volatility)
        s += label_to_string("IMPLEMENTATION", self.implementation_type)
        s += label_to_string("NUMSTEPS", self.num_steps)
        return s

###############################################################################


def black_value(fwd, t, k, r, v, option_type):
    """ Price a derivative using Black model. """
    d1, d2 = calculate_d1_d2(fwd, t, k, v)
    if option_type == OptionTypes.EUROPEAN_CALL:
        return np.exp(-r*t) * (fwd * n_vect(d1) - k * n_vect(d2))
    elif option_type == OptionTypes.EUROPEAN_PUT:
        return np.exp(-r*t) * (k * n_vect(-d2) - fwd * n_vect(-d1))
    else:
        raise FinError("Option type must be a European Call or Put")


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

