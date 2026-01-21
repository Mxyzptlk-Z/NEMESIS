from math import *
import scipy.stats as st
from scipy.stats import norm, lognorm
from scipy.integrate import quad
import numpy as np


#%% Vanilla options
def vanilla(flavor, s, strike, t, r, b, sigma):
    # flavor are 'call' -> call option, 'put' -> put option
    d1 = (log(s / strike) + (b + sigma**2 / 2) * t) / (sqrt(t) * sigma)
    d2 = (log(s / strike) + (b - sigma**2 / 2) * t) / (sqrt(t) * sigma)

    if flavor == 'call':
        return s * exp((b - r) * t) * norm.cdf(d1) - strike * exp(-r * t) * norm.cdf(d2)
    elif flavor == 'put':
        return strike * exp(-r * t) * norm.cdf(-d2) - s * exp((b - r) * t) * norm.cdf(-d1)
    else:
        raise Exception('Vanilla option type error!')


def vanilla_delta(flavor, s, strike, t, r, b, sigma):
    d1 = (log(s / strike) + (b + sigma**2 / 2) * t) / (sqrt(t) * sigma)
    
    if flavor == 'call':
        return exp((b - r) * t) * norm.cdf(d1)
    elif flavor == 'put':
        return exp((b - r) * t) * (norm.cdf(d1) - 1)
    else:
        raise Exception('Vanilla option type error!')


def vanilla_gamma(s, strike, t, r, b, sigma):
    d1 = (log(s / strike) + (b + sigma**2 / 2) * t) / (sqrt(t) * sigma)
    
    return exp((b - r) * t) * norm.pdf(d1) / (sigma*sqrt(t))


def vanilla_vega(s, strike, t, r, b, sigma):
    d1 = (log(s / strike) + (b + sigma**2 / 2) * t) / (sqrt(t) * sigma)
    
    return exp((b - r) * t) * norm.pdf(d1) * s * sqrt(t)


def vanilla_rho(flavor, s, strike, t, r, b, sigma):
    d2 = (log(s / strike) + (b - sigma**2 / 2) * t) / (sqrt(t) * sigma)

    if flavor == 'call':
        return t * strike * exp(-r * t) * norm.cdf(d2)
    elif flavor == 'put':
        return -t * strike * exp(-r * t) * norm.cdf(-d2)
    else:
        raise Exception('Vanilla option type error!')


def vanilla_theta(flavor, s, strike, t, r, b, sigma):
    d1 = (log(s / strike) + (b + sigma**2 / 2) * t) / (sqrt(t) * sigma)
    d2 = (log(s / strike) + (b - sigma**2 / 2) * t) / (sqrt(t) * sigma)
    q = b - r
    
    if flavor == 'call':
        return (-s * exp(q * t) * norm.pdf(d1) * sigma / (2 * sqrt(t)) - 
                q * s * exp(q * t) * norm.cdf(d1) - 
                r * strike * exp(-r * t) * norm.cdf(d2))
    elif flavor == 'put':
        return (-s * exp(q * t) * norm.pdf(d1) * sigma / (2 * sqrt(t)) + 
                q * s * exp(q * t) * norm.cdf(-d1) + 
                r * strike * exp(-r * t) * norm.cdf(-d2))
    else:
        raise Exception('Vanilla option type error!')


#%% The Bjerksund and Stensland (2002) American approximation
def bs_american_approx_2002(flavor, s, strike, t, r, b, sigma):
    # flavor are 'call' -> call option, 'put' -> put option
    if flavor == 'call':
        return bs_american_call_approx_2002(s, strike, t, r, b, sigma)
  
    elif flavor == 'put':
    # Use the Bjerksund and Stensland put-call transformation 
        return bs_american_call_approx_2002(strike, s, t, r - b, -b, sigma)
    
    else:
        raise Exception('Vanilla option type error!')
    

def bs_american_call_approx_2002(S, X, T, r, b, v):
    t1 = 1/2 * (sqrt(5) - 1) * T
  
    if b >= r:  # Never optimal to exersice before maturity
        return vanilla('call', S, X, T, r, b, v)
  
    else:
        Beta = (1/2 - b/v**2) + sqrt((b/v**2 - 1/2)**2 + 2*r/v**2)
        BInfinity = Beta / (Beta - 1) * X
        B0 = max(X, r/(r - b)*X)
        
        ht1 = -(b*t1 + 2*v*sqrt(t1)) * X**2 / ((BInfinity - B0) * B0)
        ht2 = -(b*T + 2*v*sqrt(T)) * X**2 / ((BInfinity - B0) * B0)
        I1 = B0 + (BInfinity - B0) * (1 - exp(ht1))
        I2 = B0 + (BInfinity - B0) * (1 - exp(ht2))
        alfa1 = (I1 - X) * I1**(-Beta)
        alfa2 = (I2 - X) * I2**(-Beta)
    
        if S >= I2:
            return S - X
        else:
            return (alfa2 * S**Beta - alfa2*phi(S, t1, Beta, I2, I2, r, b, v) + 
                    phi(S, t1, 1, I2, I2, r, b, v) - phi(S, t1, 1, I1, I2, r, b, v) - 
                    X*phi(S,t1,0,I2,I2,r,b,v) + X*phi(S,t1,0,I1,I2,r,b,v) + 
                    alfa1 * phi(S, t1, Beta, I1, I2, r, b, v) - 
                    alfa1 * ksi(S, T, Beta, I1, I2, I1, t1, r, b, v) + 
                    ksi(S,T,1,I1,I2,I1,t1,r,b,v) - ksi(S,T,1,X,I2,I1,t1,r,b,v) - 
                    X*ksi(S,T,0,I1,I2,I1,t1,r,b,v) + X*ksi(S,T,0,X,I2,I1,t1,r,b,v))
         

def phi(S, T, gamma, h, i, r, b, v):
    
    lmda = (-r + gamma*b + 0.5*gamma*(gamma - 1) * v**2) * T
    d = -(log(S/h) + (b + (gamma - 0.5) * v**2)*T) / (v * sqrt(T))
    kappa = 2*b / (v**2) + (2*gamma - 1)
    
    return exp(lmda) * S**gamma * (st.norm.cdf(d) - 
                    (i/S)**kappa * st.norm.cdf(d - 2*log(i/S)/(v*sqrt(T))))


def ksi(S, T2, gamma, h, I2, I1, t1, r, b, v):
    e1 = (log(S/I1) + (b + (gamma - 0.5)*v**2)*t1) / (v*sqrt(t1))
    e2 = (log(I2**2 / (S*I1)) + (b + (gamma - 0.5)*v**2)*t1) / (v*sqrt(t1))
    e3 = (log(S/I1) - (b + (gamma - 0.5)*v**2)*t1) / (v*sqrt(t1))
    e4 = (log(I2**2 / (S*I1)) - (b + (gamma - 0.5)*v**2)*t1) / (v*sqrt(t1))
  
    f1 = (log(S/h) + (b + (gamma - 0.5)*v**2)*T2) / (v*sqrt(T2))
    f2 = (log(I2**2 / (S*h)) + (b + (gamma - 0.5)*v**2)*T2) / (v*sqrt(T2))
    f3 = (log(I1**2 / (S*h)) + (b + (gamma - 0.5)*v**2)*T2) / (v*sqrt(T2))
    f4 = (log((S*I1**2) / (h*I2**2)) + 
          (b + (gamma - 0.5)*v**2) * T2) / (v*sqrt(T2))
  
    rho = sqrt(t1 / T2)
    lmda = -r + gamma * b + 0.5 * gamma * (gamma - 1) * v**2
    kappa = 2 * b / (v**2) + (2 * gamma - 1)
  
    return exp(lmda * T2) * S**gamma * \
           (double_norm_cdf(-e1, -f1, rho) - (I2 / S)**kappa * double_norm_cdf(-e2, -f2, rho) -
            (I1 / S)**kappa * double_norm_cdf(-e3, -f3, -rho) + 
            (I1 / I2)**kappa * double_norm_cdf(-e4, -f4, -rho))


def double_norm_cdf(x, y, rho):
    return st.multivariate_normal.cdf([x, y], mean = [0, 0], cov=[[1, rho], [rho, 1]])


#%% The Haug, Haug and Margrabe (2003) Dicrete Asian approximation
def discrete_asian_HHM(flavor, spot, strike, ts, T, r, b, sigma, SA):

    def get_F(spot, t, b):
        return spot * np.exp(b*t)
    
    def get_EA(Fs):
        return np.mean(Fs)
    
    def get_EA2(Fs, sigmas, ts):
        n = len(Fs)
        add = Fs[-1]**2 * np.exp(sigmas[-1]**2 * ts[-1])
        if n >= 2:
            Fs_reverse_cumsum = np.cumsum(Fs[::-1])[-2::-1]
            add_factor = map(lambda F, sigma, t, cumsum_part:
                              F**2 * np.exp(sigma**2 * t) + 2 * F * np.exp(sigma**2 * t) * cumsum_part,
                              Fs[:-1], sigmas[:-1], ts[:-1], Fs_reverse_cumsum)
            add += np.sum(np.fromiter(add_factor, dtype=float)) 
        return add / n**2
    
    
    n = len(ts)
    m = np.sum(ts <= 0)
    if m == 0:
        SA = 0
    n_adj = n-m
    
    ts = np.sort(ts)
    ts_adj = ts[m:]
    
    Fs = np.array([get_F(spot, x, b) for x in ts_adj])
    
    if m*SA >= n*strike: # Judge option status #等号
        if flavor == 'put': # Put must be out-of-the-money
            return 0
        else: # Exercise is certain for call
            EA = get_EA(Fs)
            SA_all = (SA * m + EA * n_adj) / n
            return (SA_all - strike) * np.exp(-r * T)
    
    strike_adj = (n*strike - m*SA) / n_adj
    qty_adj = n_adj / n
    
    if n_adj == 1: # Only one fix left # 简便计算
        return vanilla(flavor, spot, strike_adj, T, r, b, sigma) * qty_adj
    
    sigmas = np.array([sigma] * len(ts_adj))
    EA = get_EA(Fs)
    EA2 = get_EA2(Fs, sigmas, ts_adj)
    sigma_a = np.sqrt((np.log(EA2) - 2*np.log(EA)) / T)
    return vanilla(flavor, EA, strike_adj, T, r, 0, sigma_a) * qty_adj


#%% The Curran (1994) Dicrete Asian approximation
def discrete_asian_Curran(flavor, spot, strike, ts, T, r, b, sigma, SA):

    n = len(ts)
    m = np.sum(ts <= 0)
    if m == 0:
        SA = 0
    n_adj = n-m
    
    ts = np.sort(ts)
    ts_adj = ts[m:]
    
    # 判断期权是否已确定行权/不行权
    if m*SA >= n*strike: # Judge option status #等号
        if flavor == 'put': # Put must be out-of-the-money
            return 0
        else: # Exercise is certain for call
            SA_all = (SA * m + np.sum([spot * np.exp(b*x) for x in ts_adj])) / n
            return (SA_all - strike) * np.exp(-r * T)
    
    strike_adj = (n*strike - m*SA) / n_adj
    qty_adj = n_adj / n
    
    # 判断是否只剩一个待确定的价格
    if n_adj == 1: # Only one fix left # 简便计算
        return vanilla(flavor, spot, strike_adj, T, r, b, sigma) * qty_adj
    
    return discrete_asian_Curran_not_into_averaging_period(
        flavor, spot, strike_adj, ts_adj, T, r, b, sigma) * qty_adj


def discrete_asian_Curran_not_into_averaging_period(flavor, spot, strike, ts, T, r, b, sigma):
    '''
    Xi = lnSi #正态分布(mu_xi[i], var_xi[i])
    X = np.mean(Xi) #正态分布(mu_xa, var_xa)
    G = np.exp(X) #几何平均数 #对数正态分布
    A = np.mean(Si) #算数平均数 # Xi|X正态分布 <=> Xi|G正态分布 <=> Si|G对数正态分布
    '''
    n = len(ts)    
    mu_xi = np.log(spot) + (b - sigma**2/2) * ts #1*n
    var_xi = sigma**2 * ts #1*n
    
    mu_xa = np.mean(mu_xi) #1*1
    cov_xi_xj = np.zeros((n, n))
    for i in range(n):
        cov_xi_xj[i,:i+1] = var_xi[:i+1]
    cov_xi_xj = cov_xi_xj + cov_xi_xj.T - np.diag(cov_xi_xj.diagonal()) #n*n
    cov_xa_xi = np.mean(cov_xi_xj, axis=0) #1*n
    var_xa = np.mean(cov_xa_xi) #1*1
    sigma_xa = np.sqrt(var_xa) #1*1
    
    g_dist = lognorm(s=sigma_xa, scale=np.exp(mu_xa))

    def EA_G(x):
        E = mu_xi + (np.log(x) - mu_xa) / var_xa * cov_xa_xi #1*n
        D = var_xi - cov_xa_xi**2 / var_xa #1*n
        return np.mean(np.exp(E + D/2)) #1*1
       
    if flavor == 'call':
        I1 = (1/n) * np.dot(np.exp(mu_xi + var_xi/2), 
                            norm.cdf((mu_xa - np.log(strike) + cov_xa_xi) / sigma_xa))
        I2 = strike * norm.cdf((mu_xa - np.log(strike)) / sigma_xa)
        C2 = I1 - I2
        def f(x):
            return max((EA_G(x) - strike, 0)) * g_dist.pdf(x)
    else:
        C2 = 0
        def f(x):
            return max((strike - EA_G(x), 0)) * g_dist.pdf(x)
    C1, _ = quad(f, 0, strike)
    return np.exp(-r*T) * (C1+C2)



