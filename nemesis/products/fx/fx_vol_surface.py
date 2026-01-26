import numpy as np
import pandas as pd
from scipy import optimize
from scipy.interpolate import interp1d
from scipy.stats import norm

from ...market.curves.discount_curve import DiscountCurve
from ...utils.calendar import BusDayAdjustTypes, Calendar, CalendarTypes
from ...utils.date import Date
from ...utils.day_count import DayCount, DayCountTypes
from ...utils.error import FinError

###############################################################################


class SigmaSolver:
    """
    Iterative solver for finding volatility given strike in delta-space.

    The core idea is that sigma and delta have a circular dependency:
    - Given sigma -> we can calculate delta (via Black-Scholes d1)
    - Given delta -> we can interpolate sigma from the vol surface

    Goal: Find sigma such that sigma = f(Delta(sigma))
    """

    def __init__(
        self,
        T: float,
        df_f: float,
        strike: float,
        forward: float,
        vol_data: pd.DataFrame,
        max_retries: int = 100,
        tol: float = 1e-4
    ):
        """
        Parameters
        ----------
        T : float
            Time to expiry in years
        df_f : float
            Foreign currency discount factor
        strike : float
            Option strike price
        forward : float
            Forward FX rate
        vol_data : pd.DataFrame
            Volatility data with T as index and delta as columns
        max_retries : int
            Maximum number of iterations
        tol : float
            Convergence tolerance
        """
        self.T = T
        self.df_f = df_f
        self.strike = strike
        self.forward = forward
        self.vol_data = vol_data

        self.max_retries = max_retries
        self.tol = tol

        # Pre-compute delta interpolation functions for each tenor
        self.interp_delta_funcs = {}
        for t in self.vol_data.index:
            smile = self.vol_data.loc[t, :].dropna(axis=0)
            # Store cumulative variance (sigma^2 * t) for variance interpolation
            self.interp_delta_funcs[t] = interp1d(
                smile.index, smile ** 2 * t, fill_value='extrapolate'
            )

    def target_func(self, sigma: float) -> float:
        """
        Target function for root-finding.

        Parameters
        ----------
        sigma : float
            Current volatility guess

        Returns
        -------
        float
            Difference between input sigma and interpolated sigma
        """
        # Calculate d1 and delta using Black-Scholes
        d1 = (np.log(self.forward / self.strike) + 0.5 * sigma ** 2 * self.T) / \
             (sigma * np.sqrt(self.T))
        delta = self.df_f * norm.cdf(d1)

        # Interpolate cumulative variance at each tenor using delta
        ts = self.vol_data.index
        interp_cumulative_var = pd.Series(data=[np.nan] * len(ts), index=ts)

        for t in ts:
            interp_cumulative_var[t] = self.interp_delta_funcs[t](delta)

        # Interpolate in time dimension
        interp_func = interp1d(
            interp_cumulative_var.index,
            interp_cumulative_var,
            fill_value='extrapolate'
        )
        interp_sigma_sq_t = interp_func(self.T)

        # Convert cumulative variance back to volatility
        if interp_sigma_sq_t < 0:
            adjusted_sigma = 1e-4
        else:
            adjusted_sigma = np.sqrt(interp_sigma_sq_t / self.T)

        return sigma - adjusted_sigma

    def solve_sigma(self, initial_guess: float) -> float:
        """
        Solve for volatility using Newton's method.

        Parameters
        ----------
        initial_guess : float
            Initial volatility guess (typically ATM vol)

        Returns
        -------
        float
            Solved volatility
        """
        optimize_sigma = optimize.newton(
            self.target_func,
            initial_guess,
            tol=self.tol * 1e-4,
            maxiter=self.max_retries,
            disp=False
        )

        if np.abs(self.target_func(optimize_sigma)) < self.tol:
            return optimize_sigma
        else:
            # Try again with tighter tolerance
            update_optimize_sigma = optimize.newton(
                self.target_func,
                optimize_sigma,
                tol=self.tol * 1e-8,
                maxiter=self.max_retries,
                disp=False
            )
            if np.abs(self.target_func(update_optimize_sigma)) >= self.tol:
                raise RuntimeError(
                    f"Target func is still big, value is {self.target_func(update_optimize_sigma)}"
                )
            return update_optimize_sigma


###############################################################################


class FXVolSurface:
    """
    FX Volatility Surface using delta-space interpolation.

    This class builds a volatility surface from market RR/BF quotes and
    provides volatility interpolation for any expiry/strike combination.

    The interpolation is performed in delta space rather than strike space,
    which is the standard convention in FX options markets.

    Interpolation Methods:
    - Delta dimension: Linear interpolation
    - Time dimension: Variance interpolation (sigma^2 * T)
    """

    def __init__(
        self,
        value_dt: Date,
        vol_data: pd.DataFrame,
        spot_fx_rate: float,
        dom_ccy: str,
        for_ccy: str,
        fx_forward_curve,
        dom_curve: DiscountCurve,
        for_curve: DiscountCurve,
        cal_type: CalendarTypes = CalendarTypes.NONE,
        dc_type: DayCountTypes = DayCountTypes.ACT_365F,
    ):
        """
        Parameters
        ----------
        value_dt : Date
            Valuation date
        vol_data : pd.DataFrame
            Volatility data in RR/BF format with columns:
            - 'Maturity Period': tenor string (e.g., '1M', '3M')
            - 'Delta Type': one of 'ATM', '25D_RR', '25D_BF', '10D_RR', '10D_BF', etc.
            - 'Volatility': volatility value (in percentage, e.g., 10 for 10%)
        spot_fx_rate : float
            Spot FX rate
        dom_ccy : str
            Domestic currency code (3 letters)
        for_ccy : str
            Foreign currency code (3 letters)
        fx_forward_curve : FXForwardCurve
            FX forward curve for forward rate calculation
        dom_curve : DiscountCurve
            Domestic currency discount curve
        for_curve : DiscountCurve
            Foreign currency discount curve
        cal_type : CalendarTypes
            Calendar type for date calculations
        dc_type : DayCountTypes
            Day count type for time fraction calculations
        """
        self.value_dt = value_dt
        self.vol_data_rr_bf = vol_data.copy()
        self.spot_fx_rate = spot_fx_rate
        self.dom_ccy = dom_ccy
        self.for_ccy = for_ccy
        self.fx_forward_curve = fx_forward_curve
        self.dom_curve = dom_curve
        self.for_curve = for_curve
        self.cal_type = cal_type
        self.dc_type = dc_type

        self._calendar = Calendar(cal_type)
        self._day_count = DayCount(dc_type)

        # Convert volatility from percentage to decimal
        self.vol_data_rr_bf['Volatility'] = self.vol_data_rr_bf['Volatility'] / 100.0

        # Transform RR/BF data to Call/Put volatilities
        self.vol_data = self._build_vol_data()

    def _build_vol_data(self) -> pd.DataFrame:
        """
        Transform RR/BF format volatility data to Call/Put delta format.

        The transformation formulas:
        - Call vol (σ_DC) = RR/2 + BF + ATM
        - Put vol (σ_DP) = -RR/2 + BF + ATM

        Returns
        -------
        pd.DataFrame
            Volatility data with time T as index and delta as columns
        """
        # Pivot the data: rows=tenor, columns=delta type
        vol_data_pivot = self.vol_data_rr_bf.pivot(
            index='Maturity Period',
            columns='Delta Type',
            values='Volatility'
        )

        # Check ATM data availability
        atm_missing = vol_data_pivot[vol_data_pivot['ATM'].isna()]
        if len(atm_missing) != 0:
            raise FinError(f'ATM data of {list(atm_missing.index)} missing!')

        # Start with ATM data
        vol_data = vol_data_pivot[['ATM']].copy()
        delta_dict = {'ATM': 0.5}  # ATM corresponds to delta = 0.5

        # Extract delta numbers (e.g., '25' from '25D_RR')
        nums = set([x.split('D_')[0] for x in vol_data_pivot.columns]) - set(['ATM'])

        for num in nums:
            try:
                # Check that RR and BF data are both present or both absent
                pair_data_missing = vol_data_pivot[
                    vol_data_pivot[f'{num}D_RR'].isna() != vol_data_pivot[f'{num}D_BF'].isna()
                ]
                if len(pair_data_missing) != 0:
                    raise FinError(f'{num}-pair data of {list(pair_data_missing.index)} missing!')
            except KeyError:
                raise FinError(f'{num}-pair data missing RR or BF column!')

            # Transform RR/BF to Call/Put volatilities
            # Call: RR/2 + BF + ATM
            vol_data[f'{num}DC'] = (
                vol_data_pivot[f'{num}D_RR'] / 2 +
                vol_data_pivot[f'{num}D_BF'] +
                vol_data_pivot['ATM']
            )
            # Put: -RR/2 + BF + ATM
            vol_data[f'{num}DP'] = (
                -vol_data_pivot[f'{num}D_RR'] / 2 +
                vol_data_pivot[f'{num}D_BF'] +
                vol_data_pivot['ATM']
            )

            # Map column names to delta values
            delta_dict[f'{num}DC'] = float(num) / 100  # e.g., 25DC -> 0.25
            delta_dict[f'{num}DP'] = 1 - float(num) / 100  # e.g., 25DP -> 0.75

        # Rename columns from delta names to delta values
        vol_data.columns = vol_data.columns.map(lambda x: delta_dict[x])
        vol_data.columns.name = None

        # Convert tenor strings to year fractions
        vol_data.index = vol_data.index.map(
            lambda x: self._tenor_to_year_fraction(x)
        )
        vol_data.index.name = None

        # Sort by time (rows) and delta (columns)
        vol_data = vol_data.loc[sorted(vol_data.index), sorted(vol_data.columns)]

        return vol_data

    def _tenor_to_year_fraction(self, tenor: str) -> float:
        """
        Convert a tenor string to year fraction.

        Parameters
        ----------
        tenor : str
            Tenor string (e.g., '1M', '3M', '1Y')

        Returns
        -------
        float
            Year fraction
        """
        expiry_dt = self.value_dt.add_tenor(tenor)
        expiry_dt = self._calendar.adjust(expiry_dt, BusDayAdjustTypes.FOLLOWING)
        return self._day_count.year_frac(self.value_dt, expiry_dt)[0]

    def _get_atm_term_sigma(self, t: float) -> float:
        """
        Get ATM volatility for a given time by interpolation.

        Parameters
        ----------
        t : float
            Time in years

        Returns
        -------
        float
            ATM volatility
        """
        atm_vol = self.vol_data[0.5].copy()
        interp_t_func = interp1d(atm_vol.index, atm_vol, fill_value='extrapolate')
        atm_term_sigma = interp_t_func(t)

        if atm_term_sigma < 0:
            atm_term_sigma = 1e-4

        return float(atm_term_sigma)

    def interp_vol(self, expiry_dt: Date, strike: float) -> float:
        """
        Interpolate volatility for a given expiry and strike.

        Parameters
        ----------
        expiry_dt : Date
            Option expiry date
        strike : float
            Option strike price

        Returns
        -------
        float
            Interpolated volatility
        """
        # Get forward rate at expiry
        forward = self.fx_forward_curve.get_forward(expiry_dt, self.dc_type)

        # Calculate time to expiry
        T = self._day_count.year_frac(self.value_dt, expiry_dt)[0]

        # Get foreign currency discount factor
        df_f = self.for_curve.df(expiry_dt, day_count=self.dc_type)

        # Use ATM vol as initial guess
        sigma = self._get_atm_term_sigma(T)

        # Solve for volatility
        solver = SigmaSolver(T, df_f, strike, forward, self.vol_data)
        sigma = solver.solve_sigma(sigma)

        return float(sigma)

    def __repr__(self) -> str:
        s = "FX VOLATILITY SURFACE\n"
        s += f"Value Date: {self.value_dt}\n"
        s += f"Currency Pair: {self.for_ccy}/{self.dom_ccy}\n"
        s += f"Spot Rate: {self.spot_fx_rate}\n"
        s += f"Tenors: {list(self.vol_data.index)}\n"
        s += f"Deltas: {list(self.vol_data.columns)}\n"
        return s


###############################################################################
