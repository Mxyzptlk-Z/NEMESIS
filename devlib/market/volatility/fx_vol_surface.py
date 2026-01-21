import warnings
warnings.filterwarnings('ignore')
import math
import numpy as np
import pandas as pd
import QuantLib as ql
from scipy.interpolate import CubicSpline, interp1d
from scipy.stats import norm
import copy

import devlib.market.curves.fx_curves as fx_fc
import devlib.utils.ql_calendar_utils as qcu
from scipy import optimize



class FxVolSurface:
    def __init__(self, today, vol_data, d_ccy, f_ccy, fx_fwd_crv, d_crv, 
                 daycount=ql.Actual365Fixed(), spot_delta=True, tweak=0.0):
        self.today = today
        self.vol_data = vol_data.copy()
        self.d_ccy = d_ccy
        self.f_ccy = f_ccy
        self.fx_fwd_crv = fx_fwd_crv
        self.d_crv = d_crv
        calendar = qcu.cfets_fx_calendar_map[f_ccy]
        f_crv = fx_fc.FxImpliedAssetCurve(today, d_crv, fx_fwd_crv, calendar, ql.Actual365Fixed())
        self.f_crv = f_crv
        self.daycount = daycount
        self.spot_delta = spot_delta
        self.tweak = tweak
    
        self.vol_data['25DC'] = (self.vol_data['25DRR'] + 2 * self.vol_data['25DBF'] + 
                                 2 * self.vol_data['ATM']) / 2
        self.vol_data['25DP'] = self.vol_data['25DC'] - self.vol_data['25DRR']
        self.vol_data['10DC'] = (self.vol_data['10DRR'] + 2 * self.vol_data['10DBF'] + 
                                 2 * self.vol_data['ATM']) / 2
        self.vol_data['10DP'] = self.vol_data['10DC'] - self.vol_data['10DRR']

        # calibrate Vol Surface at init
        self.__delta_to_strike__()

    
    def __delta_to_strike__(self):
        strike_25DC_list = []
        strike_25DP_list = []
        strike_10DC_list = []
        strike_10DP_list = []
        strike_ATM_list = []
        expiry_list = []
        
        for ix, row in self.vol_data.iterrows():
            expiry = row['ExpiryDate']
            expiry = ql.DateParser.parseFormatted(expiry, '%Y-%m-%d')
            expiry_list.append(expiry)
            T = self.daycount.yearFraction(self.today, expiry)
            F = self.fx_fwd_crv.get_forward(expiry)
            strike_ATM_list.append(F)
            df_f = self.f_crv.curve.discount(expiry)
            sigma_25DC = row['25DC']
            sigma_25DP = row['25DP']
            sigma_10DC = row['10DC']
            sigma_10DP = row['10DP']

            if self.spot_delta:
                strike_25DC = F / math.exp(norm.ppf(0.25 / df_f) * sigma_25DC * math.sqrt(T) - 
                                           0.5 * sigma_25DC ** 2 * T) 
                strike_25DP = F / math.exp( - norm.ppf(0.25 / df_f) * sigma_25DP * math.sqrt(T) - 
                                           0.5 * sigma_25DP ** 2 * T)
                strike_10DC = F / math.exp(norm.ppf(0.10 / df_f) * sigma_10DC * math.sqrt(T) - 
                                           0.5 * sigma_10DC ** 2 * T)
                strike_10DP = F / math.exp( - norm.ppf(0.10 / df_f) * sigma_10DP * math.sqrt(T) - 
                                           0.5 * sigma_10DP ** 2 * T)
                
            else:
                # Forward delta 待修改
                strike_25DC = F / math.exp(norm.ppf(0.25) * sigma_25DC * math.sqrt(T) - 
                                           0.5 * sigma_25DC ** 2 * T) 
                strike_25DP = F / math.exp( - norm.ppf(0.25) * sigma_25DP * math.sqrt(T) - 
                                           0.5 * sigma_25DP ** 2 * T)
                strike_10DC = F / math.exp(norm.ppf(0.10) * sigma_10DC * math.sqrt(T) - 
                                           0.5 * sigma_10DC ** 2 * T)
                strike_10DP = F / math.exp( - norm.ppf(0.10) * sigma_10DP * math.sqrt(T) - 
                                           0.5 * sigma_10DP ** 2 * T)
                
            strike_25DC_list.append(strike_25DC)
            strike_25DP_list.append(strike_25DP)
            strike_10DC_list.append(strike_10DC)
            strike_10DP_list.append(strike_10DP)
        
        # self.vol_data['expiry'] = expiry_list
        self.vol_data['Strike_10DP'] = strike_10DP_list
        self.vol_data['Strike_25DP'] = strike_25DP_list
        self.vol_data['Strike_ATM'] = strike_ATM_list
        self.vol_data['Strike_25DC'] = strike_25DC_list
        self.vol_data['Strike_10DC'] = strike_10DC_list

        # Cache Smile, Strike and Expiries info
        self.num_vol_sample = len(self.vol_data)
        self.smiles = self.vol_data[['10DP', '25DP', 'ATM', '25DC', '10DC']].values
        self.strikes = self.vol_data[['Strike_10DP', 'Strike_25DP', 'Strike_ATM', 
                                      'Strike_25DC', 'Strike_10DC']].values
        # self.expiries = self.vol_data['expiry'].values
        self.expiries = np.array(expiry_list)
        
        # Cache cublic splines at once
        self.cubic_splines = []
        for n in range(self.num_vol_sample):
            # sort strikes
            idxs_sort = np.argsort(self.strikes[n])
            self.strikes[n], self.smiles[n] = self.strikes[n][idxs_sort], self.smiles[n][idxs_sort]
            cubic_spline = CubicSpline(self.strikes[n], self.smiles[n], True)
            self.cubic_splines.append(cubic_spline)
        
           
    def interp_vol(self, expiry, strike):
        if expiry <= self.expiries[0]:
            # first sample
            strikes = self.strikes[0]
            smiles = self.smiles[0]
            interp = self.cubic_splines[0]
            if strike <= strikes[0]:
                interp_vol = smiles[0]
            elif strike >= strikes[-1]:
                interp_vol = smiles[-1]
            else:
                interp_vol = interp(strike)

        elif expiry >= self.expiries[-1]:
            # last sample
            strikes = self.strikes[-1]
            smiles = self.smiles[-1]
            interp = self.cubic_splines[-1]
            if strike <= strikes[0]:
                interp_vol = smiles[0]
            elif strike >= strikes[-1]:
                interp_vol = smiles[-1]
            else:
                interp_vol = interp(strike)
            
        else:
            # middle sample
            pos_right = np.argmax(self.expiries > expiry)
            pos_left = pos_right - 1
            
            strikes_left = self.strikes[pos_left]
            smiles_left = self.smiles[pos_left]
            interp_left = self.cubic_splines[pos_left]
            
            if strike <= strikes_left[0]:
                interp_vol_left = smiles_left[0]
            elif strike >= strikes_left[-1]:
                interp_vol_left = smiles_left[-1]
            else:
                interp_vol_left = interp_left(strike)
            
            dcf_left = self.daycount.yearFraction(self.today, self.expiries[pos_left])
            var_left = interp_vol_left ** 2 * dcf_left
            
            strikes_right = self.strikes[pos_right]
            smiles_right = self.smiles[pos_right]
            interp_right = self.cubic_splines[pos_right]
            
            if strike <= strikes_right[0]:
                interp_vol_right = smiles_right[0]
            elif strike >= strikes_right[-1]:
                interp_vol_right = smiles_right[-1]
            else:
                interp_vol_right = interp_right(strike)
            
            dcf_right = self.daycount.yearFraction(self.today, self.expiries[pos_right])
            var_right = interp_vol_right ** 2 * dcf_right
            
            dcf = self.daycount.yearFraction(self.today, expiry)

            interp_vol = math.sqrt((var_left * (dcf_right - dcf) + var_right * (dcf - dcf_left)) / 
                                   (dcf_right - dcf_left) / dcf)
            
        return float(interp_vol) + self.tweak
        
        
    def vol_tweak(self, tweak):
        tweaked_fx_vol_surface = copy.copy(self)
        tweaked_fx_vol_surface.tweak += tweak

        return tweaked_fx_vol_surface
    


class SigmaSolver:
    def __init__(self, T, df_f, strike, mtm, vol_data, max_retries=100, tol=1e-4):
        self.T = T             
        self.df_f = df_f       
        self.strike = strike    
        self.mtm = mtm
        self.vol_data = vol_data
        
        # 设置循环次数
        self.max_retries = max_retries
        # 设置优化精度
        self.tol = tol     
        
        # 计算delta维度插值函数
        self.interp_delta_funcs = {}
        for t in self.vol_data.index:
            smile = self.vol_data.loc[t,:].dropna(axis=0)
            self.interp_delta_funcs[t] = interp1d(smile.index, smile**2*t, fill_value='extrapolate')


    def target_func(self, sigma):
        # 计算d1和delta
        d1 = (math.log(self.mtm / self.strike) + 0.5 * sigma ** 2 * self.T) / (sigma * math.sqrt(self.T))
        delta = self.df_f * norm.cdf(d1)
        
        # 计算调整波动率
        ts = self.vol_data.index
        interp_cumulative_var = pd.Series(data=[np.nan]*len(ts), index=ts)
        
        for t in ts:
            interp_cumulative_var[t] = self.interp_delta_funcs[t](delta)
            
        interp_func = interp1d(interp_cumulative_var.index, interp_cumulative_var, fill_value='extrapolate')
        interp_sigma = interp_func(self.T)
        if interp_sigma < 0:  
            adjusted_sigma = 1e-4
        else:
            adjusted_sigma = math.sqrt(interp_sigma / self.T)
        return sigma - adjusted_sigma


    def solve_sigma(self, initial_guess): 
        optimize_sigma = optimize.newton(self.target_func, initial_guess, tol=self.tol * 1e-4, maxiter=self.max_retries, disp=False)
        if np.abs(self.target_func(optimize_sigma)) < self.tol:
            return optimize_sigma
        else:
            update_optimize_sigma = optimize.newton(self.target_func, optimize_sigma, tol=self.tol * 1e-8, maxiter=self.max_retries, disp=False)
            if np.abs(self.target_func(update_optimize_sigma)) >= self.tol:
                # 此处为报错展示，系统实现以warning形式记录日志，以防批量估值异常
                raise RuntimeError("Tartget func is still big, value is %s."%(self.target_func(update_optimize_sigma))) 
            return update_optimize_sigma
                
    
class FxVolSurfaceHK:
    def __init__(self, today, vol_data, spot, d_ccy, f_ccy, fx_fwd_crv, d_crv, f_crv,
                 calendar=ql.NullCalendar(), daycount=ql.Actual365Fixed(), tweak=0.0):
        self.today = today
        self.vol_data_rr_bf = vol_data.copy()
        self.spot = spot
        self.d_ccy = d_ccy
        self.f_ccy = f_ccy
        self.fx_fwd_crv = fx_fwd_crv
        self.d_crv = d_crv
        self.f_crv = f_crv
        self.calendar = calendar 
        self.daycount = daycount
        self.tweak = tweak
        
        self.vol_data_rr_bf['Volatility'] /= 100
        
        self.vol_data = self.__get_vol_data_cp__()
        
        
    def __get_vol_data_cp__(self):
        
        vol_data_pivot = self.vol_data_rr_bf.pivot(index='Maturity Period', columns='Delta Type', values='Volatility')
        atm_missing = vol_data_pivot[vol_data_pivot['ATM'].isna()]
        if len(atm_missing)!=0:
            raise Exception(f'ATM data of {list(atm_missing.index)} missing!')
        
        vol_data = vol_data_pivot[['ATM']]
        delta_dict = {'ATM': 0.5}
        nums = set([x.split('D_')[0] for x in vol_data_pivot.columns]) - set(['ATM'])
        for num in nums:
            try:
                pair_data_missing = vol_data_pivot[vol_data_pivot[f'{num}D_RR'].isna()!=vol_data_pivot[f'{num}D_BF'].isna()]
                if len(pair_data_missing)!=0:
                    raise Exception(f'{num}-pair data of {list(pair_data_missing.index)} missing!')
            except:
                raise Exception(f'{num}-pair data of {list(pair_data_missing.index)} missing!')
                
            vol_data[f'{num}DC'] = vol_data_pivot[f'{num}D_RR']/2 + vol_data_pivot[f'{num}D_BF'] + vol_data_pivot['ATM']
            vol_data[f'{num}DP'] = -vol_data_pivot[f'{num}D_RR']/2 + vol_data_pivot[f'{num}D_BF'] + vol_data_pivot['ATM']
            delta_dict[f'{num}DC'] = float(num)/100
            delta_dict[f'{num}DP'] = 1- float(num)/100 #check
        
        vol_data.columns = vol_data.columns.map(lambda x: delta_dict[x])
        vol_data.columns.name = None
        vol_data.index = vol_data.index.map(lambda x: self.daycount.yearFraction(
                self.today, self.calendar.advance(self.today, ql.Period(x))))
        vol_data.index.name = None
        vol_data = vol_data.loc[sorted(vol_data.index), sorted(vol_data.columns)]
        
        return vol_data
        
        
    def __get_atm_term_sigma__(self, t):
        atm_vol = self.vol_data[0.5].copy()
        interp_t_func = interp1d(atm_vol.index, atm_vol, fill_value='extrapolate')
        atm_term_sigma = interp_t_func(t)
        if atm_term_sigma < 0:
            atm_term_sigma = 1e-4
        return atm_term_sigma
    
    
    def interp_vol(self, expiry, strike): 
        # 期权参数计算
        mtm = self.fx_fwd_crv.get_forward(expiry)
        T = self.daycount.yearFraction(self.today, expiry)  
        df_f = self.f_crv.curve.discount(expiry)
        
        # 设置初始sigma
        sigma = self.__get_atm_term_sigma__(T)
        
        solver = SigmaSolver(T, df_f, strike, mtm, self.vol_data)
        sigma = solver.solve_sigma(sigma)  
        
        return float(sigma) + self.tweak

            
    def vol_tweak(self, tweak):
        tweaked_fx_vol_surface = copy.copy(self)
        tweaked_fx_vol_surface.tweak += tweak

        return tweaked_fx_vol_surface
    