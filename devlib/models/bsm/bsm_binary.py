import math
from scipy.stats import norm



def cash_or_nothing(flavor, s, strike, cash, t, r, b, sigma):
    d2 = (math.log(s / strike) + (b - sigma**2 / 2) * t) / (sigma * math.sqrt(t))

    if flavor == 'call':
        return cash * math.exp(-r * t) * norm.cdf(d2)
    elif flavor == 'put':
        return cash * math.exp(-r * t) * norm.cdf(-d2)
    else:
        raise Exception('Binary option type error!')



def asset_or_nothing(flavor, s, strike, t, r, b, sigma):
    d1 = (math.log(s / strike) + (b + sigma**2 / 2) * t) / (sigma * math.sqrt(t))
    if flavor == 'call':
        return s * math.exp((b - r) * t) * norm.cdf(d1)
    elif flavor == 'put':
        return s * math.exp((b - r) * t) * norm.cdf(-d1)
    else:
        raise Exception('Binary option type error!')



if __name__ == "__main__":
    adays = 365
    flavor, s, strike, cash, t, r, b, sigma = ['call', 100, 104, 1, 180/adays, 0.02, 0, 0.056]
    print(cash_or_nothing(flavor, s, strike, cash, t , r , b , sigma))
