from math import *
from scipy.stats import norm

class NegativeSigmaError(ValueError):
    """波动率为负数时抛出的专属异常"""
    pass


# Black76 version(forward option version)

def vanilla_76(flavor, f, strike, t, sigma, df):
    if sigma <= 0:
        raise NegativeSigmaError("波动率sigma不能为负数，当前值：{}".format(sigma))
        
    # flavor are 'c' -> call option, 'p' -> put option
    d1 = (log(f / strike) + sigma**2 / 2 * t) / (sqrt(t) * sigma)
    d2 = (log(f / strike) - sigma**2 / 2 * t) / (sqrt(t) * sigma)

    if flavor == 'call':
        return df * (f * norm.cdf(d1) - strike * norm.cdf(d2))
    elif flavor == 'put':
        return df * (-f * norm.cdf(-d1) + strike * norm.cdf(-d2))
    else:
        raise Exception('Vanilla option type error!')



def cash_or_nothing_76(flavor, f, strike, cash, t, sigma, df):
    if sigma <= 0:
        raise NegativeSigmaError("波动率sigma不能为负数，当前值：{}".format(sigma))
        
    d2 = (log(f / strike) - sigma**2 / 2 * t) / (sqrt(t) * sigma)

    if flavor == 'call':
        return df * cash * norm.cdf(d2)
    elif flavor == 'put':
        return df * cash * norm.cdf(-d2)
    else:
        raise Exception('Binary option type error!')



def asset_or_nothing_76(flavor, f, strike, t, sigma, f_pay, df):
    if sigma <= 0:
        raise NegativeSigmaError("波动率sigma不能为负数，当前值：{}".format(sigma))
        
    d1 = (log(f / strike) + sigma**2 / 2 * t) / (sqrt(t) * sigma)

    if flavor == 'call':
        return df * f_pay * norm.cdf(d1)
    elif flavor == 'put':
        return df * f_pay * norm.cdf(-d1)
    else:
        raise Exception('Binary option type error!')