import numpy as np
import pandas as pd
from scipy import optimize
from typing import Union, List, Dict

from ...utils.error import FinError
from ...utils.date import Date
from ...utils.day_count import DayCountTypes
from ...utils.frequency import FrequencyTypes
from ...utils.calendar import Calendar, BusDayAdjustTypes
from ...utils.helpers import check_argument_types, label_to_string, times_from_dates
from ...utils.global_types import SwapTypes
from ...market.curves.discount_curve import DiscountCurve
from ...market.curves.interpolator import InterpTypes, Interpolator
# from ...utils.math import test_monotonicity, g_small
from ...utils.global_vars import g_days_in_year

SWAP_TOL = 1e-10

###############################################################################


def _f(df, *args):
    """Root search objective function for OIS"""

    curve = args[0]
    value_dt = args[1]
    swap = args[2]
    num_points = len(curve._times)
    curve._dfs[num_points - 1] = df

    # For discount that need a fit function, we fit it now
    curve._interpolator.fit(curve._times, curve._dfs)
    v_swap = swap.value(value_dt, curve, None)
    notional = swap.fixed_leg.notional
    v_swap /= notional
    return v_swap


###############################################################################


class CCSCurve(DiscountCurve):
    """
    """
    
    ###############################################################################
    
    def __init__(
        self,
        value_dt: Date,
        fx_forwards: list,
        ois_swaps: list,
        foreign_curve: DiscountCurve,
        interp_type: InterpTypes = InterpTypes.FLAT_FWD_RATES,
    ):
        """
        """
        check_argument_types(self.__init__, locals())
        
        self.value_dt = value_dt
        self.foreign_curve = foreign_curve
        self._interp_type = interp_type
        self._interpolator = None

        self._validate_inputs(fx_forwards, ois_swaps)
        self._from_ql = False
        self._build_curve()
        
    ###############################################################################
    
    def _validate_inputs(self, fx_forwards, ois_swaps):
        """Validate the inputs for each of the Libor products."""

        # Now determine which instruments are used
        self.used_forwards = fx_forwards
        self.used_swaps = ois_swaps

        # Need the floating leg basis for the curve
        if len(self.used_swaps) > 0:
            self.dc_type = ois_swaps[0].float_leg.dc_type
        else:
            self.dc_type = None

    ###############################################################################

    def _build_curve(self):
        
        self._build_curve_using_1d_solver()
        
    ###############################################################################
    
    # def _build_curve_using_1d_solver(self):
        
    #     self._interpolator = Interpolator(self._interp_type)
    #     self._times = np.array([])
    #     self._dfs = np.array([])

    #     t_mat = 0.0
    #     df_mat = 1.0
    #     self._times = np.append(self._times, 0.0)
    #     self._dfs = np.append(self._dfs, df_mat)
    #     self._interpolator.fit(self._times, self._dfs)
        
    #     for fwd in self.used_forwards:
    #         fwd_rate = fwd.fwd_rate
    #         df_f_settle = self.foreign_curve.df(fwd.settle_dt, day_count=DayCountTypes.ACT_365F)
    #         df_f_maturity = self.foreign_curve.df(fwd.maturity_dt, day_count=DayCountTypes.ACT_365F)
    #         t_settle = (fwd.settle_dt - self.value_dt) / g_days_in_year
    #         df_d_settle = self._interpolator.interpolate(t_settle)

    #         # 根据利率平价关系计算到期日的本币折现因子
    #         # df_d(t_e) = df_d(t_s) · df_f(t_e) / df_f(t_s) · spot / fwd_rate
    #         df_mat = df_d_settle * (df_f_maturity / df_f_settle) * (self.spot_rate / fwd_rate)
            
    #         # 计算到期日的时间点
    #         t_mat = (fwd.maturity_dt - self.value_dt) / g_days_in_year

    #         # 添加到曲线
    #         self._times = np.append(self._times, t_mat)
    #         self._dfs = np.append(self._dfs, df_mat)
            
    #         # 更新插值器
    #         self._interpolator.fit(self._times, self._dfs)

    # def _build_curve_using_1d_solver(self):
    #     """通过迭代法解决结算日和到期日折现因子的循环依赖问题"""
        
    #     # 初始化时间点和折现因子数组
    #     self._times = np.array([0.0])
    #     self._dfs = np.array([1.0])  # 估值日的折现因子为1
    #     self._interpolator = Interpolator(self._interp_type)
    #     self._interpolator.fit(self._times, self._dfs)
        
    #     # 获取结算日(假设所有远期合约的结算日相同，通常为T+2)
    #     settle_dt = self.used_forwards[0].settle_dt
    #     t_settle = (settle_dt - self.value_dt) / g_days_in_year
        
    #     # 获取外币(USD)在结算日的折现因子
    #     df_f_settle = self.foreign_curve.df(settle_dt)
        
    #     # 初始估计：假设结算日的本币利率与外币相同
    #     # 这只是一个起点，后续会通过迭代优化
    #     df_d_settle = df_f_settle
        
    #     # 临时存储到期日的折现因子
    #     maturity_dfs = []
        
    #     # 迭代求解
    #     max_iterations = 10
    #     tolerance = 1e-10
        
    #     # 如果结算日不是估值日，需要添加结算日点
    #     if t_settle > 0:
    #         temp_times = np.array([0.0, t_settle])
    #         temp_dfs = np.array([1.0, df_d_settle])
    #         temp_interpolator = Interpolator(self._interp_type)
    #         temp_interpolator.fit(temp_times, temp_dfs)
    #     else:
    #         temp_interpolator = self._interpolator
        
    #     # 迭代求解结算日折现因子
    #     for _ in range(max_iterations):
    #         # 保存当前结算日折现因子作为比较基准
    #         prev_df_settle = df_d_settle
            
    #         # 计算所有到期日的折现因子
    #         maturity_dfs = []
    #         for fwd in self.used_forwards:
    #             # 计算远期汇率
    #             fwd_rate = fwd.fwd_rate
                
    #             # 获取外币在结算日和到期日的折现因子
    #             df_f_settle = self.foreign_curve.df(fwd.settle_dt, day_count=DayCountTypes.ACT_365F)
    #             df_f_maturity = self.foreign_curve.df(fwd.maturity_dt, day_count=DayCountTypes.ACT_365F)
                
    #             # 根据利率平价关系计算到期日的本币折现因子
    #             df_d_maturity = df_d_settle * (df_f_maturity / df_f_settle) * (fwd.spot_rate / fwd_rate)
    #             maturity_dfs.append(df_d_maturity)
            
    #         # 使用第一个远期合约的到期日折现因子重新估计结算日折现因子
    #         t_first_maturity = (self.used_forwards[0].maturity_dt - self.value_dt) / g_days_in_year
            
    #         # 创建临时曲线用于插值
    #         temp_times = np.array([0.0, t_first_maturity])
    #         temp_dfs = np.array([1.0, maturity_dfs[0]])
    #         temp_interpolator = Interpolator(self._interp_type)
    #         temp_interpolator.fit(temp_times, temp_dfs)
            
    #         # 使用临时插值器计算结算日折现因子
    #         new_df_settle = temp_interpolator.interpolate(t_settle)
            
    #         # 更新结算日折现因子
    #         df_d_settle = new_df_settle
            
    #         # 检查收敛性
    #         if abs(new_df_settle - prev_df_settle) < tolerance:
    #             break
        
    #     # 使用最终收敛的结算日折现因子构建完整曲线
    #     self._times = np.array([0.0])
    #     self._dfs = np.array([1.0])
        
    #     if t_settle > 0:
    #         self._times = np.append(self._times, t_settle)
    #         self._dfs = np.append(self._dfs, df_d_settle)
        
    #     # 添加所有到期日点
    #     for i, fwd in enumerate(self.used_forwards):
    #         t_maturity = (fwd.maturity_dt - self.value_dt) / g_days_in_year
    #         self._times = np.append(self._times, t_maturity)
    #         self._dfs = np.append(self._dfs, maturity_dfs[i])
        
    #     # 最终拟合曲线
    #     self._interpolator.fit(self._times, self._dfs)
    
    def _build_curve_using_1d_solver(self):
        """通过迭代法解决结算日和到期日折现因子的循环依赖问题"""

        self._times = np.array([0.0])
        self._dfs = np.array([1.0])
        self._interpolator = Interpolator(self._interp_type)
        self._interpolator.fit(self._times, self._dfs)
        
        for i, fwd in enumerate(self.used_forwards):
            if i == 0:
                t_settle, df_d_settle, df_d_mat = self._solve_for_df_d_settle(fwd)
                if t_settle > 0:
                    self._times = np.append(self._times, t_settle)
                    self._dfs = np.append(self._dfs, df_d_settle)
                    self._interpolator.fit(self._times, self._dfs)
            else:
                df_d_mat = self._get_df_d_mat(fwd)
        
            t_mat = (fwd.maturity_dt - self.value_dt) / g_days_in_year
            self._times = np.append(self._times, t_mat)
            self._dfs = np.append(self._dfs, df_d_mat)
        
        for swap in self.used_swaps:
            # I use the lastPaymentDate in case a date has been adjusted fwd
            # over a holiday as the maturity date is usually not adjusted CHECK
            maturity_dt = swap.fixed_leg.payment_dts[-1]
            t_mat = (maturity_dt - self.value_dt) / g_days_in_year

            self._times = np.append(self._times, t_mat)
            self._dfs = np.append(self._dfs, df_d_mat)

            argtuple = (self, self.value_dt, swap)

            df_d_mat = optimize.newton(
                _f,
                x0=df_d_mat,
                fprime=None,
                args=argtuple,
                tol=SWAP_TOL,
                maxiter=50,
                fprime2=None,
                full_output=False,
            )
        
        self._interpolator.fit(self._times, self._dfs)
    
    ###############################################################################

    def _solve_for_df_d_settle(self, forward, max_iter=20, tolerance=1e-10):

        t_mat = (forward.maturity_dt - self.value_dt) / g_days_in_year
        t_settle = (forward.settle_dt - self.value_dt) / g_days_in_year
        df_f_settle = self.foreign_curve.df(forward.settle_dt, day_count=DayCountTypes.ACT_365F)
        df_f_mat = self.foreign_curve.df(forward.maturity_dt, day_count=DayCountTypes.ACT_365F)
        
        # 初始估计：假设结算日的本币利率与外币相同
        df_d_settle = df_f_settle        
        for _ in range(max_iter):

            # 保存当前结算日折现因子作为比较基准
            prev_df_settle = df_d_settle
            # 根据利率平价关系计算到期日的本币折现因子
            df_d_mat = df_d_settle * (df_f_mat / df_f_settle) * (forward.spot_rate / forward.fwd_rate)

            # 创建临时曲线用于插值
            temp_times = np.append(self._times, t_mat)
            temp_dfs = np.append(self._times, df_d_mat)
            temp_interpolator = Interpolator(self._interp_type)
            temp_interpolator.fit(temp_times, temp_dfs)
            
            # 使用临时插值器计算结算日折现因子
            new_df_settle = temp_interpolator.interpolate(t_settle)
            
            # 更新结算日折现因子
            df_d_settle = new_df_settle
            
            # 检查收敛性
            if abs(new_df_settle - prev_df_settle) < tolerance:
                break
        
        return t_settle, df_d_settle, df_d_mat
    
    def _get_df_d_mat(self, forward):
        t_settle = (forward.settle_dt - self.value_dt) / g_days_in_year
        df_f_settle = self.foreign_curve.df(forward.settle_dt, day_count=DayCountTypes.ACT_365F)
        df_f_mat = self.foreign_curve.df(forward.maturity_dt, day_count=DayCountTypes.ACT_365F)

        df_d_settle = self._interpolator.interpolate(t_settle)
        df_d_mat = df_d_settle * (df_f_mat / df_f_settle) * (forward.spot_rate / forward.fwd_rate)
        return df_d_mat

    ###############################################################################

    def print_table(self, payment_dt: list):
        """Print a table of zero rate and discount factor on pivot dates."""
            
        zr = self.zero_rate(
            payment_dt, 
            freq_type = FrequencyTypes.CONTINUOUS, 
            dc_type = DayCountTypes.ACT_365F
        )
            
        df = self.df(payment_dt, day_count = DayCountTypes.ACT_365F)
        
        payment_dt_datetime = [dt.datetime() for dt in payment_dt]
        curve_result = pd.DataFrame({"Date": payment_dt_datetime, "ZR": (zr*100).round(5), "DF": df.round(6)})

        return curve_result
    
    ###############################################################################
    
    def __repr__(self):
        s = label_to_string("对象类型", type(self).__name__)
        s += label_to_string("估值日期", self.value_dt)
        s += label_to_string("即期汇率", f"{self.spot_rate:.6f}")
        s += label_to_string("插值方法", self._interp_type)
        
        s += label_to_string("日期", "折现因子")
        num_points = len(self._times)
        for i in range(num_points):
            date = self.value_dt.add_days(int(self._times[i] * 365))
            s += label_to_string(f"{date}", f"{self._dfs[i]:.8f}")
            
        return s
        
    ###############################################################################