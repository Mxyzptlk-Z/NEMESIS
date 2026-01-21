import math
from scipy.stats import norm
import numpy as np


# Adjust barrier level when monitoring discretely
def discrete_adjusted_barrier(s, barrier, sigma, dt):
    if barrier > s:
        return barrier * math.exp(0.5826 * sigma * math.sqrt(dt))
    elif barrier < s:
        return barrier * math.exp(-0.5826 * sigma * math.sqrt(dt))
    else:
        return barrier



# standard barrier options
def standard_barrier(type_flag, s, strike, barrier, rebate, t, r, carry, sigma):
    #    the 'type_flag' gives you 8 different standard barrier options:
    #    1) 'cdi' = Down-and-in call,    2) 'cui' = Up-and-in call
    #    3) 'pdi' = Down-and-in put,     4) 'pui' = Up-and-in put
    #    5) 'cdo' = Down-and-out call,   6) 'cuo' = Up-out-in call
    #    7) 'pdo' = Down-and-out put,    8) 'puo' = Up-out-in put

    # eta :Binary variable that can take the value of 1 or -1
    # phi :Binary variable that can take the value of 1 or -1

    #    Dim f1    'Equal to formula ' A'  in the book
    #    Dim f2    'Equal to formula ' B'  in the book
    #    Dim f3    'Equal to formula ' C'  in the book
    #    Dim f4    'Equal to formula ' D'  in the book
    #    Dim f5    'Equal to formula ' E'  in the book
    #    Dim f6    'Equal to formula ' F'  in the book

    mu = (carry - sigma ** 2 / 2) / sigma ** 2
    lmbda = math.sqrt(mu ** 2 + 2 * r / sigma ** 2)
    x1 = math.log(s / strike) / (sigma * math.sqrt(t)) + (1 + mu) * sigma * math.sqrt(t)
    x2 = math.log(s / barrier) / (sigma * math.sqrt(t)) + (1 + mu) * sigma * math.sqrt(t)
    y1 = math.log(barrier ** 2 / (s * strike)) / (sigma * math.sqrt(t)) + (1 + mu) * sigma * math.sqrt(t)
    y2 = math.log(barrier / s) / (sigma * math.sqrt(t)) + (1 + mu) * sigma * math.sqrt(t)
    z = math.log(barrier / s) / (sigma * math.sqrt(t)) + lmbda * sigma * math.sqrt(t)

    if type_flag == 'cdi' or type_flag == 'cdo':
        eta = 1
        phi = 1
    elif type_flag == 'cui' or type_flag == 'cuo':
        eta = -1
        phi = 1
    elif type_flag == 'pdi' or type_flag == 'pdo':
        eta = 1
        phi = -1
    elif type_flag == 'pui' or type_flag == 'puo':
        eta = -1
        phi = -1
    else:
        raise Exception('Standard barrier type_flag error!')

    f1 = (phi * s * math.exp((carry - r) * t) * norm.cdf(phi * x1) - 
          phi * strike * math.exp(-r * t) * norm.cdf(phi * x1 - phi * sigma * math.sqrt(t)))
    f2 = (phi * s * math.exp((carry - r) * t) * norm.cdf(phi * x2) - 
          phi * strike * math.exp(-r * t) * norm.cdf(phi * x2 - phi * sigma * math.sqrt(t)))
    f3 = (phi * s * math.exp((carry - r) * t) * (barrier / s) ** (2 * (mu + 1)) * norm.cdf(eta * y1) - 
          phi * strike * math.exp(-r * t) * (barrier / s) ** (2 * mu) * norm.cdf(eta * y1 - eta * sigma * math.sqrt(t)))
    f4 = (phi * s * math.exp((carry - r) * t) * (barrier / s) ** (2 * (mu + 1)) * norm.cdf(eta * y2) - 
          phi * strike * math.exp(-r * t) * (barrier / s) ** (2 * mu) * norm.cdf(eta * y2 - eta * sigma * math.sqrt(t)))
    f5 = rebate * math.exp(-r * t) * (norm.cdf(eta * x2 - eta * sigma * math.sqrt(t)) - 
                                      (barrier / s) ** (2 * mu) * norm.cdf(eta * y2 - eta * sigma * math.sqrt(t)))
    f6 = rebate * ((barrier / s) ** (mu + lmbda) * norm.cdf(eta * z) + 
                   (barrier / s) ** (mu - lmbda) * norm.cdf(eta * z - 2 * eta * lmbda * sigma * math.sqrt(t)))

    if strike > barrier:
        if type_flag == 'cdi':  # 1a) cdi
            return f3 + f5
        elif type_flag == 'cui':  # 2a) cui
            return f1 + f5
        elif type_flag == 'pdi':  # 3a) pdi
            return f2 - f3 + f4 + f5
        elif type_flag == 'pui':  # 4a) pui
            return f1 - f2 + f4 + f5
        elif type_flag == 'cdo':  # 5a) cdo
            return f1 - f3 + f6
        elif type_flag == 'cuo':  # 6a) cuo
            return f6
        elif type_flag == 'pdo':  # 7a) pdo
            return f1 - f2 + f3 - f4 + f6
        elif type_flag == 'puo':  # 8a) puo
            return f2 - f4 + f6

    elif strike < barrier:
        if type_flag == 'cdi':  # 1b) cdi
            return f1 - f2 + f4 + f5
        elif type_flag == 'cui':  # 2b) cui
            return f2 - f3 + f4 + f5
        elif type_flag == 'pdi':  # 3b) pdi
            return f1 + f5
        elif type_flag == 'pui':  # 4b) pui
            return f3 + f5
        elif type_flag == 'cdo':  # 5b) cdo
            return f2 + f6 - f4
        elif type_flag == 'cuo':  # 6b) cuo
            return f1 - f2 + f3 - f4 + f6
        elif type_flag == 'pdo':  # 7b) pdo
            return f6
        elif type_flag == 'puo':  # 8b) puo
            return f1 - f3 + f6

    else:
        raise Exception('Strike should not be equal to barrier!')



#  Binary barrier options
def binary_barrier(type_flag, s, strike, barrier, rebate, t, r, b, sigma):
    #  type_flag:  value 1 to 28 dependent on binary option type, look in the book for spesifications.

    if type_flag in [1, 3, 9, 11, 13, 15, 21, 23]:
        eta = 1
        phi = 1
    elif type_flag in [2, 4, 6, 8, 14, 16, 22, 24]:
        eta = -1
        phi = 1
    elif type_flag in [5, 7, 17, 19, 25, 27]:
        eta = 1
        phi = -1
    elif type_flag in [10, 12, 18, 20, 26, 28]:
        eta = -1
        phi = -1
    else:
        raise Exception('Wrong type flag!')

    mu = (b - sigma ** 2 / 2) / sigma ** 2
    lmbda = math.sqrt(mu ** 2 + 2 * r / sigma ** 2)
    x1 = math.log(s / strike) / (sigma * math.sqrt(t)) + (mu + 1) * sigma * math.sqrt(t)
    x2 = math.log(s / barrier) / (sigma * math.sqrt(t)) + (mu + 1) * sigma * math.sqrt(t)
    y1 = math.log(barrier ** 2 / (s * strike)) / (sigma * math.sqrt(t)) + (mu + 1) * sigma * math.sqrt(t)
    y2 = math.log(barrier / s) / (sigma * math.sqrt(t)) + (mu + 1) * sigma * math.sqrt(t)
    z = math.log(barrier / s) / (sigma * math.sqrt(t)) + lmbda * sigma * math.sqrt(t)

    a1 = s * math.exp((b - r) * t) * norm.cdf(phi * x1)
    b1 = rebate * math.exp(-r * t) * norm.cdf(phi * x1 - phi * sigma * math.sqrt(t))
    a2 = s * math.exp((b - r) * t) * norm.cdf(phi * x2)
    b2 = rebate * math.exp(-r * t) * norm.cdf(phi * x2 - phi * sigma * math.sqrt(t))
    a3 = s * math.exp((b - r) * t) * (barrier / s) ** (2 * (mu + 1)) * norm.cdf(eta * y1)
    b3 = rebate * math.exp(-r * t) * (barrier / s) ** (2 * mu) * norm.cdf(eta * y1 - eta * sigma * math.sqrt(t))
    a4 = s * math.exp((b - r) * t) * (barrier / s) ** (2 * (mu + 1)) * norm.cdf(eta * y2)
    b4 = rebate * math.exp(-r * t) * (barrier / s) ** (2 * mu) * norm.cdf(eta * y2 - eta * sigma * math.sqrt(t))
    a5 = rebate * ((barrier / s) ** (mu + lmbda) * norm.cdf(eta * z) + 
                   (barrier / s) ** (mu - lmbda) * norm.cdf(eta * z - 2 * eta * lmbda * sigma * math.sqrt(t)))

    if strike > barrier:
        if type_flag < 5:
            return a5
        elif type_flag < 7:
            return b2 + b4
        elif type_flag < 9:
            return a2 + a4
        elif type_flag < 11:
            return b2 - b4
        elif type_flag < 13:
            return a2 - a4
        elif type_flag == 13:
            return b3
        elif type_flag == 14:
            return b3
        elif type_flag == 15:
            return a3
        elif type_flag == 16:
            return a1
        elif type_flag == 17:
            return b2 - b3 + b4
        elif type_flag == 18:
            return b1 - b2 + b4
        elif type_flag == 19:
            return a2 - a3 + a4
        elif type_flag == 20:
            return a1 - a2 + a3
        elif type_flag == 21:
            return b1 - b3
        elif type_flag == 22 or type_flag == 24:
            return 0
        elif type_flag == 23:
            return a1 - a3
        elif type_flag == 25:
            return b1 - b2 + b3 - b4
        elif type_flag == 26:
            return b2 - b4
        elif type_flag == 27:
            return a1 - a2 + a3 - a4
        elif type_flag == 28:
            return a2 - a4
        else:
            raise Exception('Wrong type flag!')

    elif strike < barrier:
        if type_flag < 5:
            return a5
        elif type_flag < 7:
            return b2 + b4
        elif type_flag < 9:
            return a2 + a4
        elif type_flag < 11:
            return b2 - b4
        elif type_flag < 13:
            return a2 - a4
        elif type_flag == 13:
            return b1 - b2 + b4
        elif type_flag == 14:
            return b2 - b3 + b4
        elif type_flag == 15:
            return a1 - a2 + a4
        elif type_flag == 16:
            return a2 - a3 + a4
        elif type_flag == 17:
            return b1
        elif type_flag == 18:
            return b3
        elif type_flag == 19:
            return a1
        elif type_flag == 20:
            return a3
        elif type_flag == 21:
            return b2 - b4
        elif type_flag == 22:
            return b1 - b2 + b3 - b4
        elif type_flag == 23:
            return a2 - a4
        elif type_flag == 24:
            return a1 - a2 + a3 - a4
        elif type_flag == 25 or type_flag == 27:
            return 0
        elif type_flag == 26:
            return b1 - b3
        elif type_flag == 28:
            return a1 - a3
        else:
            raise Exception('Wrong type flag!')

    else:
        return 0
    

def double_barrier_binary(type_flag, s, strike_down, strike_up, rebate, t, r, b, sigma):

    alpha = -0.5 * (2 * b / sigma**2 - 1)
    beta = -0.25 * (2 * b / sigma**2 - 1)**2 - 2 * r / sigma**2 
    z = math.log(strike_up / strike_down)
    
    npv = 0
    for i in range(1,51):
        npv = npv + 2 * np.pi * i * rebate / z**2 * \
            (((s / strike_down)**alpha - (-1)**i * (s / strike_up)**alpha) / 
             (alpha**2 + (i * np.pi / z)**2)) * math.sin(i * np.pi / z * math.log(s / strike_down)) * \
             math.exp(-0.5 * ((i * np.pi / z)**2 - beta) * sigma**2 * t)
    
    if type_flag == 'o':  #  // Knock-out
        return npv
    
    elif type_flag == 'i':  #  // Knock-in
        return rebate * math.exp(-r * t) - npv
    
    else:
        print('TypeFlag Error, it should be o(out) or i(in)')
        return math.nan

